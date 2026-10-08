"""
Phantoms built on the anatomy of a real, openly licensed healthy subject.

This is the closest reproduction of the *realistic TBI phantoms* of Mistral
et al. (2022), who inserted lesions in the MD maps of healthy volunteers.
Starting from a diffusion-weighted acquisition (DWI, b-values, b-vectors),
tissue probability maps and a FreeSurfer-style parcellation, the module:

1. fits the diffusion tensor voxel-wise (ordinary least squares on the
   log-signal, as in Basser et al. 1994) and derives the MD map;
2. builds a ``TissueModel`` and atlas parcellations from the tissue maps and
   the parcellation, so that the lesion and cohort machinery of this package
   applies unchanged;
3. derives healthy "volunteers" by augmenting the subject's MD map (scanner
   scale, bias field, noise), and patients by inserting lesions.

The reference open dataset is the Stanford HARDI subject distributed with
DIPY (``dipy_fetch stanford_hardi stanford_labels stanford_pve_maps``): files
``HARDI150.nii.gz``, ``HARDI150.bval``, ``HARDI150.bvec``, ``pve_csf.nii.gz``,
``pve_gm.nii.gz``, ``pve_wm.nii.gz`` and ``aparc-reduced.nii.gz`` (Rokem et al.,
PLoS ONE 2015, Stanford Digital Repository, Creative Commons Attribution).
Any dataset with the same kinds of files works.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Optional, Tuple, cast

import nibabel as nib
import numpy as np

from oxytcmri.tests.phantoms.anatomy import (
    Parcellation,
    PhantomGeometry,
    Tissue,
    TissueModel,
    hemispheric_parcellation,
)
from oxytcmri.tests.phantoms.cohort import (
    CohortGenerator,
    CohortSpec,
    PhantomCohort,
    summarize,
)
from oxytcmri.tests.phantoms.diffusivity import (
    AcquisitionNoise,
    smooth_bias_field,
)


def load_volume(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Load a NIfTI file as ``(data, affine)``."""
    image = cast(nib.Nifti1Image, nib.load(str(path)))
    return np.asarray(image.get_fdata(), dtype=float), np.asarray(image.affine, dtype=float)


def read_gradient_table(bvals_path: Path, bvecs_path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read FSL-style b-values and b-vectors.

    Returns
    -------
    tuple of np.ndarray
        ``bvals`` of shape ``(n,)`` in s/mm² and unit ``bvecs`` of shape ``(n, 3)``.
    """
    bvals = np.loadtxt(bvals_path).ravel()
    bvecs = np.loadtxt(bvecs_path)
    if bvecs.shape[0] == 3:
        bvecs = bvecs.T
    norms = np.linalg.norm(bvecs, axis=1)
    bvecs = np.divide(bvecs, norms[:, None], out=np.zeros_like(bvecs), where=norms[:, None] > 0)
    return bvals, bvecs


def tensor_design_matrix(bvals: np.ndarray, bvecs: np.ndarray) -> np.ndarray:
    """
    Design matrix of the log-linear tensor model.

    For each gradient, ``log(S) = log(S0) - b * g^T D g``; with ``D`` symmetric
    this is linear in ``(Dxx, Dyy, Dzz, Dxy, Dxz, Dyz, log S0)``.
    """
    g = bvecs
    return np.column_stack([
        -bvals * g[:, 0] ** 2, -bvals * g[:, 1] ** 2, -bvals * g[:, 2] ** 2,
        -2 * bvals * g[:, 0] * g[:, 1], -2 * bvals * g[:, 0] * g[:, 2], -2 * bvals * g[:, 1] * g[:, 2],
        np.ones(len(bvals)),
    ])


def fit_mean_diffusivity(dwi: np.ndarray, bvals: np.ndarray, bvecs: np.ndarray,
                         mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Ordinary least-squares tensor fit, returning the mean diffusivity map.

    Parameters
    ----------
    dwi : np.ndarray
        Diffusion-weighted signal of shape ``(x, y, z, n)``.
    bvals : np.ndarray
        b-values in s/mm².
    bvecs : np.ndarray
        Unit gradient directions, shape ``(n, 3)``.
    mask : np.ndarray, optional
        Voxels to fit; the rest is set to 0.

    Returns
    -------
    np.ndarray
        MD in mm²/s, clipped to ``[0, 5e-3]`` to discard non-physical fits.
    """
    design = tensor_design_matrix(bvals, bvecs)
    pseudo_inverse = np.linalg.pinv(design)
    signal = np.asarray(dwi, dtype=float)
    mask = np.ones(signal.shape[:3], dtype=bool) if mask is None else mask.astype(bool)
    log_signal = np.log(np.clip(signal[mask], 1e-6, None))  # shape (voxels, n)
    coefficients = log_signal @ pseudo_inverse.T  # shape (voxels, 7)
    md = np.zeros(signal.shape[:3], dtype=float)
    md[mask] = coefficients[:, :3].mean(axis=1)
    return np.clip(md, 0.0, 5e-3)


@dataclass(frozen=True)
class SubjectFiles:
    """Input files of one healthy subject."""

    dwi: Path
    bvals: Path
    bvecs: Path
    pve_csf: Path
    pve_gm: Path
    pve_wm: Path
    parcellation: Path

    @classmethod
    def stanford_hardi(cls, folder: Path) -> SubjectFiles:
        """File names of the Stanford HARDI subject as fetched by DIPY."""
        return cls(dwi=folder / "HARDI150.nii.gz", bvals=folder / "HARDI150.bval", bvecs=folder / "HARDI150.bvec",
                   pve_csf=folder / "pve_csf.nii.gz", pve_gm=folder / "pve_gm.nii.gz",
                   pve_wm=folder / "pve_wm.nii.gz", parcellation=folder / "aparc-reduced.nii.gz")


def tissue_model_from_probability_maps(pve_csf: np.ndarray, pve_gm: np.ndarray, pve_wm: np.ndarray,
                                       geometry: PhantomGeometry) -> TissueModel:
    """
    Tissue model from partial-volume (probability) maps.

    Each voxel inside the head takes its most probable tissue: CSF, cortex
    (all grey matter) or white matter. Ventricles are not separated from the
    other CSF, as neither receives lesions. Hemispheres are split by the sign
    of the x coordinate (RAS convention).
    """
    probabilities = np.stack([pve_csf, pve_gm, pve_wm], axis=-1)
    inside_head = probabilities.sum(axis=-1) > 0.5
    most_probable = probabilities.argmax(axis=-1)

    tissue = np.full(geometry.shape, int(Tissue.BACKGROUND), dtype=np.int16)
    tissue[inside_head & (most_probable == 0)] = Tissue.CSF
    tissue[inside_head & (most_probable == 1)] = Tissue.CORTEX
    tissue[inside_head & (most_probable == 2)] = Tissue.WHITE_MATTER

    x, _, _ = geometry.coordinates_mm()
    parenchyma = np.isin(tissue, [Tissue.CORTEX, Tissue.WHITE_MATTER])
    regions = {"hemisphere_left": parenchyma & (x < 0), "hemisphere_right": parenchyma & (x >= 0)}
    return TissueModel(geometry=geometry, tissue=tissue, regions=regions)


def parcellation_from_labels(labels: np.ndarray, model: TissueModel, atlas_id: int,
                             name: str = "FreeSurfer parcellation") -> Parcellation:
    """Atlas from an integer label volume, restricted to the parenchyma of the tissue model."""
    restricted = np.where(model.parenchyma_mask, np.rint(labels).astype(np.int16), 0)
    return Parcellation(atlas_id=atlas_id, name=name, labels=restricted)


@dataclass
class RealSubject:
    """
    A real healthy subject prepared for phantom generation.

    Attributes
    ----------
    md_map : np.ndarray
        Fitted MD map in mm²/s.
    model : TissueModel
        Tissue classes derived from the probability maps.
    parcellations : Dict[int, Parcellation]
        Atlases keyed by identifier: the FreeSurfer-style parcellation (1) and
        the hemispheric tissue atlas (2).
    """

    md_map: np.ndarray
    model: TissueModel
    parcellations: Dict[int, Parcellation]

    @classmethod
    def from_files(cls, files: SubjectFiles) -> RealSubject:
        """Fit the tensor and derive the tissue model and atlases from the subject's files."""
        dwi, affine = load_volume(files.dwi)
        geometry = PhantomGeometry.from_image(dwi.shape[:3], affine)
        pve_csf, pve_gm, pve_wm = (load_volume(path)[0] for path in (files.pve_csf, files.pve_gm, files.pve_wm))
        model = tissue_model_from_probability_maps(pve_csf, pve_gm, pve_wm, geometry)

        bvals, bvecs = read_gradient_table(files.bvals, files.bvecs)
        md_map = fit_mean_diffusivity(dwi, bvals, bvecs, mask=model.tissue != Tissue.BACKGROUND)

        labels, _ = load_volume(files.parcellation)
        parcellations = {1: parcellation_from_labels(labels, model, 1),
                         2: hemispheric_parcellation(model, 2)}
        return cls(md_map=md_map, model=model, parcellations=parcellations)


def augment_md_map(md_map: np.ndarray, model: TissueModel, rng: np.random.Generator,
                   center_scale: float = 1.0, noise: Optional[AcquisitionNoise] = None) -> np.ndarray:
    """
    Derive a new "subject" from a real MD map.

    The map is rescaled (scanner and subject factors), modulated by a smooth
    bias field and corrupted by voxel-wise noise, as healthy maps are in
    ``synthesize_md_map``; the anatomy itself is unchanged.
    """
    noise = noise or AcquisitionNoise()
    subject_scale = rng.normal(loc=1.0, scale=noise.subject_scale_sd)
    bias = smooth_bias_field(model.geometry.shape, noise.bias_field_fraction, rng)
    voxel_noise = rng.normal(loc=0.0, scale=noise.voxel_noise_fraction, size=md_map.shape)
    augmented = md_map * center_scale * subject_scale * bias * (1.0 + voxel_noise)
    augmented[model.tissue == Tissue.BACKGROUND] = 0.0
    return np.clip(augmented, 0.0, None)


def generate_cohort_from_subject(subject: RealSubject, spec: CohortSpec, output_dir: Path) -> PhantomCohort:
    """
    Generate a phantom cohort whose anatomy is that of a real subject.

    Healthy volunteers are augmented copies of the subject's MD map and
    patients additionally carry inserted lesions; the atlases are the
    subject's parcellation and a hemispheric tissue atlas.

    Parameters
    ----------
    subject : RealSubject
        Prepared subject (see ``RealSubject.from_files``).
    spec : CohortSpec
        Cohort layout; its ``geometry`` is replaced by the subject's grid.
    output_dir : Path
        Where to write the cohort.
    """
    spec = replace(spec, geometry=subject.model.geometry)

    def md_source(rng: np.random.Generator, center_scale: float) -> np.ndarray:
        return augment_md_map(subject.md_map, subject.model, rng, center_scale, spec.noise)

    generator = CohortGenerator(spec, output_dir, model=subject.model,
                                parcellations=list(subject.parcellations.values()), md_source=md_source)
    return generator.generate()


def main() -> None:
    """Command line entry point: build a cohort from a Stanford-HARDI-like subject folder."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate DTI phantoms on the anatomy of a real healthy subject.")
    parser.add_argument("--subject-dir", type=Path, required=True,
                        help="folder with the Stanford HARDI files fetched by DIPY (~/.dipy/stanford_hardi)")
    parser.add_argument("--output", type=Path, default=Path("data/phantoms_real"), help="output folder")
    parser.add_argument("--centers", type=int, default=2, help="number of centres")
    parser.add_argument("--healthy", type=int, default=3, help="healthy volunteers per centre")
    parser.add_argument("--patients", type=int, default=1, help="patients per centre")
    parser.add_argument("--seed", type=int, default=2024, help="random seed")
    args = parser.parse_args()

    subject = RealSubject.from_files(SubjectFiles.stanford_hardi(args.subject_dir))
    centers = {index: f"Centre {chr(ord('A') + index - 1)}" for index in range(1, args.centers + 1)}
    scales = {index: 1.0 + 0.04 * ((index - 1) % 3 - 1) for index in centers}
    spec = CohortSpec(centers=centers, healthy_per_center=args.healthy, patients_per_center=args.patients,
                      center_scales=scales, seed=args.seed)
    cohort = generate_cohort_from_subject(subject, spec, args.output)
    print(summarize(cohort))
    print(f"\nFiles written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
