"""
Insertion of realistic diffusion lesions into healthy MD maps.

The recipe follows the *realistic TBI phantoms* of Mistral et al.
(Front. Neurol. 2022, doi:10.3389/fneur.2021.740603): lesions are drawn in
the parenchyma, MD is multiplied by a coefficient in 0.41-0.91 (low MD,
cytotoxic oedema) or 1.10-2.10 (high MD, vasogenic oedema), and the
modified map is smoothed with a 3 mm Gaussian filter to match the
appearance of post-traumatic oedema. Only the MD map is modified, the
ground truth being the unsmoothed lesion mask. In that study the inserted
lesions amounted to 2-4 % of the brain volume (mean 31 ml).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Sequence, Tuple

import numpy as np

from oxytcmri.domain.entities.mri import AbnormalValueType
from oxytcmri.tests.phantoms.anatomy import TissueModel, Vector, ellipsoid_mask
from oxytcmri.tests.phantoms.diffusivity import gaussian_smooth

FWHM_TO_SIGMA = 1.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))
LESION_SMOOTHING_FWHM_MM = 3.0
"""Half-width of the Gaussian filter applied to inserted lesions (Mistral et al.)."""


class LesionKind(Enum):
    """Type of diffusion abnormality, with the coefficient range of Mistral et al."""

    LOW_MD = (0.41, 0.91)
    HIGH_MD = (1.10, 2.10)

    @property
    def coefficient_range(self) -> Tuple[float, float]:
        """Admissible range of the multiplicative MD coefficient."""
        return self.value

    @property
    def abnormal_value_type(self) -> AbnormalValueType:
        """Domain counterpart of this lesion kind."""
        return AbnormalValueType.LOW if self is LesionKind.LOW_MD else AbnormalValueType.HIGH

    @property
    def ground_truth_value(self) -> int:
        """Integer stored in ground-truth NIfTI files (same encoding as the pipeline output)."""
        return self.abnormal_value_type.to_integer()


@dataclass(frozen=True)
class Blob:
    """One ellipsoidal component of a lesion, in millimetres."""

    center: Vector
    semi_axes: Vector
    rotation: Tuple[Tuple[float, float, float], ...] = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


@dataclass
class Lesion:
    """
    A lesion made of overlapping ellipsoidal blobs.

    Attributes
    ----------
    kind : LesionKind
        Low or high MD abnormality.
    coefficient : float
        Multiplicative factor applied to MD inside the lesion.
    blobs : List[Blob]
        Ellipsoids whose union defines the lesion.
    """

    kind: LesionKind
    coefficient: float
    blobs: List[Blob] = field(default_factory=list)

    def __post_init__(self) -> None:
        low, high = self.kind.coefficient_range
        if not low <= self.coefficient <= high:
            raise ValueError(f"Coefficient {self.coefficient} outside {self.kind.name} range {low}-{high}")

    def rasterise(self, model: TissueModel) -> np.ndarray:
        """Boolean mask of the lesion restricted to the parenchyma."""
        coords = model.geometry.coordinates_mm()
        mask = np.zeros(model.geometry.shape, dtype=bool)
        for blob in self.blobs:
            mask |= ellipsoid_mask(coords, blob.center, blob.semi_axes, np.asarray(blob.rotation))
        return mask & model.parenchyma_mask


def random_rotation(rng: np.random.Generator) -> np.ndarray:
    """Uniformly distributed random 3-D rotation matrix (QR of a Gaussian matrix)."""
    q, r = np.linalg.qr(rng.normal(size=(3, 3)))
    return q * np.sign(np.diag(r))


def sample_lesion(rng: np.random.Generator,
                  center: Vector,
                  kind: LesionKind,
                  radius_range_mm: Tuple[float, float] = (6.0, 18.0),
                  max_blobs: int = 3) -> Lesion:
    """
    Draw one irregular lesion around a centre.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded random generator.
    center : Vector
        Centre of the main blob in millimetres.
    kind : LesionKind
        Low or high MD lesion; the coefficient is drawn uniformly in its range.
    radius_range_mm : tuple of float
        Range of the semi-axes of each blob.
    max_blobs : int
        Maximum number of overlapping ellipsoids.
    """
    coefficient = float(rng.uniform(*kind.coefficient_range))
    blobs: List[Blob] = []
    for _ in range(int(rng.integers(1, max_blobs + 1))):
        semi_axes = tuple(rng.uniform(*radius_range_mm, size=3))
        offset = rng.normal(scale=0.4 * np.mean(semi_axes), size=3)
        blobs.append(Blob(center=tuple(np.asarray(center) + offset),  # type: ignore[arg-type]
                          semi_axes=semi_axes,  # type: ignore[arg-type]
                          rotation=tuple(map(tuple, random_rotation(rng)))))  # type: ignore[arg-type]
    return Lesion(kind=kind, coefficient=coefficient, blobs=blobs)


def sample_lesions(model: TissueModel,
                   rng: np.random.Generator,
                   target_brain_fraction: float | None = None,
                   high_md_probability: float = 0.65,
                   max_lesions: int = 6) -> List[Lesion]:
    """
    Draw a set of non-overlapping lesions covering a target fraction of the brain.

    Parameters
    ----------
    model : TissueModel
        Anatomy in which lesions are placed (parenchyma only).
    rng : np.random.Generator
        Seeded random generator.
    target_brain_fraction : float, optional
        Fraction of the brain volume to cover; drawn uniformly in 2-4 % if omitted,
        as in the phantoms of Mistral et al.
    high_md_probability : float
        Probability that a lesion is of high-MD type. High MD lesions dominated
        the lesion load in the trial patients (41 ml vs 7 ml median).
    max_lesions : int
        Upper bound on the number of lesions.

    Returns
    -------
    List[Lesion]
        The sampled lesions, whose masks do not overlap.
    """
    if target_brain_fraction is None:
        target_brain_fraction = float(rng.uniform(0.02, 0.04))
    target_voxels = target_brain_fraction * model.brain_mask.sum()

    parenchyma_indices = np.argwhere(model.parenchyma_mask)
    coords = model.geometry.coordinates_mm()
    occupied = np.zeros(model.geometry.shape, dtype=bool)
    lesions: List[Lesion] = []
    attempts = 0
    while occupied.sum() < target_voxels and len(lesions) < max_lesions and attempts < 50:
        attempts += 1
        seed_voxel = parenchyma_indices[rng.integers(len(parenchyma_indices))]
        center = tuple(float(axis[tuple(seed_voxel)]) for axis in coords)
        kind = LesionKind.HIGH_MD if rng.uniform() < high_md_probability else LesionKind.LOW_MD
        lesion = sample_lesion(rng, center, kind)  # type: ignore[arg-type]
        mask = lesion.rasterise(model)
        if mask.sum() == 0 or (mask & occupied).any():
            continue
        occupied |= mask
        lesions.append(lesion)
    return lesions


def apply_lesions(md_map: np.ndarray,
                  lesions: Sequence[Lesion],
                  model: TissueModel) -> Tuple[np.ndarray, np.ndarray]:
    """
    Insert lesions into a healthy MD map.

    Parameters
    ----------
    md_map : np.ndarray
        Healthy MD map in mm²/s.
    lesions : Sequence[Lesion]
        Lesions to insert.
    model : TissueModel
        Anatomy of the map (used to confine lesions to the parenchyma).

    Returns
    -------
    tuple of np.ndarray
        ``(lesioned_md_map, ground_truth)`` where ``ground_truth`` holds 0 for
        normal voxels and the pipeline's integer encoding of HIGH or LOW elsewhere.
    """
    coefficient = np.ones(model.geometry.shape, dtype=float)
    ground_truth = np.zeros(model.geometry.shape, dtype=np.int16)
    for lesion in lesions:
        mask = lesion.rasterise(model)
        coefficient[mask] = lesion.coefficient
        ground_truth[mask] = lesion.kind.ground_truth_value

    sigma_voxels = LESION_SMOOTHING_FWHM_MM * FWHM_TO_SIGMA / model.geometry.voxel_size_mm
    coefficient = gaussian_smooth(coefficient, sigma_voxels)
    # Only the parenchyma is modified: CSF keeps its original diffusivity.
    coefficient[~model.parenchyma_mask] = 1.0
    return md_map * coefficient, ground_truth


def lesion_volume_ml(ground_truth: np.ndarray, kind: LesionKind, voxel_volume_ml: float) -> float:
    """Ground-truth volume of a lesion type, in millilitres."""
    return float(np.count_nonzero(ground_truth == kind.ground_truth_value)) * voxel_volume_ml
