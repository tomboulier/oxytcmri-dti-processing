"""
Simplified brain anatomy and atlas parcellations for digital phantoms.

The anatomy is a set of nested ellipsoids expressed in millimetres, then
rasterised on a regular voxel grid. It is deliberately crude (no gyri, no
skull) but keeps the features that matter for the lesion pipeline: tissue
classes with distinct diffusivity, cerebrospinal fluid (CSF) next to
parenchyma, and anatomically named regions that atlases can parcellate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

Vector = Tuple[float, float, float]


class Tissue(IntEnum):
    """Tissue classes of the phantom, stored as integer voxel values."""

    BACKGROUND = 0
    CSF = 1
    WHITE_MATTER = 2
    CORTEX = 3
    DEEP_GREY = 4
    CORPUS_CALLOSUM = 5
    VENTRICLE = 6

    @property
    def is_parenchyma(self) -> bool:
        """Whether the tissue is brain parenchyma (where lesions can occur)."""
        return self in (Tissue.WHITE_MATTER, Tissue.CORTEX, Tissue.DEEP_GREY, Tissue.CORPUS_CALLOSUM)


@dataclass(frozen=True)
class PhantomGeometry:
    """
    Voxel grid of the phantom.

    Parameters
    ----------
    voxel_size_mm : float
        Isotropic voxel size in millimetres.
    field_of_view_mm : Vector
        Physical extent of the grid along x, y, z in millimetres. The origin
        of the anatomical coordinates is the centre of the field of view.
    """

    voxel_size_mm: float = 3.0
    field_of_view_mm: Vector = (150.0, 180.0, 144.0)

    @property
    def shape(self) -> Tuple[int, int, int]:
        """Number of voxels along each axis."""
        return tuple(int(round(extent / self.voxel_size_mm)) for extent in self.field_of_view_mm)  # type: ignore

    @property
    def affine(self) -> np.ndarray:
        """NIfTI affine mapping voxel indices to millimetres, centred on the grid."""
        affine = np.eye(4)
        for axis in range(3):
            affine[axis, axis] = self.voxel_size_mm
            affine[axis, 3] = -0.5 * (self.shape[axis] - 1) * self.voxel_size_mm
        return affine

    @property
    def voxel_volume_ml(self) -> float:
        """Volume of one voxel in millilitres."""
        return self.voxel_size_mm ** 3 / 1000.0

    def coordinates_mm(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Physical coordinates (x, y, z) of every voxel centre, in millimetres."""
        axes = [
            (np.arange(size) * self.voxel_size_mm) + self.affine[axis, 3]
            for axis, size in enumerate(self.shape)
        ]
        return np.meshgrid(*axes, indexing="ij")  # type: ignore[return-value]


def ellipsoid_mask(coords: Tuple[np.ndarray, np.ndarray, np.ndarray],
                   center: Vector,
                   semi_axes: Vector,
                   rotation: np.ndarray | None = None) -> np.ndarray:
    """
    Boolean mask of an (optionally rotated) ellipsoid.

    Parameters
    ----------
    coords : tuple of np.ndarray
        Voxel coordinates in millimetres, as returned by ``PhantomGeometry.coordinates_mm``.
    center : Vector
        Centre of the ellipsoid in millimetres.
    semi_axes : Vector
        Semi-axes lengths in millimetres.
    rotation : np.ndarray, optional
        3x3 rotation matrix applied to the ellipsoid (identity if omitted).

    Returns
    -------
    np.ndarray
        Boolean array, True inside the ellipsoid.
    """
    offsets = np.stack([axis - c for axis, c in zip(coords, center, strict=True)], axis=-1)
    if rotation is not None:
        offsets = offsets @ rotation
    normalised = offsets / np.asarray(semi_axes, dtype=float)
    return np.sum(normalised ** 2, axis=-1) <= 1.0


@dataclass
class TissueModel:
    """
    Rasterised anatomy of a phantom.

    Attributes
    ----------
    geometry : PhantomGeometry
        The voxel grid.
    tissue : np.ndarray
        Integer array of ``Tissue`` values, one per voxel.
    regions : Dict[str, np.ndarray]
        Named boolean masks of anatomical structures (e.g. ``"thalamus_left"``),
        used to build atlas parcellations.
    """

    geometry: PhantomGeometry
    tissue: np.ndarray
    regions: Dict[str, np.ndarray] = field(default_factory=dict)

    @property
    def brain_mask(self) -> np.ndarray:
        """Boolean mask of the whole brain (parenchyma and ventricles)."""
        return (self.tissue != Tissue.BACKGROUND) & (self.tissue != Tissue.CSF)

    @property
    def parenchyma_mask(self) -> np.ndarray:
        """Boolean mask of the brain parenchyma (every tissue where lesions may occur)."""
        return np.isin(self.tissue, [t for t in Tissue if t.is_parenchyma])

    @property
    def brain_volume_ml(self) -> float:
        """Brain volume in millilitres."""
        return float(self.brain_mask.sum()) * self.geometry.voxel_volume_ml


# Semi-axes of the brain ellipsoid (x: left-right, y: antero-posterior, z: cranio-caudal), in mm.
BRAIN_SEMI_AXES: Vector = (65.0, 80.0, 60.0)
# Thickness of the cortical ribbon and of the peripheral CSF rim, as fractions of the brain radius.
CORTEX_RELATIVE_THICKNESS = 0.12
CSF_RIM_RELATIVE_THICKNESS = 0.06


def build_tissue_model(geometry: Optional[PhantomGeometry] = None) -> TissueModel:
    """
    Build the synthetic anatomy on the given grid.

    The brain is an ellipsoid: its outer shell is cortex, its core is white
    matter. Deep grey nuclei (thalami, striata), the corpus callosum and the
    lateral ventricles are carved inside, and a thin CSF rim surrounds the
    brain to reproduce partial volume with high-diffusivity fluid.

    Parameters
    ----------
    geometry : PhantomGeometry, optional
        Voxel grid on which to rasterise the anatomy (default grid if omitted).

    Returns
    -------
    TissueModel
        Tissue labels and named region masks.
    """
    geometry = geometry or PhantomGeometry()
    coords = geometry.coordinates_mm()
    origin: Vector = (0.0, 0.0, 0.0)

    def scaled(factor: float) -> Vector:
        return tuple(axis * factor for axis in BRAIN_SEMI_AXES)  # type: ignore[return-value]

    brain = ellipsoid_mask(coords, origin, BRAIN_SEMI_AXES)
    inner = ellipsoid_mask(coords, origin, scaled(1.0 - CORTEX_RELATIVE_THICKNESS))
    rim = ellipsoid_mask(coords, origin, scaled(1.0 + CSF_RIM_RELATIVE_THICKNESS))

    tissue = np.full(geometry.shape, int(Tissue.BACKGROUND), dtype=np.int16)
    tissue[rim] = Tissue.CSF
    tissue[brain] = Tissue.CORTEX
    tissue[inner] = Tissue.WHITE_MATTER

    regions: Dict[str, np.ndarray] = {}
    for side, sign in (("left", -1.0), ("right", 1.0)):
        ventricle = ellipsoid_mask(coords, (sign * 12.0, 0.0, 2.0), (7.0, 30.0, 8.0))
        thalamus = ellipsoid_mask(coords, (sign * 12.0, -10.0, -8.0), (9.0, 12.0, 8.0))
        striatum = ellipsoid_mask(coords, (sign * 24.0, 10.0, -2.0), (7.0, 15.0, 10.0))
        regions[f"ventricle_{side}"] = ventricle
        regions[f"thalamus_{side}"] = thalamus & ~ventricle
        regions[f"striatum_{side}"] = striatum & ~ventricle
        tissue[regions[f"thalamus_{side}"]] = Tissue.DEEP_GREY
        tissue[regions[f"striatum_{side}"]] = Tissue.DEEP_GREY

    # The corpus callosum is a flat arch of white matter above the ventricles.
    corpus_callosum = ellipsoid_mask(coords, (0.0, 0.0, 14.0), (30.0, 34.0, 5.0)) & inner
    regions["corpus_callosum"] = corpus_callosum
    tissue[corpus_callosum] = Tissue.CORPUS_CALLOSUM

    for side in ("left", "right"):
        tissue[regions[f"ventricle_{side}"]] = Tissue.VENTRICLE

    x, y, z = coords
    regions["hemisphere_left"] = brain & (x < 0)
    regions["hemisphere_right"] = brain & (x >= 0)
    regions["anterior"] = brain & (y >= 0)
    regions["posterior"] = brain & (y < 0)
    regions["superior"] = brain & (z >= 0)
    regions["inferior"] = brain & (z < 0)

    return TissueModel(geometry=geometry, tissue=tissue, regions=regions)


@dataclass(frozen=True)
class Parcellation:
    """
    An atlas parcellation of the phantom.

    Attributes
    ----------
    atlas_id : int
        Single-digit atlas identifier (the NIfTI file is named ``Atlas{atlas_id}``).
    name : str
        Human-readable name of the atlas.
    labels : np.ndarray
        Integer label per voxel, 0 outside the parcellated regions.
    """

    atlas_id: int
    name: str
    labels: np.ndarray

    @property
    def label_values(self) -> List[int]:
        """Sorted list of the non-zero labels present in the parcellation."""
        return sorted(int(value) for value in np.unique(self.labels) if value != 0)


ParcellationBuilder = Callable[[TissueModel, int], Parcellation]


def hemispheric_parcellation(model: TissueModel, atlas_id: int) -> Parcellation:
    """
    Coarse parcellation: one label per tissue class and hemisphere.

    Labels are ``10 * tissue + hemisphere`` with hemisphere 1 (left) or 2
    (right), plus label 50 for the corpus callosum. Ventricles and CSF are
    left unlabelled, as in the real pipeline where CSF voxels are excluded.
    """
    labels = np.zeros(model.geometry.shape, dtype=np.int16)
    for hemisphere_index, side in enumerate(("left", "right"), start=1):
        hemisphere = model.regions[f"hemisphere_{side}"]
        for tissue in (Tissue.WHITE_MATTER, Tissue.CORTEX, Tissue.DEEP_GREY):
            labels[hemisphere & (model.tissue == tissue)] = 10 * int(tissue) + hemisphere_index
    labels[model.tissue == Tissue.CORPUS_CALLOSUM] = 50
    return Parcellation(atlas_id=atlas_id, name="Hemispheric tissue atlas", labels=labels)


def lobar_parcellation(model: TissueModel, atlas_id: int) -> Parcellation:
    """
    Finer parcellation: tissue classes split by hemisphere and quadrant.

    White matter and cortex are split into antero-posterior and
    cranio-caudal quadrants (labels ``100 * tissue + 10 * hemisphere + quadrant``),
    deep grey nuclei are split into thalamus (label ``4h1``) and striatum
    (``4h2``), and the corpus callosum into anterior (501) and posterior (502)
    parts. This mimics the subdivision of large regions into small
    parcels used by the Potholes and Molehills method.
    """
    labels = np.zeros(model.geometry.shape, dtype=np.int16)
    quadrants = {
        1: model.regions["anterior"] & model.regions["superior"],
        2: model.regions["anterior"] & model.regions["inferior"],
        3: model.regions["posterior"] & model.regions["superior"],
        4: model.regions["posterior"] & model.regions["inferior"],
    }
    for hemisphere_index, side in enumerate(("left", "right"), start=1):
        hemisphere = model.regions[f"hemisphere_{side}"]
        for tissue in (Tissue.WHITE_MATTER, Tissue.CORTEX):
            for quadrant_index, quadrant in quadrants.items():
                voxels = hemisphere & quadrant & (model.tissue == tissue)
                labels[voxels] = 100 * int(tissue) + 10 * hemisphere_index + quadrant_index
        labels[model.regions[f"thalamus_{side}"]] = 100 * int(Tissue.DEEP_GREY) + 10 * hemisphere_index + 1
        labels[model.regions[f"striatum_{side}"]] = 100 * int(Tissue.DEEP_GREY) + 10 * hemisphere_index + 2
    corpus_callosum = model.tissue == Tissue.CORPUS_CALLOSUM
    labels[corpus_callosum & model.regions["anterior"]] = 501
    labels[corpus_callosum & model.regions["posterior"]] = 502
    return Parcellation(atlas_id=atlas_id, name="Lobar tissue atlas", labels=labels)


def grid_parcellation(model: TissueModel, atlas_id: int, block_size_mm: float = 36.0) -> Parcellation:
    """
    Parcellation of the parenchyma into cubic blocks ("molehills").

    Each block of ``block_size_mm`` side gets its own label (``1000 + index``),
    regardless of tissue class. This produces regions with mixed tissue
    distributions, a useful stress test for percentile-based thresholds.
    """
    coords = model.geometry.coordinates_mm()
    block_indices = [np.floor((axis - axis.min()) / block_size_mm).astype(int) for axis in coords]
    blocks_per_axis = [int(index.max()) + 1 for index in block_indices]
    flat_index = (block_indices[0] * blocks_per_axis[1] + block_indices[1]) * blocks_per_axis[2] + block_indices[2]
    labels = np.where(model.parenchyma_mask, 1000 + flat_index, 0).astype(np.int16)
    return Parcellation(atlas_id=atlas_id, name=f"Grid atlas ({block_size_mm:g} mm blocks)", labels=labels)


DEFAULT_PARCELLATIONS: Dict[int, ParcellationBuilder] = {
    1: hemispheric_parcellation,
    2: lobar_parcellation,
}
"""Atlas builders used by default, keyed by atlas identifier."""
