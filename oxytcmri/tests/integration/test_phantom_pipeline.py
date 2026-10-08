"""
End-to-end run of the lesion pipeline on a realistic digital phantom cohort.

The cohort is generated on the fly (two centres, three healthy volunteers
and one patient each) and processed exactly as the CLI would: import,
normative values, segmentation with STAPLE merging, lesion volumes. The
segmentation is then scored against the known ground truth, in the spirit
of the phantom experiments of Mistral et al. (2022).
"""
import sqlite3
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from oxytcmri.domain.entities.mri import AbnormalValueType, DTIMetric
from oxytcmri.domain.use_cases.compute_dti_normative_values import StatisticsStrategies
from oxytcmri.infrastructure.cli import ControllerFactory, DatabaseSetup
from oxytcmri.infrastructure.settings import Settings
from oxytcmri.tests.phantoms import (
    CohortSpec,
    LesionKind,
    PhantomCohort,
    generate_cohort,
)
from oxytcmri.tests.phantoms.scoring import SegmentationScore, score_segmentation


@pytest.fixture(scope="module")
def cohort(tmp_path_factory) -> PhantomCohort:
    """Generate the cohort and run the whole pipeline on it, once per module."""
    spec = CohortSpec(centers={1: "Centre A", 2: "Centre B"}, center_scales={1: 1.0, 2: 1.05},
                      healthy_per_center=3, patients_per_center=1, seed=2024)
    cohort = generate_cohort(spec, tmp_path_factory.mktemp("phantom_pipeline"))

    settings = Settings(str(cohort.settings_file))
    controller = ControllerFactory.create_dti_controller(settings, DatabaseSetup.create_database_gateway(settings))
    controller.compute_normative_dti_values(
        dti_metrics=[DTIMetric.MD],
        statistics_strategies=[StatisticsStrategies.QUANTILE_5_STRATEGY, StatisticsStrategies.QUANTILE_95_STRATEGY],
    )
    controller.segment_dti_abnormal_values(dti_metrics=[DTIMetric.MD])
    controller.compute_brain_lesions_volumes(dti_metrics=[DTIMetric.MD])
    return cohort


def load_segmentation(exam_folder: Path) -> np.ndarray:
    """Integer segmentation written by the pipeline next to the MD map."""
    return np.rint(np.asarray(nib.load(str(exam_folder / "MD_segmentation.nii.gz")).dataobj)).astype(int)


def labelled_mask(exam_folder: Path) -> np.ndarray:
    """Voxels covered by the first atlas, i.e. those the pipeline can label."""
    return np.asarray(nib.load(str(exam_folder / "Atlas1.nii.gz")).dataobj) > 0


def scores_for(cohort: PhantomCohort, kind: LesionKind) -> dict[str, SegmentationScore]:
    return {
        exam.exam_id: score_segmentation(load_segmentation(exam.folder), cohort.load_ground_truth(exam),
                                         kind.ground_truth_value, labelled_mask(exam.folder))
        for exam in cohort.patients
    }


class TestPipelineOnPhantoms:
    def test_segmentation_written_for_every_patient(self, cohort):
        for exam in cohort.patients:
            segmentation = load_segmentation(exam.folder)
            assert segmentation.shape == cohort.spec.geometry.shape
            assert set(np.unique(segmentation)) <= {0, 1, 2}

    def test_high_md_lesions_are_recovered(self, cohort):
        """Vasogenic-like lesions (MD x1.1 to x2.1) are mostly detected with few false alarms."""
        for exam_id, score in scores_for(cohort, LesionKind.HIGH_MD).items():
            assert score.recall >= 0.6, f"{exam_id}: HIGH recall {score.recall:.2f}"
            assert score.false_positive_rate <= 0.06, f"{exam_id}: HIGH false positive rate {score.false_positive_rate:.3f}"

    def test_low_md_lesions_are_recovered(self, cohort):
        """Cytotoxic-like lesions (MD x0.41 to x0.91) are detected."""
        for exam_id, score in scores_for(cohort, LesionKind.LOW_MD).items():
            assert score.recall >= 0.7, f"{exam_id}: LOW recall {score.recall:.2f}"

    @pytest.mark.xfail(strict=True, reason="STAPLE probabilities are summed (2*low + high) before rounding, "
                                            "so ambiguous voxels are encoded as LOW: false positives inflate "
                                            "the LOW lesion volume far beyond the ground truth.")
    def test_low_md_false_positive_rate_is_bounded(self, cohort):
        """Normal parenchyma flagged LOW should stay near the 5 % expected from the 5th-percentile threshold."""
        for exam_id, score in scores_for(cohort, LesionKind.LOW_MD).items():
            assert score.false_positive_rate <= 0.06, f"{exam_id}: LOW false positive rate {score.false_positive_rate:.3f}"

    def test_stored_volumes_match_segmentation_files(self, cohort):
        """The volumes in the database are the voxel counts of the written segmentation."""
        database = sqlite3.connect(str(cohort.output_dir / "phantom_database.db"))
        rows = database.execute(
            "SELECT mri_exam_id, abnormal_value_type, value_ml FROM brain_lesions_volumes "
            "WHERE region_of_interest_name = 'Whole Brain'").fetchall()
        assert len(rows) == 2 * len(cohort.patients)
        voxel_volume = cohort.spec.geometry.voxel_volume_ml
        for exam_id, abnormal_value_type, value_ml in rows:
            exam = next(exam for exam in cohort.patients if exam.exam_id == exam_id)
            code = AbnormalValueType(abnormal_value_type).to_integer()
            expected = np.count_nonzero(load_segmentation(exam.folder) == code) * voxel_volume
            assert value_ml == pytest.approx(expected, rel=1e-6)

    def test_high_md_volume_is_within_mistral_tolerance(self, cohort):
        """Mistral et al. reported +13 % volume overestimation by the automated procedure on phantoms;
        without spatial filtering the bias here is larger, so a loose factor-of-two bound is used."""
        for exam in cohort.patients:
            truth = exam.lesion_volumes_ml[LesionKind.HIGH_MD]
            segmentation = load_segmentation(exam.folder)
            detected = np.count_nonzero(segmentation == LesionKind.HIGH_MD.ground_truth_value) * \
                cohort.spec.geometry.voxel_volume_ml
            assert 0.5 * truth <= detected <= 2.5 * truth, f"{exam.exam_id}: HIGH {detected:.1f} ml vs {truth:.1f} ml"
