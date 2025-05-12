"""
This module segments the abnormal values in DTI images using the normative values computed in each center from healthy subjects.
"""
from __future__ import annotations
from typing import List, Callable, Tuple, cast

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas, DTIMetric, DTIMap, MRIData, VoxelData, MRIExamId
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.monitoring import EventDispatcher
from oxytcmri.domain.ports.repositories import (
    SubjectRepository, MRIExamRepository, AtlasRepository, CenterRepository, RepositoriesRegistry)
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue, \
    StatisticStrategy, StatisticsStrategies

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from functools import partial


class AbnormalValueType(Enum):
    """
    Enum for the type of abnormal values.
    """
    HIGH = "high"
    LOW = "low"

    @classmethod
    def from_integer(cls, value: int) -> Optional['AbnormalValueType']:
        """
        Convert an integer value to AbnormalValueType.

        Parameters
        ----------
        value : int
            Integer value to convert (0, 1, or 2)

        Returns
        -------
        Optional[AbnormalValueType]
            Corresponding AbnormalValueType or None if value is 0

        Raises
        ------
        ValueError
            If the value is not 0, 1, or 2
        """
        if value == 0:
            return None
        elif value == 1:
            return cls.LOW
        elif value == 2:
            return cls.HIGH
        else:
            raise ValueError(f"Invalid integer value for conversion to AbnormalValueType: {value}")

    def to_integer(self) -> int:
        """
        Convert AbnormalValueType to integer.

        Returns
        -------
        int
            1 for LOW, 2 for HIGH
        """
        if self == self.LOW:
            return 1
        elif self == self.HIGH:
            return 2
        else:
            # This should never happen as we only have LOW and HIGH
            raise ValueError(f"Unknown AbnormalValueType: {self}")


class AbnormalVoxelData(VoxelData[AbnormalValueType]):
    """
    Implementation of VoxelData for abnormal DTI values.

    This class stores abnormal voxels in a dictionary, where only abnormal voxels
    are stored. Voxels not present in the dictionary are considered normal.

    Attributes
    ----------
    source_voxel_data : VoxelData[float]
        The source voxel data from which the abnormal values are derived.
    """

    def __init__(self,
                 source_voxel_data: VoxelData[float]
                 ) -> None:
        """
        Initialize with dimensions from the source voxel data.

        Parameters
        ----------
        source_voxel_data : VoxelData[float]
            The source voxel data from which the abnormal values are derived.
        """
        self.source_voxel_data = source_voxel_data

        # Dictionary to store abnormal voxels
        # Key: tuple (x, y, z), Value: AbnormalValueType (HIGH or LOW)
        self.abnormal_voxels: dict[tuple[int, int, int], AbnormalValueType] = {}

    @classmethod
    def from_source_voxel_data(cls, source_voxel_data: VoxelData[float]) -> AbnormalVoxelData:
        """
        Create an AbnormalVoxelData object from source VoxelData.

        Parameters
        ----------
        source_voxel_data: VoxelData[float]
            The source voxel data from which the abnormal values are derived.

        Returns
        -------
        AbnormalVoxelData
            The created AbnormalVoxelData object
        """
        return cls(source_voxel_data=source_voxel_data)

    def get_source_voxel_data(self) -> VoxelData[float]:
        """
        Get the source voxel data.

        Returns
        -------
        VoxelData[float]
            The source voxel data
        """
        return self.source_voxel_data

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

    def get_value_at(self, x: int, y: int, z: int) -> Optional[AbnormalValueType]:
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
        if not self._is_in_bounds(x, y, z):
            raise ValueError(f"Coordinates ({x}, {y}, {z}) out of bounds. Dimensions: {self.dimensions}")

        if coords not in self.abnormal_voxels:
            return None

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
        return self.source_voxel_data.get_dimensions()

    def get_voxel_volume_in_ml(self) -> float:
        """
        Get the volume of a voxel in milliliters.

        Returns
        -------
        float
            Volume in milliliters
        """
        return self.source_voxel_data.get_voxel_volume_in_ml()

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

    def __init__(self,
                 mri_exam_id: MRIExamId,
                 voxel_data: AbnormalVoxelData,
                 source_dti_map: DTIMap,
                 name: Optional[str] = None,
                 ) -> None:
        self.mri_exam_id = mri_exam_id
        self.voxel_data = voxel_data
        self.source_dti_map = source_dti_map
        self.name = name or f"abnormal_values_{source_dti_map.name}"

    @classmethod
    def from_dti_map(cls, dti_map: DTIMap, name: Optional[str] = None) -> DTIAbnormalValues:
        """
        Create a DTIAbnormalValues object from a DTIMap.
        """
        return cls(mri_exam_id=dti_map.mri_exam_id,
                   voxel_data=AbnormalVoxelData.from_source_voxel_data(dti_map.voxel_data),
                   source_dti_map=dti_map,
                   name=name or f"abnormal_values_{dti_map.name}",
                   )


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

    def __init__(self,
                 normative_value_repository: NormativeValueRepository,
                 center_repository: CenterRepository):
        """
        Initialize the strategy with a normative value repository and center.

        Parameters
        ----------
        normative_value_repository : NormativeValueRepository
            The repository to fetch normative values
        center_repository : CenterRepository
            The repository to fetch center information
        """
        self.normative_value_repository = normative_value_repository
        self.center_repository = center_repository

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


class QuantileThresholdStrategy(ThresholdStrategy):
    """
    A strategy that computes thresholds based on quantiles of normative values.
    """

    def __init__(self,
                 normative_value_repository: NormativeValueRepository,
                 center_repository: CenterRepository,
                 high_quantile: int = 95,
                 low_quantile: int = 5):
        """
        Initialize with quantiles for threshold computation.

        Parameters
        ----------
        normative_value_repository : NormativeValueRepository
            The repository to fetch normative values
        center_repository : CenterRepository
            The repository to fetch center information
        high_quantile : int
            The quantile for the high threshold
        low_quantile : int
            The quantile for the low threshold
        """
        super().__init__(normative_value_repository, center_repository)
        self.high_quantile = high_quantile
        self.low_quantile = low_quantile

    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Compute thresholds based on quantiles of normative values.

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
        # Get the center from the DTI image
        center = self.center_repository.get_by_mri_exam_id(dti_image.mri_exam_id)

        # Create a partial function to avoid passing the same parameters multiple times
        get_stat_value = partial(
            self._get_normative_value,
            center=center,
            atlas_label=atlas_label,
            atlas=atlas,
            dti_metric=dti_image.dti_metric
        )

        # Use the partial function to get the quantiles
        high_threshold = get_stat_value(statistic_strategy=StatisticsStrategies.get_by_name(f"quantile {self.high_quantile}"))
        low_threshold = get_stat_value(statistic_strategy=StatisticsStrategies.get_by_name(f"quantile {self.low_quantile}"))

        return DTIThresholds(high_threshold=high_threshold, low_threshold=low_threshold)

    def _get_normative_value(self,
                             center: Center,
                             statistic_strategy: StatisticStrategy,
                             atlas_label: int,
                             atlas: Atlas,
                             dti_metric: DTIMetric) -> float:
        """
        Get the normative value based on the provided parameters.

        Parameters
        ----------
        center : Center
            The center to use for fetching normative values
        statistic_strategy : StatisticStrategy
            The strategy to use for computing the normative value
        atlas_label : int
            The atlas label to use for fetching normative values
        atlas : Atlas
            The atlas to use for fetching normative values
        dti_metric : DTIMetric
            The DTI metric to use for fetching normative values

        """
        return self.normative_value_repository.get_by_parameters(
            statistic_strategy=statistic_strategy,
            center=center,
            atlas_label=atlas_label,
            atlas=atlas,
            dti_metric=dti_metric,
        ).value


class MeanThresholdStrategy(ThresholdStrategy):
    """
    A strategy that computes thresholds based on the mean and standard deviation of normative values.

    This is a dummy implementation for development and testing.
    In a real application, the computation would depend on the DTI metric and atlas.
    """

    def __init__(self,
                 normative_value_repository: NormativeValueRepository,
                 center_repository: CenterRepository,
                 high_deviation_factor: float = 2.0,
                 low_deviation_factor: float = 2.0):
        """
        Initialize with a z-score for threshold computation.

        Parameters
        ----------
        normative_value_repository : NormativeValueRepository
            The repository to fetch normative values
        center_repository : CenterRepository
            The repository to fetch center information
        high_deviation_factor : float
            The factor to multiply the standard deviation for high threshold
        low_deviation_factor : float
            The factor to multiply the standard deviation for low threshold
        """
        super().__init__(normative_value_repository, center_repository)
        self.high_deviation_factor = high_deviation_factor
        self.low_deviation_factor = low_deviation_factor

    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Compute thresholds based on the mean and standard deviation of normative values.

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
        # Get the center from the DTI image
        center = self.center_repository.get_by_mri_exam_id(dti_image.mri_exam_id)

        # Create a partial function to avoid passing the same parameters multiple times
        get_stat_value = partial(
            self._get_normative_value,
            center=center,
            atlas_label=atlas_label,
            atlas=atlas,
            dti_metric=dti_image.dti_metric
        )

        # Use the partial function to get the mean and standard deviation
        mean_value = get_stat_value(statistic_strategy=StatisticsStrategies.get_by_name("mean"))
        std_value = get_stat_value(statistic_strategy=StatisticsStrategies.get_by_name("standard deviation"))

        high_threshold = mean_value + self.high_deviation_factor * std_value
        low_threshold = mean_value - self.low_deviation_factor * std_value
        return DTIThresholds(high_threshold=high_threshold, low_threshold=low_threshold)

    def _get_normative_value(self,
                             center: Center,
                             statistic_strategy: StatisticStrategy,
                             atlas_label: int,
                             atlas: Atlas,
                             dti_metric: DTIMetric) -> float:
        """
        Get the normative value based on the provided parameters.

        Parameters
        ----------
        center : Center
            The center to use for fetching normative values
        statistic_strategy : StatisticStrategy
            The strategy to use for computing the normative value
        atlas_label : int
            The atlas label to use for fetching normative values
        atlas : Atlas
            The atlas to use for fetching normative values
        dti_metric : DTIMetric
            The DTI metric to use for fetching normative values

        """
        return self.normative_value_repository.get_by_parameters(
            statistic_strategy=statistic_strategy,
            center=center,
            atlas_label=atlas_label,
            atlas=atlas,
            dti_metric=dti_metric,
        ).value


class InterQuartileRangeThresholdStrategy(ThresholdStrategy):
    """
    A strategy that computes thresholds based on the interquartile range (IQR) of normative values.
    """

    def __init__(self,
                 normative_value_repository: NormativeValueRepository,
                 center_repository: CenterRepository,
                 high_deviation_factor: float = 2.0, low_deviation_factor: float = 2.0):
        """
        Initialize with a z-score for threshold computation.

        Parameters
        ----------
        normative_value_repository : NormativeValueRepository
            The repository to fetch normative values
        center_repository : CenterRepository
            The repository to fetch center information
        high_deviation_factor : float
            The factor to multiply the interquartile range for high threshold
        low_deviation_factor : float
            The factor to multiply the interquartile range for low threshold
        """
        super().__init__(normative_value_repository, center_repository)
        self.high_deviation_factor = high_deviation_factor
        self.low_deviation_factor = low_deviation_factor

    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Compute thresholds based on the interquartile range of normative values.

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
        # Get the center from the DTI image
        center = self.center_repository.get_by_mri_exam_id(dti_image.mri_exam_id)

        # Create a partial function to avoid passing the same parameters multiple times
        get_stat_value = partial(
            self._get_normative_value,
            center=center,
            atlas_label=atlas_label,
            atlas=atlas,
            dti_metric=dti_image.dti_metric
        )

        # Use the partial function to get the first and third quartiles
        q1 = get_stat_value(statistic_strategy=StatisticsStrategies.get_by_name("quartile 25"))
        q3 = get_stat_value(statistic_strategy=StatisticsStrategies.get_by_name("quartile 75"))

        iqr = q3 - q1

        high_threshold = q3 + self.high_deviation_factor * iqr
        low_threshold = q1 - self.low_deviation_factor * iqr

        return DTIThresholds(high_threshold=high_threshold, low_threshold=low_threshold)

    def _get_normative_value(self,
                             center: Center,
                             statistic_strategy: StatisticStrategy,
                             atlas_label: int,
                             atlas: Atlas,
                             dti_metric: DTIMetric) -> float:
        """
        Get the normative value based on the provided parameters.

        Parameters
        ----------
        center : Center
            The center to use for fetching normative values
        statistic_strategy : StatisticStrategy
            The strategy to use for computing the normative value
        atlas_label : int
            The atlas label to use for fetching normative values
        atlas : Atlas
            The atlas to use for fetching normative values
        dti_metric : DTIMetric
            The DTI metric to use for fetching normative values

        """
        return self.normative_value_repository.get_by_parameters(
            statistic_strategy=statistic_strategy,
            center=center,
            atlas_label=atlas_label,
            atlas=atlas,
            dti_metric=dti_metric,
        ).value


class SegmentationMerger(ABC):
    """
    Abstract interface for merging MRI segmentations.
    This interface respects the dependency inversion principle.
    """

    @abstractmethod
    def merge(self, segmentations: List[DTIAbnormalValues]) -> DTIAbnormalValues:
        """
        Merges multiple segmentations into a single one.

        Parameters
        ----------
        segmentations : List[DTIAbnormalValues]
            List of segmentations to merge.

        Returns
        -------
        DTIAbnormalValues
            The merged segmentation.

        Raises
        -------
        RuntimeError
            If the segmentations cannot be merged.
        """


class SegmentDTIAbnormalValues:
    """
    Segment abnormal values in DTI images compared to normative values (computed in each center from healthy subjects).
    """

    def __init__(self,
                 repositories_registry: RepositoriesRegistry,
                 threshold_strategy: Optional[ThresholdStrategy] = None,
                 segmentation_merger: Optional[SegmentationMerger] = None,
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

        self.dispatcher = dispatcher

        # Define the default threshold strategy to MeanThresholdStrategy
        default_threshold_strategy = QuantileThresholdStrategy(
            normative_value_repository=self.normative_values_repository,
            center_repository=self.centers_repository
        )
        self.threshold_strategy = threshold_strategy or default_threshold_strategy

        # Define the default segmentation merger
        self.segmentation_merger = segmentation_merger

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
                dti_image = mri_exam.get_dti_map(dti_metric)
                segmented_dti_map = self.segment_dti_map(dti_image)

                # Save the segmented DTI map
                mri_exam.add_mri_data(segmented_dti_map)
                self.mri_repository.save(mri_exam)

    def segment_dti_map(self, dti_image: DTIMap) -> DTIAbnormalValues:
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

    def segment_dti_map_for_atlas(self, dti_image: DTIMap, atlas: Atlas) -> DTIAbnormalValues:
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
        DTIAbnormalValues
            The segmented DTI map with abnormal values.
        """
        result = DTIAbnormalValues.from_dti_map(dti_image)
        for atlas_label in atlas.labels:
            thresholds = self.compute_thresholds(dti_image, atlas, atlas_label)
            self.mark_abnormal_voxels(dti_image, atlas, atlas_label, thresholds, result)
        return result

    def merge_segmentations(self, segmentations: List[DTIAbnormalValues]) -> DTIAbnormalValues:
        """
        Merges the segmentations into a single MRIData object.

        Parameters
        ----------
        segmentations : List[DTIAbnormalValues]
            The list of segmentations to merge.

        Returns
        -------
        DTIAbnormalValues
            The merged segmentation.

        Raises
        -------
        RuntimeError
            If the segmentation merger is not set.
        """
        if not self.segmentation_merger:
            raise RuntimeError("Segmentation merger is not set. Cannot merge segmentations.")

        return self.segmentation_merger.merge(segmentations)

    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Compute thresholds for abnormal values detection.
        
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
        """
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
