"""
Voxel-wise scores of a lesion segmentation against the phantom ground truth.

The metrics are those used by Mistral et al. (2022) to compare automated
and manual delineations: Dice, precision and recall (sensitivity).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SegmentationScore:
    """
    Confusion counts of one lesion type, restricted to an evaluation mask.

    Attributes
    ----------
    true_positives : int
        Voxels of the type in both prediction and ground truth.
    false_positives : int
        Voxels predicted of the type but normal in the ground truth.
    false_negatives : int
        Ground-truth voxels of the type missed by the prediction.
    evaluated_normal_voxels : int
        Normal voxels of the ground truth inside the evaluation mask.
    """

    true_positives: int
    false_positives: int
    false_negatives: int
    evaluated_normal_voxels: int

    @property
    def recall(self) -> float:
        """Sensitivity: fraction of ground-truth lesion voxels detected."""
        return _ratio(self.true_positives, self.true_positives + self.false_negatives)

    @property
    def precision(self) -> float:
        """Fraction of detected voxels that are true lesion voxels."""
        return _ratio(self.true_positives, self.true_positives + self.false_positives)

    @property
    def dice(self) -> float:
        """Dice similarity coefficient between prediction and ground truth."""
        return _ratio(2 * self.true_positives, 2 * self.true_positives + self.false_positives + self.false_negatives)

    @property
    def false_positive_rate(self) -> float:
        """Fraction of normal voxels (inside the evaluation mask) wrongly detected."""
        return _ratio(self.false_positives, self.evaluated_normal_voxels)


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def score_segmentation(prediction: np.ndarray,
                       ground_truth: np.ndarray,
                       lesion_code: int,
                       evaluation_mask: np.ndarray | None = None) -> SegmentationScore:
    """
    Score the prediction of one lesion type.

    Parameters
    ----------
    prediction : np.ndarray
        Integer segmentation produced by the pipeline (0 normal, 1 high MD, 2 low MD).
    ground_truth : np.ndarray
        Integer ground truth with the same encoding.
    lesion_code : int
        Code of the lesion type to score (``AbnormalValueType.to_integer()``).
    evaluation_mask : np.ndarray, optional
        Boolean mask restricting false positives to the voxels the pipeline can
        actually label (e.g. the atlas-covered parenchyma). Defaults to everywhere.

    Returns
    -------
    SegmentationScore
        Confusion counts from which recall, precision, Dice and the false
        positive rate are derived.
    """
    if prediction.shape != ground_truth.shape:
        raise ValueError(f"Shape mismatch: prediction {prediction.shape} vs ground truth {ground_truth.shape}")
    evaluated = np.ones(ground_truth.shape, dtype=bool) if evaluation_mask is None else evaluation_mask.astype(bool)
    predicted = (prediction == lesion_code) & evaluated
    truth = ground_truth == lesion_code
    normal = (ground_truth == 0) & evaluated
    return SegmentationScore(
        true_positives=int((predicted & truth).sum()),
        false_positives=int((predicted & ~truth).sum()),
        false_negatives=int((truth & ~predicted).sum()),
        evaluated_normal_voxels=int(normal.sum()),
    )
