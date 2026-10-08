"""
Unit tests of the digital phantom generator.

They check that the synthetic anatomy, diffusivity values and inserted
lesions stay within the physiological ranges and the recipe of Mistral et al.
"""
import csv
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from oxytcmri.domain.entities.mri import AbnormalValueType, MRIExamId
from oxytcmri.domain.entities.subject import SubjectType
from oxytcmri.tests.phantoms import (
    CohortSpec,
    Lesion,
    LesionKind,
    PhantomGeometry,
    Tissue,
    apply_lesions,
    build_tissue_model,
    generate_cohort,
    sample_lesions,
)
from oxytcmri.tests.phantoms.anatomy import (
    grid_parcellation,
    hemispheric_parcellation,
    lobar_parcellation,
)
from oxytcmri.tests.phantoms.diffusivity import (
    REFERENCE_MD_MM2_PER_S,
    gaussian_smooth,
    synthesize_md_map,
)
from oxytcmri.tests.phantoms.lesions import Blob
from oxytcmri.tests.phantoms.scoring import score_segmentation


@pytest.fixture(scope="module")
def model():
    return build_tissue_model(PhantomGeometry(voxel_size_mm=3.0))


class TestAnatomy:
    def test_brain_volume_is_physiological(self, model):
        """An adult brain is roughly 1.1 to 1.5 litres."""
        assert 1100 <= model.brain_volume_ml <= 1500

    def test_every_tissue_is_present(self, model):
        present = set(np.unique(model.tissue))
        assert present == {int(tissue) for tissue in Tissue}

    def test_ventricles_are_inside_white_matter(self, model):
        ventricle = model.tissue == Tissue.VENTRICLE
        assert ventricle.any()
        # dilating the ventricles by one voxel only reaches parenchyma, never background
        shifted = np.zeros_like(ventricle)
        for axis in range(3):
            shifted |= np.roll(ventricle, 1, axis) | np.roll(ventricle, -1, axis)
        neighbours = model.tissue[shifted & ~ventricle]
        assert not np.isin(neighbours, [Tissue.BACKGROUND, Tissue.CSF]).any()

    def test_affine_is_centered_and_isotropic(self):
        geometry = PhantomGeometry(voxel_size_mm=2.0, field_of_view_mm=(40.0, 60.0, 80.0))
        assert geometry.shape == (20, 30, 40)
        x, y, z = geometry.coordinates_mm()
        assert np.isclose(x.mean(), 0.0) and np.isclose(y.mean(), 0.0) and np.isclose(z.mean(), 0.0)
        assert np.allclose(np.diag(geometry.affine)[:3], 2.0)
        assert geometry.voxel_volume_ml == pytest.approx(0.008)


class TestParcellations:
    def test_hemispheric_atlas_covers_parenchyma_only(self, model):
        atlas = hemispheric_parcellation(model, 1)
        assert (atlas.labels > 0).sum() == model.parenchyma_mask.sum()
        assert atlas.label_values == [21, 22, 31, 32, 41, 42, 50]

    def test_lobar_atlas_refines_hemispheric_atlas(self, model):
        coarse = hemispheric_parcellation(model, 1)
        fine = lobar_parcellation(model, 2)
        assert ((coarse.labels > 0) == (fine.labels > 0)).all()
        assert len(fine.label_values) > len(coarse.label_values)
        # each fine label lies within a single coarse label
        for label in fine.label_values:
            assert len(np.unique(coarse.labels[fine.labels == label])) == 1

    def test_grid_atlas_blocks_have_bounded_volume(self, model):
        atlas = grid_parcellation(model, 3, block_size_mm=36.0)
        max_voxels = max(np.count_nonzero(atlas.labels == label) for label in atlas.label_values)
        assert max_voxels * model.geometry.voxel_volume_ml <= 36.0 ** 3 / 1000.0


class TestDiffusivity:
    def test_tissue_values_match_reference(self, model):
        md = synthesize_md_map(model, np.random.default_rng(0))
        for tissue in (Tissue.WHITE_MATTER, Tissue.CORTEX, Tissue.DEEP_GREY):
            median = np.median(md[model.tissue == tissue])
            assert median == pytest.approx(REFERENCE_MD_MM2_PER_S[tissue], rel=0.08), tissue.name
        # ventricles are small, so partial volume with white matter lowers their median
        ventricle_median = np.median(md[model.tissue == Tissue.VENTRICLE])
        assert 0.8 * REFERENCE_MD_MM2_PER_S[Tissue.VENTRICLE] <= ventricle_median <= REFERENCE_MD_MM2_PER_S[Tissue.VENTRICLE]
        assert (md[model.tissue == Tissue.BACKGROUND] == 0).all()
        assert (md >= 0).all()

    def test_center_scale_shifts_the_whole_map(self, model):
        reference = synthesize_md_map(model, np.random.default_rng(1), center_scale=1.0)
        scaled = synthesize_md_map(model, np.random.default_rng(1), center_scale=1.1)
        inside = model.brain_mask
        assert np.allclose(scaled[inside], 1.1 * reference[inside])

    def test_gaussian_smooth_preserves_mean_and_reduces_variance(self):
        volume = np.random.default_rng(2).normal(size=(12, 14, 10))
        smoothed = gaussian_smooth(volume, sigma_voxels=1.0)
        assert smoothed.shape == volume.shape
        assert smoothed.mean() == pytest.approx(volume.mean(), abs=0.05)
        assert smoothed.var() < volume.var() / 5
        assert np.array_equal(gaussian_smooth(volume, 0.0), volume)


class TestLesions:
    def test_coefficient_must_be_in_range(self):
        with pytest.raises(ValueError):
            Lesion(kind=LesionKind.HIGH_MD, coefficient=0.5)
        with pytest.raises(ValueError):
            Lesion(kind=LesionKind.LOW_MD, coefficient=1.5)

    def test_sampled_lesions_follow_mistral_recipe(self, model):
        lesions = sample_lesions(model, np.random.default_rng(3), target_brain_fraction=0.03)
        assert 1 <= len(lesions) <= 6
        for lesion in lesions:
            low, high = lesion.kind.coefficient_range
            assert low <= lesion.coefficient <= high
        _, ground_truth = apply_lesions(np.ones(model.geometry.shape), lesions, model)
        fraction = np.count_nonzero(ground_truth) / model.brain_mask.sum()
        assert 0.02 <= fraction <= 0.06
        # lesions are confined to the parenchyma
        assert not (ground_truth[~model.parenchyma_mask] != 0).any()

    def test_apply_lesions_scales_md_and_keeps_csf(self, model):
        md = synthesize_md_map(model, np.random.default_rng(4))
        lesion = Lesion(kind=LesionKind.HIGH_MD, coefficient=2.0,
                        blobs=[Blob(center=(30.0, 20.0, 0.0), semi_axes=(12.0, 12.0, 12.0))])
        lesioned, ground_truth = apply_lesions(md, [lesion], model)
        core = ground_truth == AbnormalValueType.HIGH.to_integer()
        assert core.sum() > 0
        ratio = lesioned[core] / md[core]
        assert ratio.min() > 1.2 and ratio.max() <= 2.0 + 1e-9  # smoothed edges, saturated core
        csf = model.tissue == Tissue.VENTRICLE
        assert np.array_equal(lesioned[csf], md[csf])
        assert np.array_equal(lesioned[ground_truth == 0], md[ground_truth == 0]) is False  # smoothing spills out

    def test_low_md_lesion_lowers_values(self, model):
        md = synthesize_md_map(model, np.random.default_rng(5))
        lesion = Lesion(kind=LesionKind.LOW_MD, coefficient=0.5,
                        blobs=[Blob(center=(-30.0, -20.0, 0.0), semi_axes=(10.0, 10.0, 10.0))])
        lesioned, ground_truth = apply_lesions(md, [lesion], model)
        core = ground_truth == AbnormalValueType.LOW.to_integer()
        assert (lesioned[core] < md[core]).all()


class TestScoring:
    def test_perfect_prediction(self):
        truth = np.array([[0, 1, 2], [1, 0, 2]])
        score = score_segmentation(truth, truth, lesion_code=1)
        assert score.recall == 1.0 and score.precision == 1.0 and score.dice == 1.0
        assert score.false_positive_rate == 0.0

    def test_partial_prediction(self):
        truth = np.array([0, 0, 1, 1, 1, 2])
        prediction = np.array([1, 0, 1, 1, 0, 2])
        score = score_segmentation(prediction, truth, lesion_code=1)
        assert score.true_positives == 2 and score.false_positives == 1 and score.false_negatives == 1
        assert score.recall == pytest.approx(2 / 3)
        assert score.precision == pytest.approx(2 / 3)
        assert score.false_positive_rate == pytest.approx(1 / 2)

    def test_evaluation_mask_restricts_false_positives(self):
        truth = np.zeros(4, dtype=int)
        prediction = np.array([1, 1, 0, 0])
        score = score_segmentation(prediction, truth, lesion_code=1, evaluation_mask=np.array([1, 0, 1, 0], bool))
        assert score.false_positives == 1 and score.evaluated_normal_voxels == 2


class TestCohortGeneration:
    @pytest.fixture(scope="class")
    def cohort(self, tmp_path_factory):
        spec = CohortSpec(centers={1: "A", 2: "B"}, healthy_per_center=1, patients_per_center=1, seed=7)
        return generate_cohort(spec, tmp_path_factory.mktemp("phantoms"))

    def test_exam_identifiers_are_parsable(self, cohort):
        assert len(cohort.exams) == 4
        for exam in cohort.exams:
            subject_id = MRIExamId(exam.exam_id).to_subject_id()
            assert subject_id.center_id == exam.center_id
            assert subject_id.subject_type == exam.subject_type

    def test_expected_files_are_written(self, cohort):
        for exam in cohort.exams:
            assert exam.md_map_path.exists()
            assert (exam.folder / "Atlas1.nii.gz").exists() and (exam.folder / "Atlas2.nii.gz").exists()
            if exam.subject_type == SubjectType.PATIENT:
                assert exam.ground_truth_path.exists()
            else:
                assert exam.ground_truth_path is None and not exam.lesions
        assert cohort.settings_file.exists()

    def test_csv_files_match_importer_formats(self, cohort):
        with open(cohort.centers_csv, newline="") as file:
            rows = list(csv.DictReader(file))
        assert [row["id"] for row in rows] == ["1", "2"]
        with open(cohort.atlases_csv, newline="") as file:
            atlas_rows = list(csv.reader(file))
        assert [int(row[0]) for row in atlas_rows] == [1, 2]
        assert all(int(label) > 0 for row in atlas_rows for label in row[2:])

    def test_ground_truth_volumes_are_consistent(self, cohort):
        with open(cohort.output_dir / "ground_truth.csv", newline="") as file:
            rows = {(row["mri_exam_id"], row["abnormal_value_type"]): float(row["volume_ml"])
                    for row in csv.DictReader(file)}
        for exam in cohort.patients:
            ground_truth = cohort.load_ground_truth(exam)
            for kind in LesionKind:
                voxels = np.count_nonzero(ground_truth == kind.ground_truth_value)
                expected = voxels * cohort.spec.geometry.voxel_volume_ml
                assert rows[(exam.exam_id, kind.abnormal_value_type.value)] == pytest.approx(expected, abs=1e-3)
                assert exam.lesion_volumes_ml[kind] == pytest.approx(expected)

    def test_nifti_headers_carry_voxel_size(self, cohort):
        image = nib.load(str(cohort.exams[0].md_map_path))
        assert tuple(image.header.get_zooms()) == pytest.approx((3.0, 3.0, 3.0))
        assert image.get_data_dtype() == np.float32

    def test_generation_is_deterministic(self, tmp_path):
        spec = CohortSpec(centers={1: "A"}, healthy_per_center=1, patients_per_center=1, seed=11)
        first = generate_cohort(spec, tmp_path / "first")
        second = generate_cohort(spec, tmp_path / "second")
        for exam_a, exam_b in zip(first.exams, second.exams, strict=True):
            assert exam_a.exam_id == exam_b.exam_id
            assert np.array_equal(np.asarray(nib.load(str(exam_a.md_map_path)).dataobj),
                                  np.asarray(nib.load(str(exam_b.md_map_path)).dataobj))
        assert Path(first.settings_file).read_text() != Path(second.settings_file).read_text()  # paths differ
