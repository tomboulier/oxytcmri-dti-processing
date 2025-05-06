from abc import ABC, abstractmethod
from typing import List

from oxytcmri.domain.entities.mri import MRIData


class SegmentationMerger(ABC):
    """
    Abstract interface for merging MRI segmentations.
    This interface respects the dependency inversion principle.
    """

    @abstractmethod
    def merge(self, segmentations: List[MRIData]) -> MRIData:
        """
        Merges multiple segmentations into a single one.

        Parameters
        ----------
        segmentations : List[MRIData]
            List of segmentations to merge.

        Returns
        -------
        MRIData
            The merged segmentation.

        Raises
        -------
        RuntimeError
            If the segmentations cannot be merged.
        """
