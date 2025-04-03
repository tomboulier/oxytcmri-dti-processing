from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable
import numpy as np

from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas, RegionOfInterest
from oxytcmri.domain.ports.repositories import (
    Repository,
    SubjectRepository,
    MRIExamRepository,
    AtlasRepository,
    CenterRepository
)
from oxytcmri.domain.ports.monitoring import EventDispatcher, ProgressEvent


@dataclass
class StatisticStrategy:
    """
    A statistical calculation strategy that encapsulates both the type
    and the calculation method.

    Parameters
    ----------
    name : str
        A human-readable name for the statistical strategy
    calculate : Callable[[List[float]], float]
        A function that calculates a specific statistical measure

    Methods
    -------
    __call__(values: List[float]) -> float
        Allows the strategy to be called directly like a function
    """

    name: str
    calculate: Callable[[List[float]], float]

    def __call__(self, values: List[float]) -> float:
        """
        Execute the statistical calculation strategy.

        Parameters
        ----------
        values : List[float]
            The list of values to calculate statistics on

        Returns
        -------
        float
            The calculated statistical value
        """
        return self.calculate(values)


class StatisticsStrategies:
    """
    A collection of statistical calculation strategies for DTI metrics.

    This class defines various statistical methods that can be applied
    to lists of float values, with built-in handling for empty lists.

    Methods
    -------
    mean(values: List[float]) -> float
        Calculate the arithmetic mean of the values
    std_dev(values: List[float]) -> float
        Calculate the standard deviation of the values
    quartile_25(values: List[float]) -> float
        Calculate the 25th percentile (first quartile)
    quartile_75(values: List[float]) -> float
        Calculate the 75th percentile (third quartile)
    iqr(values: List[float]) -> float
        Calculate the interquartile range
    """

    @staticmethod
    def mean(values: List[float]) -> float:
        """Calculate mean with handling for empty lists."""
        return float(np.mean(values)) if values else 0.0

    @staticmethod
    def std_dev(values: List[float]) -> float:
        """Calculate standard deviation with handling for empty lists."""
        return float(np.std(values)) if values else 0.0

    @staticmethod
    def quartile_25(values: List[float]) -> float:
        """Calculate 25th percentile with handling for empty lists."""
        return float(np.percentile(values, 25)) if values else 0.0

    @staticmethod
    def quartile_75(values: List[float]) -> float:
        """Calculate 75th percentile with handling for empty lists."""
        return float(np.percentile(values, 75)) if values else 0.0

    @staticmethod
    def iqr(values: List[float]) -> float:
        """
        Calculate interquartile range with handling for empty lists.

        Returns the difference between 75th and 25th percentiles.
        """
        if not values:
            return 0.0
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        return float(q3 - q1)

    # Available statistical strategies
    MEAN = StatisticStrategy("mean", mean)
    STD_DEV = StatisticStrategy("standard deviation", std_dev)
    QUARTILE_25 = StatisticStrategy("quartile 25", quartile_25)
    QUARTILE_75 = StatisticStrategy("quartile 75", quartile_75)
    IQR = StatisticStrategy("interquartile range", iqr)

    @classmethod
    def all(cls):
        """
        Retrieve all defined statistical strategies.

        Returns
        -------
        List[StatisticStrategy]
            A list of all available statistical strategies
        """
        return [cls.MEAN, cls.STD_DEV, cls.QUARTILE_25, cls.QUARTILE_75, cls.IQR]

    @classmethod
    def get_by_name(cls, name: str) -> StatisticStrategy:
        """
        Retrieve a statistical strategy by its name.

        Parameters
        ----------
        name : str
            The name of the statistical strategy

        Returns
        -------
        StatisticStrategy
            The corresponding statistical strategy

        Raises
        ------
        ValueError
            If no strategy with the given name exists
        """
        for strategy in cls.all():
            if strategy.name == name:
                return strategy
        raise ValueError(f"No statistical strategy found with name: {name}")


@dataclass(frozen=True)
class NormativeValue:
    """
    Represents a normative value for a DTI metric.

    A normative value is a statistical measure calculated from healthy subjects
    for a specific DTI metric in a specific anatomical region.

    Parameters
    ----------
    center : Center
        The medical center where the normative value was calculated
    dti_metric : DTIMetric
        The type of DTI metric (e.g., MD, FA)
    atlas : Atlas
        The atlas used for segmentation
    atlas_label : int
        The specific label within the atlas
    statistic_strategy : StatisticStrategy
        The statistical strategy used to compute the value
    value : float
        The calculated statistical value
    """

    center: Center
    dti_metric: DTIMetric
    atlas: Atlas
    atlas_label: int
    statistic_strategy: StatisticStrategy
    value: float


class NormativeValueRepository(Repository, ABC):
    """
    Abstract base class for Normative Value repository.

    Defines the interface for saving and retrieving normative values.
    """

    @abstractmethod
    def save(self, normative_value: NormativeValue) -> None:
        """
        Save a normative value.
        """

    @abstractmethod
    def get_all(self) -> List[NormativeValue]:
        """
        Retrieve all normative values.
        """

    @abstractmethod
    def exists(self,
               center: Center,
               dti_metric: DTIMetric,
               atlas: Atlas,
               atlas_label: int,
               statistic_strategy: StatisticStrategy
               ) -> bool:
        """
        Check if a normative value is already saved for the given configuration.
        """


class ComputeDTINormativeValues:
    """
    Use case for computing normative DTI values from healthy volunteers.

    This class orchestrates the process of extracting DTI values from
    healthy subjects and computing various statistical measures.

    Attributes
    ----------
    subjects_repository : SubjectRepository
        Repository for accessing subject information
    mri_repository : MRIExamRepository
        Repository for accessing MRI data
    atlas_repository : AtlasRepository
        Repository for accessing atlas information
    centers_repository : CenterRepository
        Repository for accessing center information
    """

    def __init__(
            self,
            subjects_repository: SubjectRepository,
            mri_repository: MRIExamRepository,
            atlas_repository: AtlasRepository,
            centers_repository: CenterRepository,
            normative_values_repository: NormativeValueRepository,
            dispatcher: EventDispatcher = None
    ) -> None:
        """
        Initialize the use case with a subject repository.

        Parameters
        ----------
        subjects_repository : SubjectRepository
            Repository for retrieving subject information
        mri_repository : MRIRepository
            Repository for retrieving MRI information
        atlas_repository : AtlasRepository
            Repository for retrieving atlas information
        centers_repository : CenterRepository
            Repository for retrieving center information
        normative_values_repository : NormativeValueRepository
            Repository for saving normative values
        dispatcher : EventDispatcher, optional
            Event dispatcher for dispatching events (progress bar, logs, etc.)
        """
        # repositories
        self.atlas_repository = atlas_repository
        self.centers_repository = centers_repository
        self.subjects_repository = subjects_repository
        self.mri_repository = mri_repository
        self.normative_values_repository = normative_values_repository

        # progress bar
        self.dispatcher = dispatcher
        self.current_step = None
        self.total_steps = None

    def __call__(self,
                 statistics_strategies: List[StatisticStrategy] = None,
                 dti_metrics: List[DTIMetric] = None
                 ) -> None:
        """
        Execute the use case to compute normative DTI values.

        Parameters
        ----------
        statistics_strategies : List[StatisticStrategy], optional
            List of statistical strategies to use for computing normative values
        dti_metrics : List[DTIMetric], optional
            List of DTI metrics to compute normative values for computing normative values
        """
        self.compute_all_normative_values(
            statistics_strategies=statistics_strategies,
            dti_metrics=dti_metrics
        )

    def compute_total_steps(self,
                            dti_metrics_count: int,
                            statistics_strategies_count: int
                            ) -> int:
        """
        Get the total number of steps for the progress bar.

        Returns
        -------
        int
            The total number of steps
        """
        centers = self.centers_repository.get_all_centers()

        # Get count of all atlas labels
        atlas_labels_count = 0
        atlases = self.atlas_repository.get_all_atlases()
        for atlas in atlases:
            atlas_labels_count += len(atlas.labels)

        return len(centers) * atlas_labels_count * dti_metrics_count * statistics_strategies_count

    def initialize_progress_bar(self,
                                dti_metrics_to_process: List[DTIMetric],
                                statistics_strategies_to_process: List[StatisticStrategy]
                                ) -> None:
        """
        Initialize the progress bar using the dispatcher.
        """
        self.current_step = 0
        self.total_steps = self.compute_total_steps(len(dti_metrics_to_process),
                                               len(statistics_strategies_to_process))
        if self.dispatcher is not None:
            self.dispatcher.dispatch(ProgressEvent(0, self.total_steps))

    def update_progress_bar(self) -> None:
        """
        Update the progress bar using the dispatcher.
        """
        self.current_step += 1
        if self.dispatcher is not None:
            self.dispatcher.dispatch(ProgressEvent(self.current_step, self.total_steps))

    def compute_all_normative_values(self,
                                     statistics_strategies: List[StatisticStrategy] = None,
                                     dti_metrics: List[DTIMetric] = None
                                     ) -> None:
        """
        Compute normative values for all DTI metrics, statistical strategies, centers, atlases, and labels.

        This is the main entry point that orchestrates the computation process.

        Parameters
        ----------
        statistics_strategies : List[StatisticStrategy], optional
            List of statistical strategies to include in computations.
            If provided, only this subset will be computed.
        dti_metrics : List[DTIMetric], optional
            List of DTI metrics to include in computations.
            If provided, only this subset will be computed.
        """
        # Get all resources
        dti_metrics_to_process = dti_metrics or list(DTIMetric)
        statistic_strategies_to_process = statistics_strategies or StatisticsStrategies.all()
        centers = self.centers_repository.get_all_centers()
        regions_of_interest = self.get_regions_of_interest()

        # Initialize progress bar
        self.initialize_progress_bar(
            dti_metrics_to_process,
            statistic_strategies_to_process,
        )

        # Process each DTI metric
        for dti_metric in dti_metrics_to_process:
            for statistic_strategy in statistic_strategies_to_process:
                for region_of_interest in regions_of_interest:
                    for center in centers:
                        self.process_center(center, dti_metric, statistic_strategy, region_of_interest)

    def process_center(self,
                       center: Center,
                       dti_metric: DTIMetric,
                       statistic_strategy: StatisticStrategy,
                       region_of_interest: RegionOfInterest) -> None:
        """
        Process a specific center for a given DTI metric and statistical strategy.

        Parameters
        ----------
        center : Center
            The center to process
        dti_metric : DTIMetric
            The DTI metric to process
        statistic_strategy : StatisticStrategy
            The statistical strategy to apply
        region_of_interest : RegionOfInterest
            The region of interest to process
        """
        if len(region_of_interest.labels) > 1:
            raise ValueError("Region of interest must have only one label in this context")

        label_of_interest = region_of_interest.labels[0]
        # Check if the normative value already exists
        if self.normative_values_repository.exists(
                center, dti_metric, region_of_interest.atlas, label_of_interest, statistic_strategy):
            # Skip if the normative value already exists
            self.update_progress_bar()
            return

        # Get healthy subjects for this center
        healthy_subjects = self.subjects_repository.find_subjects_by_center(
            center=center, subject_type=SubjectType.HEALTHY_VOLUNTEER
        )

        if not healthy_subjects:
            # No healthy subjects for this center, skip
            return

        # Collect DTI values for this region
        all_dti_values = self.collect_dti_values_for_region(
            healthy_subjects, dti_metric, region_of_interest)

        if not all_dti_values:
            # No DTI values collected, skip
            self.update_progress_bar()
            return

        # Calculate the statistical value
        statistics_value = statistic_strategy(all_dti_values)

        # Create and save the normative value
        normative_value = NormativeValue(
            center=center,
            dti_metric=dti_metric,
            atlas=region_of_interest.atlas,
            atlas_label=label_of_interest,
            statistic_strategy=statistic_strategy,
            value=statistics_value
        )

        self.store_normative_value(normative_value)
        self.update_progress_bar()

    def collect_dti_values_for_region(
            self,
            subjects: List[Subject],
            dti_metric: DTIMetric,
            region_of_interest: RegionOfInterest
    ) -> List[float]:
        """
        Collect DTI values for a specific region from multiple subjects.

        Parameters
        ----------
        subjects : List[Subject]
            List of subjects to extract values from
        dti_metric : DTIMetric
            The DTI metric to extract
        region_of_interest : RegionOfInterest
            The region of interest to extract values from

        Returns
        -------
        List[float]
            Combined list of DTI values from all subjects
        """
        all_dti_values = []

        for subject in subjects:
            # Extract DTI values for the subject
            mri_exam = self.mri_repository.get_exam_for_subject(str(subject.id))
            values = mri_exam.extract_dti_values_for_region(dti_metric, region_of_interest)

            if values:
                all_dti_values.extend(values)

        return all_dti_values

    def get_regions_of_interest(self) -> List[RegionOfInterest]:
        """
        Retrieve the list of regions of interest.

        Returns
        -------
        List[RegionOfInterest]
            A list of regions of interest
        """
        result = []
        for atlas in self.atlas_repository.get_all_atlases():
            for atlas_label in atlas.labels:
                roi = RegionOfInterest(atlas=atlas, labels=[atlas_label])
                result.append(roi)
        return result

    def store_normative_value(self, normative_value: NormativeValue) -> None:
        """Store the normative value in the repository."""
        try:
            self.normative_values_repository.save(normative_value)
        except Exception:
            # Skip storing if an error occurs
            return
