"""
Unit tests of the phantoms built on a real subject's anatomy.

No real data is needed: a Stanford-HARDI-like subject folder is simulated
from the synthetic phantom (isotropic tensor signal, tissue probability maps
and a label volume), which also validates the tensor fit against a known MD.
"""
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from oxytcmri.domain.entities.subject import SubjectType
from oxytcmri.tests.phantoms import (
    CohortSpec,
    PhantomGeometry,
    Tissue,
    build_tissue_model,
)
from oxytcmri.tests.phantoms.anatomy import lobar_parcellation
from oxytcmri.tests.phantoms.diffusivity import gaussian_smooth, synthesize_md_map
from oxytcmri.tests.phantoms.real_anatomy import (
    RealSubject,
    SubjectFiles,
    augment_md_map,
    fit_mean_diffusivity,
    generate_cohort_from_subject,
    read_gradient_table,
    tissue_model_from_probability_maps,
)

# An off-centre, slightly anisotropic grid, unlike the synthetic default, to exercise ``from_image``.
AFFINE = np.array([[2.5, 0, 0, -60.0], [0, 2.5, 0, -75.0], [0, 0, 3.0, -50.0], [0, 0, 0, 1.0]])


def simulate_dwi(md_map: np.ndarray, rng: np.random.Generator, n_directions: int = 30):
    """Isotropic-tensor DWI signal ``S0 * exp(-b * MD)`` with a few b=0 volumes and mild noise."""
    directions = rng.normal(size=(n_directions, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    bvals = np.concatenate([np.zeros(4), np.full(n_directions, 1000.0)])
    bvecs = np.concatenate([np.zeros((4, 3)), directions])
    signal = 1000.0 * np.exp(-bvals[None, None, None, :] * md_map[..., None])
    signal += rng.normal(scale=5.0, size=signal.shape)
    return np.clip(signal, 1.0, None), bvals, bvecs


@pytest.fixture(scope="module")
def subject_folder(tmp_path_factory) -> Path:
    """Write a fake Stanford-like subject (DWI, gradients, PVE maps, labels) from the synthetic phantom."""
    folder = tmp_path_factory.mktemp("fake_subject")
    rng = np.random.default_rng(0)
    geometry = PhantomGeometry.from_image((48, 60, 34), AFFINE)
    model = build_tissue_model(geometry)
    md_map = synthesize_md_map(model, rng)
    dwi, bvals, bvecs = simulate_dwi(md_map, rng)

    def save(name: str, data: np.ndarray) -> None:
        nib.save(nib.Nifti1Image(data.astype(np.float32), AFFINE), str(folder / name))

    save("HARDI150.nii.gz", dwi)
    np.savetxt(folder / "HARDI150.bval", bvals[None, :])
    np.savetxt(folder / "HARDI150.bvec", bvecs.T)
    for name, tissues in (("pve_csf", [Tissue.CSF, Tissue.VENTRICLE]),
                          ("pve_gm", [Tissue.CORTEX, Tissue.DEEP_GREY]),
                          ("pve_wm", [Tissue.WHITE_MATTER, Tissue.CORPUS_CALLOSUM])):
        save(f"{name}.nii.gz", gaussian_smooth(np.isin(model.tissue, tissues).astype(float), 0.4))
    save("aparc-reduced.nii.gz", lobar_parcellation(model, 1).labels.astype(float))
    nib.save(nib.Nifti1Image(md_map.astype(np.float32), AFFINE), str(folder / "true_md.nii.gz"))
    return folder


class TestTensorFit:
    def test_recovers_known_mean_diffusivity(self, subject_folder):
        files = SubjectFiles.stanford_hardi(subject_folder)
        dwi = np.asarray(nib.load(str(files.dwi)).get_fdata())
        true_md = np.asarray(nib.load(str(subject_folder / "true_md.nii.gz")).get_fdata())
        bvals, bvecs = read_gradient_table(files.bvals, files.bvecs)
        fitted = fit_mean_diffusivity(dwi, bvals, bvecs, mask=true_md > 0)
        parenchyma = (true_md > 0.5e-3) & (true_md < 1.2e-3)
        relative_error = np.abs(fitted[parenchyma] - true_md[parenchyma]) / true_md[parenchyma]
        assert np.median(relative_error) < 0.02
        assert fitted[true_md == 0].max() == 0.0

    def test_gradient_table_accepts_both_layouts(self, tmp_path):
        bvecs = np.array([[1.0, 0, 0], [0, 2.0, 0]])
        np.savetxt(tmp_path / "bval", [[0, 1000]])
        np.savetxt(tmp_path / "bvec_rows", bvecs)
        np.savetxt(tmp_path / "bvec_cols", bvecs.T)
        for layout in ("bvec_rows", "bvec_cols"):
            bvals, unit_vectors = read_gradient_table(tmp_path / "bval", tmp_path / layout)
            assert bvals.tolist() == [0, 1000]
            assert np.allclose(np.linalg.norm(unit_vectors, axis=1), 1.0)


class TestTissueModelFromProbabilityMaps:
    def test_tissue_classes_match_the_reference_anatomy(self, subject_folder):
        files = SubjectFiles.stanford_hardi(subject_folder)
        maps = [np.asarray(nib.load(str(path)).get_fdata()) for path in (files.pve_csf, files.pve_gm, files.pve_wm)]
        geometry = PhantomGeometry.from_image(maps[0].shape, AFFINE)
        model = tissue_model_from_probability_maps(*maps, geometry)
        reference = build_tissue_model(geometry)
        assert set(np.unique(model.tissue)) == {Tissue.BACKGROUND, Tissue.CSF, Tissue.CORTEX, Tissue.WHITE_MATTER}
        assert model.parenchyma_mask.sum() == pytest.approx(reference.parenchyma_mask.sum(), rel=0.05)
        reference_csf = np.isin(reference.tissue, [Tissue.CSF, Tissue.VENTRICLE])
        assert (model.tissue == Tissue.CSF).sum() == pytest.approx(reference_csf.sum(), rel=0.1)
        assert model.regions["hemisphere_left"].sum() == pytest.approx(model.regions["hemisphere_right"].sum(), rel=0.1)


class TestRealSubjectCohort:
    @pytest.fixture(scope="class")
    def cohort(self, subject_folder, tmp_path_factory):
        subject = RealSubject.from_files(SubjectFiles.stanford_hardi(subject_folder))
        spec = CohortSpec(centers={1: "A", 2: "B"}, healthy_per_center=2, patients_per_center=1, seed=5)
        return generate_cohort_from_subject(subject, spec, tmp_path_factory.mktemp("real_cohort"))

    def test_grid_comes_from_the_subject(self, cohort):
        assert cohort.spec.geometry.shape == (48, 60, 34)
        image = nib.load(str(cohort.exams[0].md_map_path))
        assert np.allclose(image.affine, AFFINE)
        assert cohort.spec.geometry.voxel_volume_ml == pytest.approx(2.5 * 2.5 * 3.0 / 1000)

    def test_atlases_are_the_subject_parcellation_and_hemispheres(self, cohort):
        assert [p.atlas_id for p in cohort.parcellations] == [1, 2]
        assert len(cohort.parcellations[0].label_values) > len(cohort.parcellations[1].label_values)
        for exam in cohort.exams:
            assert (exam.folder / "Atlas1.nii.gz").exists() and (exam.folder / "Atlas2.nii.gz").exists()

    def test_patients_have_lesions_in_parenchyma(self, cohort):
        patients = cohort.patients
        assert len(patients) == 2
        for exam in patients:
            ground_truth = cohort.load_ground_truth(exam)
            assert np.count_nonzero(ground_truth) > 0
            assert not (ground_truth[~cohort.model.parenchyma_mask] != 0).any()
            assert sum(exam.lesion_volumes_ml.values()) > 10.0

    def test_volunteers_differ_but_share_anatomy(self, cohort):
        volunteers = [exam for exam in cohort.exams if exam.subject_type == SubjectType.HEALTHY_VOLUNTEER]
        first = np.asarray(nib.load(str(volunteers[0].md_map_path)).get_fdata())
        second = np.asarray(nib.load(str(volunteers[1].md_map_path)).get_fdata())
        assert not np.array_equal(first, second)
        assert np.array_equal(first == 0, second == 0)


def test_augment_md_map_keeps_background_and_scale(subject_folder):
    true_md = np.asarray(nib.load(str(subject_folder / "true_md.nii.gz")).get_fdata())
    model = build_tissue_model(PhantomGeometry.from_image(true_md.shape, AFFINE))
    augmented = augment_md_map(true_md, model, np.random.default_rng(1), center_scale=1.1)
    inside = model.brain_mask
    assert (augmented[~inside & (model.tissue == Tissue.BACKGROUND)] == 0).all()
    assert np.median(augmented[inside] / true_md[inside]) == pytest.approx(1.1, rel=0.05)
