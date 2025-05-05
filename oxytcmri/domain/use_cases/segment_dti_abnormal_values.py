"""
This module segments the abnormal values in DTI images using the normative values computed in each center from healthy subjects.
"""
import warnings
from enum import Enum
from typing import Optional, List, Callable, Tuple, cast

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas, DTIMetric, DTIMap, MRIData, VoxelData, AtlasSegmentation
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.monitoring import EventDispatcher
from oxytcmri.domain.ports.repositories import (
    SubjectRepository, MRIExamRepository, AtlasRepository, CenterRepository, RepositoriesRegistry)
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AbnormalValueType(Enum):
    """
    Enum for the type of abnormal values.
    """
    HIGH = "high"
    LOW = "low"


class AbnormalVoxelData(VoxelData[AbnormalValueType]):
    """
    Implementation of VoxelData for abnormal DTI values.

    This class stores abnormal voxels in a dictionary, where only abnormal voxels
    are stored. Voxels not present in the dictionary are considered normal.

    Parameters
    ----------
    source_dti_map : DTIMap
        The source DTI map used to get dimensions and voxel volume
    """

    def __init__(self, source_dti_map: DTIMap):
        """
        Initialize with dimensions from the source DTI map.

        Parameters
        ----------
        source_dti_map : DTIMap
            The source DTI map used to get dimensions and voxel volume
        """
        self.source_dti_map = source_dti_map

        # Dictionary to store abnormal voxels
        # Key: tuple (x, y, z), Value: AbnormalValueType (HIGH or LOW)
        self.abnormal_voxels: dict[tuple[int, int, int], AbnormalValueType] = {}

    def set_value_at(self, x: int, y: int, z: int, value: AbnormalValueType) -> None:
        """
        Set an abnormal value at the specified coordinates.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate
        value : AbnormalValueType
            The type of abnormality (HIGH or LOW)

        Raises
        ------
        ValueError
            If coordinates are out of bounds
        """
        if not self._is_in_bounds(x, y, z):
            raise ValueError(f"Coordinates ({x}, {y}, {z}) out of bounds. Dimensions: {self.dimensions}")

        # Add to dictionary
        self.abnormal_voxels[(x, y, z)] = value

    def get_value_at(self, x: int, y: int, z: int) -> AbnormalValueType:
        """
        Get the abnormal value at the specified coordinates.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate

        Returns
        -------
        AbnormalValueType
            The abnormal value type (HIGH or LOW)

        Raises
        ------
        ValueError
            If coordinates are out of bounds or if voxel is not abnormal
        """
        coords = (x, y, z)
        if coords not in self.abnormal_voxels:
            raise ValueError(f"Coordinates ({x}, {y}, {z}) out of bounds. Dimensions: {self.dimensions}")

        return self.abnormal_voxels[coords]

    def is_abnormal(self, x: int, y: int, z: int) -> bool:
        """
        Check if a voxel is marked as abnormal.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate

        Returns
        -------
        bool
            True if voxel is abnormal, False otherwise
        """
        return (x, y, z) in self.abnormal_voxels

    def _is_in_bounds(self, x: int, y: int, z: int) -> bool:
        """
        Check if coordinates are within dimensions bounds.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate

        Returns
        -------
        bool
            True if coordinates are valid, False otherwise
        """
        x_bound, y_bound, z_bound = self.get_dimensions()
        return (0 <= x < x_bound and
                0 <= y < y_bound and
                0 <= z < z_bound)

    def get_dimensions(self) -> Tuple[int, int, int]:
        """
        Get the dimensions of the voxel data.

        Returns
        -------
        Tuple[int, int, int]
            Dimensions as (x, y, z)
        """
        return self.source_dti_map.voxel_data.get_dimensions()

    def get_voxel_volume_in_ml(self) -> float:
        """
        Get the volume of a voxel in milliliters.

        Returns
        -------
        float
            Volume in milliliters
        """
        return self.source_dti_map.voxel_data.get_voxel_volume_in_ml()

    def filter_values(self, condition: Callable[[AbnormalValueType], bool]) -> VoxelData[bool]:
        """
        Filter abnormal values based on a condition.

        Parameters
        ----------
        condition : Callable[[AbnormalValueType], bool]
            Function that tests if a voxel should be included

        Returns
        -------
        VoxelData[bool]
            Boolean mask of matching voxels
        """
        raise NotImplementedError("AbnormalVoxelData.filter_values")


class DTIAbnormalValues(MRIData[AbnormalValueType]):
    """
    Class to store the abnormal values in DTI images.
    """

    def __init__(self, dti_map: DTIMap, name: Optional[str] = None):
        """
        Initializes the DTIAbnormalValues class.
        """
        super().__init__(mri_exam_id=dti_map.mri_exam_id,
                         name=name or f"abnormal_values_{dti_map.name}",
                         voxel_data=AbnormalVoxelData(dti_map))


@dataclass(frozen=True)
class DTIThresholds:
    """
    Encapsulates thresholds for detecting abnormal DTI values.

    Parameters
    ----------
    high_threshold : float
        The upper threshold - values above this are considered abnormally high
    low_threshold : float
        The lower threshold - values below this are considered abnormally low
    """
    high_threshold: float
    low_threshold: float

    def get_abnormality_type(self, value: float) -> Optional[AbnormalValueType]:
        """
        Determine if a value is abnormal and return the type of abnormality.

        Parameters
        ----------
        value : float
            The DTI value to check

        Returns
        -------
        Optional[AbnormalValueType]
            The type of abnormality (HIGH or LOW), or None if normal
        """
        if value > self.high_threshold:
            return AbnormalValueType.HIGH
        elif value < self.low_threshold:
            return AbnormalValueType.LOW
        return None


class ThresholdStrategy(ABC):
    """
    Strategy interface for computing thresholds for abnormal DTI values.
    """

    @abstractmethod
    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Compute thresholds for a specific DTI metric, atlas, and label.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map for which to compute thresholds
        atlas : Atlas
            The atlas used for segmentation
        atlas_label : int
            The specific atlas label for which to compute thresholds

        Returns
        -------
        DTIThresholds
            Computed thresholds for the given parameters
        """


class FixedThresholdStrategy(ThresholdStrategy):
    """
    A simple strategy that uses fixed thresholds for all DTI metrics.

    This is a dummy implementation for development and testing.
    In a real application, thresholds would depend on the DTI metric.
    """

    def __init__(self, high_threshold: float = 0.8, low_threshold: float = 0.3):
        """
        Initialize with fixed threshold values.

        Parameters
        ----------
        high_threshold : float
            Fixed high threshold value to use for all metrics
        low_threshold : float
            Fixed low threshold value to use for all metrics
        """
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Return fixed thresholds regardless of inputs.

        This is a simplified dummy implementation.

        Parameters
        ----------
        dti_image : DTIMap
            Not used in this implementation
        atlas : Atlas
            Not used in this implementation
        atlas_label : int
            Not used in this implementation

        Returns
        -------
        DTIThresholds
            Fixed threshold values
        """
        return DTIThresholds(high_threshold=self.high_threshold, low_threshold=self.low_threshold)


class SegmentDTIAbnormalValues:
    """
    Segment abnormal values in DTI images compared to normative values (computed in each center from healthy subjects).
    """

    def __init__(self,
                 repositories_registry: RepositoriesRegistry,
                 dispatcher: Optional[EventDispatcher] = None):
        """
        Initializes the SegmentDtiAbnormalValues use-case.
        """
        self.threshold_strategy = None
        self.subjects_repository: SubjectRepository = repositories_registry.get_repository(Subject)
        self.mri_repository: MRIExamRepository = repositories_registry.get_repository(MRIExam)
        self.atlas_repository: AtlasRepository = repositories_registry.get_repository(Atlas)
        self.centers_repository: CenterRepository = repositories_registry.get_repository(Center)
        self.normative_values_repository: NormativeValueRepository = (
            repositories_registry.get_repository(NormativeValue))

    def __call__(self,
                 dti_metrics: Optional[List[DTIMetric]] = None) -> None:
        """
        Runs the use-case.

        Segments the DTI images of all patients in the SubjectRepository, for DTI metrics provided.

        Parameters
        ----------
        dti_metrics : List[DTIMetric], optional
            The DTI metrics to segment. If None, all the DTI metrics will be segmented.
        """
        self.segment_all_mri_exams_of_patients(dti_metrics)

    def segment_all_mri_exams_of_patients(self,
                                          dti_metrics: Optional[List[DTIMetric]] = None):
        """
        Segments all the MRI exams of all patients.

        It will look for all the patients in the SubjectRepository and for each patient, it will segment the DTI images.
        This segmentation process will have access to the normative values stored in the NormativeValuesRepository.
        """
        dti_metrics = dti_metrics or list(DTIMetric)
        # Get all the patients
        patients = self.subjects_repository.list_all_patients()
        for patient in patients:
            # Get the MRI exam for the patient
            mri_exam = self.mri_repository.get_exam_for_subject(patient)
            for dti_metric in dti_metrics:
                # Get the DTI map associated with the DTI metric
                try:
                    dti_image = mri_exam.get_dti_map(dti_metric)
                    self.segment_dti_map(dti_image)
                except LookupError:
                    # If the DTI image is not found, skip this metric
                    continue

    def segment_dti_map(self, dti_image: DTIMap) -> MRIData:
        """
        Segments the DTI map, i.e. build a map with values indicating the abnormal values in the input DTI map.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map to segment.
        """
        segmentations = []
        for atlas in self.atlas_repository.list_all():
            segmentations.append(self.segment_dti_map_for_atlas(dti_image, atlas))
        return self.merge_segmentations(segmentations)

    def segment_dti_map_for_atlas(self, dti_image: DTIMap, atlas: Atlas) -> MRIData:
        """
        Segments the DTI map for a given atlas, using the normative values.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map to segment.
        atlas : Atlas
            The atlas to use for segmentation.

        Returns
        -------
        MRIData
            The list of segmentations for the DTI map.
        """
        result = DTIAbnormalValues(dti_image,
                                   name=f"abnormal_{dti_image.dti_metric}_values_{atlas.name}")
        for atlas_label in atlas.labels:
            thresholds = self.compute_thresholds(dti_image, atlas, atlas_label)
            self.mark_abnormal_voxels(dti_image, atlas, atlas_label, thresholds, result)
        return result

    @staticmethod
    def merge_segmentations(segmentations: List[MRIData]) -> MRIData:
        """
        Merges the segmentations into a single MRIData object.

        Parameters
        ----------
        segmentations : List[MRIData]
            The list of segmentations to merge.

        Returns
        -------
        MRIData
            The merged segmentation.

        Warnings
        --------
        UserWarning
            Warns that this is a temporary dummy implementation.
        """
        if not segmentations:
            raise ValueError("Cannot merge empty list of segmentations")

        warnings.warn(
            "Using dummy implementation of merge_segmentations that returns only the first segmentation. "
            "This should be properly implemented in the future.",
            UserWarning,
            stacklevel=2
        )

        # Just return the first segmentation for now
        return segmentations[0]

    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Compute thresholds for abnormal values detection.
        
        This is currently a dummy implementation that returns fixed thresholds.
        In the future, this should be replaced with proper threshold computation.
        
        Parameters
        ----------
        dti_image : DTIMap
            The DTI map image to compute thresholds for
        atlas : Atlas
            The atlas used for segmentation
        atlas_label : int
            The atlas label to compute thresholds for
            
        Returns
        -------
        DTIThresholds
            Thresholds for detecting abnormal values
        
        Warnings
        --------
        UserWarning
            Warns that this is a temporary dummy implementation.
        """
        import warnings

        # If no strategy is configured, use the default fixed threshold strategy
        if not hasattr(self, 'threshold_strategy') or self.threshold_strategy is None:
            warnings.warn(
                "Using dummy implementation of compute_thresholds that returns fixed thresholds. "
                "This should be properly implemented to use normative values in the future.",
                UserWarning,
                stacklevel=2
            )
            self.threshold_strategy = FixedThresholdStrategy()
        
        # Use the configured strategy to compute thresholds
        return self.threshold_strategy.compute_thresholds(dti_image, atlas, atlas_label)

    def mark_abnormal_voxels(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int,
                             thresholds: DTIThresholds, result: DTIAbnormalValues) -> None:
        """
        Mark voxels with abnormal values in the specified atlas region.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map image to analyze
        atlas : Atlas
            The atlas used for segmentation
        atlas_label : int
            The atlas label defining the region to analyze
        thresholds : DTIThresholds
            Thresholds for detecting abnormal values
        result : DTIAbnormalValues
            The result object where abnormal voxels will be marked
        """
        # Get the atlas segmentation from the repository
        mri_exam = cast(MRIExam, self.mri_repository.get_by_id(dti_image.mri_exam_id))
        atlas_segmentation = mri_exam.get_atlas_segmentation(atlas)

        # Iterate through the coordinates of the atlas label
        mask = atlas_segmentation.create_mask([atlas_label])
        coordinates = mask.get_true_voxel_coordinates()
        for x, y, z in coordinates:
            # Get the DTI value
            dti_value = dti_image.voxel_data.get_value_at(x, y, z)

            # Check if value is abnormal
            abnormality_type = thresholds.get_abnormality_type(dti_value)
            if abnormality_type:
                result.voxel_data.set_value_at(x, y, z, abnormality_type)
