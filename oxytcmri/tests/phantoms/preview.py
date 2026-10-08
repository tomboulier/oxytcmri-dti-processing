"""
Visual check of a generated phantom: PNG montage of axial slices.

Each row is one axial slice; the columns are the MD map, the ground-truth
lesions (red: high MD, green: low MD, as in Mistral et al.), the pipeline
segmentation when present, and the atlases. The PNG is written with the
standard library only, so no plotting dependency is required.

Usage::

    uv run python -m oxytcmri.tests.phantoms.preview data/phantoms 01_81p_mr_261024 preview.png
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path
from typing import Dict, Iterable, Tuple, cast

import nibabel as nib
import numpy as np

from oxytcmri.domain.entities.mri import AbnormalValueType

LESION_COLOURS: Dict[int, Tuple[int, int, int]] = {
    AbnormalValueType.HIGH.to_integer(): (255, 60, 60),
    AbnormalValueType.LOW.to_integer(): (60, 220, 60),
}
MD_DISPLAY_MAX = 1.2e-3  # mm²/s, saturates CSF so that parenchyma contrast is visible


def write_png(path: Path, rgb: np.ndarray) -> None:
    """Write an ``(height, width, 3)`` uint8 array as an RGB PNG file."""
    height, width, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[row].tobytes() for row in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9))
                     + chunk(b"IEND", b""))


def grey_panel(md_slice: np.ndarray) -> np.ndarray:
    """Grey-level RGB panel of an MD slice."""
    grey = np.clip(md_slice / MD_DISPLAY_MAX * 255, 0, 255).astype(np.uint8)
    return np.stack([grey] * 3, axis=-1)


def overlay_panel(md_slice: np.ndarray, labels: np.ndarray, alpha: float = 0.55) -> np.ndarray:
    """MD slice with coloured lesion labels blended on top."""
    panel = grey_panel(md_slice).astype(float)
    for code, colour in LESION_COLOURS.items():
        mask = labels == code
        panel[mask] = (1 - alpha) * panel[mask] + alpha * np.asarray(colour)
    return panel.astype(np.uint8)


def atlas_panel(labels: np.ndarray) -> np.ndarray:
    """Atlas slice with one random colour per label (black outside)."""
    rng = np.random.default_rng(0)
    panel = np.zeros(labels.shape + (3,), dtype=np.uint8)
    for value in np.unique(labels):
        if value != 0:
            panel[labels == value] = rng.integers(40, 255, size=3)
    return panel


def load(path: Path) -> np.ndarray:
    """Load a NIfTI volume as a numpy array."""
    return np.asarray(cast(nib.Nifti1Image, nib.load(str(path))).get_fdata())


def render_exam(cohort_dir: Path, exam_id: str, output: Path,
                slices: Iterable[int] | None = None, upscale: int = 4) -> None:
    """
    Render the montage of one exam to a PNG file.

    Parameters
    ----------
    cohort_dir : Path
        Folder written by the cohort generator.
    exam_id : str
        Exam identifier (sub-folder of ``nifti``).
    output : Path
        PNG file to write.
    slices : iterable of int, optional
        Axial slice indices; three evenly spaced slices by default.
    upscale : int
        Integer zoom factor applied to each panel.
    """
    exam_dir = cohort_dir / "nifti" / exam_id
    md = load(exam_dir / "MD_map.nii.gz")
    atlases = [load(path).astype(int) for path in sorted(exam_dir.glob("Atlas*.nii.gz"))]
    ground_truth_path = cohort_dir / "ground_truth" / f"{exam_id}_MD_lesions.nii.gz"
    ground_truth = load(ground_truth_path).astype(int) if ground_truth_path.exists() else np.zeros_like(md, dtype=int)
    segmentation_path = exam_dir / "MD_segmentation.nii.gz"
    segmentation = np.rint(load(segmentation_path)).astype(int) if segmentation_path.exists() else None

    depth = md.shape[2]
    slice_indices = list(slices) if slices is not None else [depth // 3, depth // 2, 2 * depth // 3]

    def axial(volume: np.ndarray, index: int) -> np.ndarray:
        return volume[:, :, index].T[::-1]  # anterior at the top

    rows = []
    for index in slice_indices:
        panels = [grey_panel(axial(md, index)), overlay_panel(axial(md, index), axial(ground_truth, index))]
        if segmentation is not None:
            panels.append(overlay_panel(axial(md, index), axial(segmentation, index)))
        panels.extend(atlas_panel(axial(atlas, index)) for atlas in atlases)
        rows.append(np.concatenate([np.repeat(np.repeat(p, upscale, 0), upscale, 1) for p in panels], axis=1))
    write_png(output, np.concatenate(rows, axis=0))


def main(argv: list[str]) -> None:
    """Command line entry point."""
    if len(argv) != 3:
        raise SystemExit("usage: python -m oxytcmri.tests.phantoms.preview <cohort_dir> <exam_id> <output.png>")
    render_exam(Path(argv[0]), argv[1], Path(argv[2]))
    print(f"Preview written to {argv[2]}")


if __name__ == "__main__":
    main(sys.argv[1:])
