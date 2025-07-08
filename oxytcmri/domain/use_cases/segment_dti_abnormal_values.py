"""
This module segments the abnormal values in DTI images using the normative values computed in each center from healthy subjects.
"""
from __future__ import annotations
from typing import List, cast
import logging

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas, DTIMetric, DTIMap, MRIExamId, AbnormalValueType, \
    DTIAbnormalValues, VoxelData
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.monitoring import EventDispatcher, ProgressEvent
from oxytcmri.domain.ports.repositories import (
    SubjectRepository, MRIExamRepository, AtlasRepository, CenterRepository, RepositoriesRegistry,
    EntityNotFoundException)
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue, \
    StatisticStrategy, StatisticsStrategies

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from functools import partial

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DTIThresholds:
    """
    Encapsulates thresholds for detecting abnormal DTI values.

    Parameters
    ----------
    high_threshold : float
        The upper threshold - values above this are considered abnormally high. If None, threshold will be set to inf.
    low_threshold : float
        The lower threshold - values below this are considered abnormally low. If None, threshold will be set to -inf.
    """
    high_threshold: Optional[float]
    low_threshold: Optional[float]

    def __post_init__(self):
        """
        Set default thresholds to infinity if None.
        """
        if self.high_threshold is None:
            object.__setattr__(self, 'high_threshold', float('inf'))
        if self.low_threshold is None:
            object.__setattr__(self, 'low_threshold', float('-inf'))

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
        high_threshold = get_stat_value(
            statistic_strategy=StatisticsStrategies.get_by_name(f"quantile {self.high_quantile}")
        )
        low_threshold = get_stat_value(
            statistic_strategy=StatisticsStrategies.get_by_name(f"quantile {self.low_quantile}")
        )

        return DTIThresholds(high_threshold=high_threshold, low_threshold=low_threshold)

    def _get_normative_value(self,
                             center: Center,
                             statistic_strategy: StatisticStrategy,
                             atlas_label: int,
                             atlas: Atlas,
                             dti_metric: DTIMetric) -> Optional[float]:
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
        try:
            return self.normative_value_repository.get_by_parameters(
                statistic_strategy=statistic_strategy,
                center=center,
                atlas_label=atlas_label,
                atlas=atlas,
                dti_metric=dti_metric,
            ).value
        except EntityNotFoundException:
            return None


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

        # Initialize the progress bar attributes
        self.current_step = None
        self.total_steps = None

    def initialize_progress_bar(self,
                                total_steps: int) -> None:
        """
        Initialise la barre de progression.
        """
        self.current_step = 0
        self.total_steps = total_steps
        if self.dispatcher is not None:
            self.dispatcher.dispatch(ProgressEvent(0, self.total_steps))

    def update_progress_bar(self) -> None:
        """
        Met à jour la barre de progression.
        """
        if self.dispatcher is not None:
            self.current_step += 1
            self.dispatcher.dispatch(ProgressEvent(self.current_step, self.total_steps))

    def __call__(self,
                 dti_metrics: Optional[List[DTIMetric]] = None,
                 mri_exam_id: Optional[MRIExamId] = None) -> None:
        """
        Runs the use-case.

        Segments the DTI images of all patients in the SubjectRepository, for DTI metrics provided.

        Parameters
        ----------
        dti_metrics : List[DTIMetric], optional
            The DTI metrics to segment. If None, all the DTI metrics will be segmented.
        """
        # If no DTI metrics are provided, segment all the DTI metrics
        dti_metrics = dti_metrics or list(DTIMetric)

        if mri_exam_id:
            self.initialize_progress_bar(total_steps=len(dti_metrics))
            mri_exam = self.mri_repository.get_by_id(mri_exam_id)
            self.segment_dti_maps_associated_to_mri_exam(mri_exam, dti_metrics)
        else:
            self.initialize_progress_bar(
                total_steps=len(self.subjects_repository.list_all_patients()) * len(dti_metrics)
            )
            self.segment_all_mri_exams_of_patients(dti_metrics)

    def segment_all_mri_exams_of_patients(self,
                                          dti_metrics: List[DTIMetric]):
        """
        Segments all the MRI exams of all patients.

        It will look for all the patients in the SubjectRepository and for each patient, it will segment the DTI images.
        This segmentation process will have access to the normative values stored in the NormativeValuesRepository.
        """
        # Get all the patients
        patients = self.subjects_repository.list_all_patients()
        for patient in patients:
            # Get the MRI exam for the patient
            mri_exam = self.mri_repository.get_exam_for_subject(patient)
            self.segment_dti_maps_associated_to_mri_exam(mri_exam, dti_metrics)

    def segment_dti_maps_associated_to_mri_exam(self,
                                                mri_exam: MRIExam,
                                                dti_metrics: List[DTIMetric]) -> None:
        """
        Segments the DTI maps associated with a given MRI exam.
        This method will look for all the DTI maps associated with the MRI exam and segment them.

        Parameters
        ----------
        dti_metrics : List[DTIMetric]
            The DTI metrics to segment.
        mri_exam : MRIExam
            The MRI exam to segment the DTI maps for.
        """
        for dti_metric in dti_metrics:
            # Check if the segmentation is already done for this DTI metric
            try:
                mri_exam.get_segmented_dti_abnormal_values(dti_metric)
                logger.info(f"DTI metric {dti_metric} already segmented for MRI exam {mri_exam.id}")
            except LookupError:
                logger.info(f"Segmentation for DTI metric {dti_metric} not found in MRI exam {mri_exam.id}: "
                            f"proceeding with segmentation.")
                # Get the DTI map associated with the DTI metric
                dti_image = mri_exam.get_dti_map(dti_metric)
                segmented_dti_map = self.segment_dti_map(dti_image)

                # Add the segmented DTI map to the MRI exam
                mri_exam.add_mri_data(segmented_dti_map)

            self.update_progress_bar()

        # Save the whole MRI exam in the repository
        self.mri_repository.save(mri_exam)

    def segment_dti_map(self, dti_image: DTIMap) -> DTIAbnormalValues:
        """
        Segments the DTI map, i.e. build a map with values indicating the abnormal values in the input DTI map.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map to segment.
        """
        logger.info(f"Segmenting DTI map: {dti_image}")
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
        logger.info(f"Segmenting DTI map: {dti_image} for atlas: {atlas}")
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
        logger.debug(f"Computing thresholds for abnormal values in DTI map {dti_image} "
                     f"for atlas {atlas} and label {atlas_label}")
        return self.threshold_strategy.compute_thresholds(dti_image, atlas, atlas_label)

    def mark_abnormal_voxels(self,
                             dti_image: DTIMap,
                             atlas: Atlas,
                             atlas_label: int,
                             thresholds: DTIThresholds,
                             result: DTIAbnormalValues) -> None:
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
        logger.debug(f"Mark abnormal values for DTI map {dti_image}, "
                     f"in label {atlas_label} of atlas {atlas},"
                     f"with threshold {thresholds}")

        # Get the MRI exam associated with the DTI image
        mri_exam = cast(MRIExam, self.mri_repository.get_by_id(dti_image.mri_exam_id))

        # Get the atlas mask for the specified label
        atlas_segmentation = mri_exam.get_atlas_segmentation(atlas)
        atlas_mask = atlas_segmentation.create_mask([atlas_label])

        # Detect high and low values
        abnormally_high_mask = dti_image.get_mask_of_values_above_threshold(thresholds.high_threshold)
        high_in_region_mask = abnormally_high_mask.mask_with(atlas_mask)
        result.voxel_data.mark_voxels_as(high_in_region_mask, AbnormalValueType.HIGH)

        abnormally_low_mask = dti_image.get_mask_of_values_below_threshold(thresholds.low_threshold)
        low_in_region_mask = abnormally_low_mask.mask_with(atlas_mask)
        result.voxel_data.mark_voxels_as(low_in_region_mask, AbnormalValueType.LOW)
