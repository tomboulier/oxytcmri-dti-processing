"""
Synthesis of mean diffusivity (MD) maps from a tissue model.

Reference MD values come from diffusion MRI of healthy adults, expressed in
mm²/s (Helenius et al., "Diffusion-weighted MR imaging in normal human brains
in various age groups", AJNR 2002, PMID 11847041): white matter ≈ 0.70e-3,
cortical grey matter ≈ 0.89e-3, deep grey nuclei ≈ 0.75e-3 and CSF ≈ 3.0e-3 mm²/s.

The synthesised maps include the main sources of variability seen in a
multi-centre study: a scanner-dependent scale per centre, a per-subject
scale, a smooth bias field, partial volume at tissue interfaces and
voxel-wise noise.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

import numpy as np

from oxytcmri.tests.phantoms.anatomy import Tissue, TissueModel

REFERENCE_MD_MM2_PER_S: Dict[Tissue, float] = {
    Tissue.BACKGROUND: 0.0,
    Tissue.CSF: 3.0e-3,
    Tissue.VENTRICLE: 3.0e-3,
    Tissue.WHITE_MATTER: 0.70e-3,
    Tissue.CORPUS_CALLOSUM: 0.70e-3,
    Tissue.CORTEX: 0.89e-3,
    Tissue.DEEP_GREY: 0.75e-3,
}
"""Typical mean diffusivity of each tissue class in healthy adults (mm²/s)."""


@dataclass(frozen=True)
class AcquisitionNoise:
    """
    Variability parameters of a synthesised MD map.

    Parameters
    ----------
    voxel_noise_fraction : float
        Standard deviation of the voxel-wise Gaussian noise, as a fraction of
        the local MD value.
    bias_field_fraction : float
        Peak amplitude of the smooth multiplicative bias field, as a fraction.
    subject_scale_sd : float
        Standard deviation of the per-subject multiplicative scale.
    partial_volume_sigma_voxels : float
        Standard deviation (in voxels) of the Gaussian blur applied to the
        tissue map to simulate partial volume at interfaces.
    """

    voxel_noise_fraction: float = 0.05
    bias_field_fraction: float = 0.03
    subject_scale_sd: float = 0.02
    partial_volume_sigma_voxels: float = 0.5


def gaussian_kernel_1d(sigma: float, truncate: float = 3.0) -> np.ndarray:
    """
    Normalised 1-D Gaussian kernel.

    Parameters
    ----------
    sigma : float
        Standard deviation in samples.
    truncate : float
        Kernel half-width in multiples of ``sigma``.
    """
    radius = max(1, int(np.ceil(truncate * sigma)))
    offsets = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    return kernel / kernel.sum()


def gaussian_smooth(volume: np.ndarray, sigma_voxels: float | Sequence[float]) -> np.ndarray:
    """
    Separable Gaussian smoothing of a 3-D volume (pure numpy, no SciPy needed).

    Parameters
    ----------
    volume : np.ndarray
        Input 3-D array.
    sigma_voxels : float or sequence of float
        Standard deviation of the Gaussian in voxels, either one value for all
        axes or one per axis. A value of 0 leaves that axis untouched.

    Returns
    -------
    np.ndarray
        Smoothed volume, with edges handled by nearest-value padding.
    """
    smoothed = np.asarray(volume, dtype=float).copy()
    sigmas = np.broadcast_to(np.asarray(sigma_voxels, dtype=float).ravel(), (3,))
    for axis, sigma in enumerate(sigmas):
        if sigma > 0:
            smoothed = _smooth_along_axis(smoothed, axis, gaussian_kernel_1d(sigma))
    return smoothed


def _smooth_along_axis(volume: np.ndarray, axis: int, kernel: np.ndarray) -> np.ndarray:
    """Convolve every line of ``volume`` along ``axis`` with ``kernel``, padding edges with the nearest value."""
    radius = len(kernel) // 2
    padded = np.pad(volume, [(radius, radius) if a == axis else (0, 0) for a in range(3)], mode="edge")
    return np.apply_along_axis(lambda line: np.convolve(line, kernel, mode="valid"), axis, padded)


def smooth_bias_field(shape: tuple[int, int, int], amplitude: float, rng: np.random.Generator) -> np.ndarray:
    """
    Smooth multiplicative field in ``[1 - amplitude, 1 + amplitude]``.

    The field is a random low-resolution grid upsampled by Gaussian
    smoothing, which mimics coil sensitivity or gradient non-linearity.
    """
    if amplitude <= 0:
        return np.ones(shape)
    coarse = rng.normal(size=shape)
    field = gaussian_smooth(coarse, sigma_voxels=max(shape) / 6.0)
    field = field / (np.abs(field).max() + 1e-12)
    return 1.0 + amplitude * field


def synthesize_md_map(model: TissueModel,
                      rng: np.random.Generator,
                      center_scale: float = 1.0,
                      noise: Optional[AcquisitionNoise] = None) -> np.ndarray:
    """
    Synthesise a healthy MD map (mm²/s) from a tissue model.

    Parameters
    ----------
    model : TissueModel
        The anatomy to render.
    rng : np.random.Generator
        Seeded random generator (drives subject scale, bias field and noise).
    center_scale : float
        Multiplicative factor modelling the scanner of the acquisition centre.
    noise : AcquisitionNoise, optional
        Variability parameters (defaults if omitted).

    Returns
    -------
    np.ndarray
        Float array of MD values in mm²/s, zero outside the head.
    """
    noise = noise or AcquisitionNoise()
    reference = np.zeros(model.geometry.shape, dtype=float)
    for tissue, value in REFERENCE_MD_MM2_PER_S.items():
        reference[model.tissue == tissue] = value

    # Partial volume: blur the piecewise-constant map at tissue interfaces.
    blurred = gaussian_smooth(reference, noise.partial_volume_sigma_voxels)
    inside_head = model.tissue != Tissue.BACKGROUND
    blurred[~inside_head] = 0.0

    subject_scale = rng.normal(loc=1.0, scale=noise.subject_scale_sd)
    bias = smooth_bias_field(model.geometry.shape, noise.bias_field_fraction, rng)
    md = blurred * center_scale * subject_scale * bias

    voxel_noise = rng.normal(loc=0.0, scale=noise.voxel_noise_fraction, size=md.shape)
    md = md * (1.0 + voxel_noise)
    md[~inside_head] = 0.0
    return np.clip(md, 0.0, None)
