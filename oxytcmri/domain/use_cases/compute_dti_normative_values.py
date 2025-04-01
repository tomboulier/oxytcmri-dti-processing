from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable
import numpy as np
from sqlalchemy.orm.sync import update

from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas, RegionOfInterest
from oxytcmri.domain.ports.repositories import SubjectRepository, MRIExamRepository, AtlasRepository, CenterRepository
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


class NormativeValueRepository(ABC):
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
            Event dispatcher for dispatching events
        """
        self.atlas_repository = atlas_repository
        self.centers_repository = centers_repository
        self.subjects_repository = subjects_repository
        self.mri_repository = mri_repository
        self.normative_values_repository = normative_values_repository

        # progress bar
        self.dispatcher = dispatcher
        self.total_steps = self.compute_total_steps()
        self.current_step = 0
        self.initialize_progress_bar()

    def __call__(self) -> None:
        """
        Execute the use case to compute normative DTI values.
        """
        normative_values = self.compute_all_normative_values()
        for normative_value in normative_values:
            self.normative_values_repository.save(normative_value)

    def compute_total_steps(self) -> int:
        """
        Get the total number of steps for the progress bar.

        Returns
        -------
        int
            The total number of steps
        """
        # Get count of all healthy volunteers
        healthy_volunteers_count = 0
        centers = self.centers_repository.get_all_centers()
        for center in centers:
            healthy_volunteers_count += len(self.subjects_repository.find_subjects_by_center(
                                            center=center, subject_type=SubjectType.HEALTHY_VOLUNTEER
                                            ))

        # Get count of all atlas labels
        atlas_labels_count = 0
        atlases = self.atlas_repository.get_all_atlases()
        for atlas in atlases:
            atlas_labels_count += len(atlas.labels)

        return healthy_volunteers_count * atlas_labels_count * len(DTIMetric) * len(StatisticsStrategies.all())

    def initialize_progress_bar(self) -> None:
        """
        Initialize the progress bar using the dispatcher.
        """
        if self.dispatcher is not None:
            self.dispatcher.dispatch(ProgressEvent(0, self.total_steps))

    def update_progress_bar(self) -> None:
        """
        Update the progress bar using the dispatcher.
        """
        self.current_step += 1
        if self.dispatcher is not None:
            self.dispatcher.dispatch(ProgressEvent(self.current_step, self.total_steps))

    def extract_dti_values_by_region(
        self, subject: Subject, dti_metric: DTIMetric, atlas: Atlas, atlas_label: int
    ) -> List[float]:
        """
        Extract DTI metric values for a specific atlas region.

        Parameters
        ----------
        subject : Subject
            The subject from which to extract DTI values
        dti_metric : DTIMetric
            The type of DTI metric to extract (MD, FA, etc.)
        atlas : Atlas
            The atlas defining the region
        atlas_label : int
            The specific label within the atlas

        Returns
        -------
        List[float]
            DTI values corresponding to the specified atlas region
        """
        # Retrieve the MRI exam for the subject
        mri_exam = self.mri_repository.get_exam_for_subject(str(subject.id))

        # Create a RegionOfInterest with the specific label
        roi = RegionOfInterest(atlas=atlas, labels=[atlas_label])

        # Extract DTI values for the specific region of interest
        dti_values = mri_exam.extract_dti_values_for_region(
            dti_metric=dti_metric, roi=roi
        )

        return dti_values

    def compute_statistics(
        self,
        subject: Subject,
        statistic_strategy: StatisticStrategy,
        dti_metric: DTIMetric,
        atlas: Atlas,
        atlas_label: int,
    ) -> float:
        """
        Compute statistics for DTI values in a specific region.

        Parameters
        ----------
        subject : Subject
            The subject for which to compute statistics
        statistic_strategy : StatisticStrategy
            The strategy for computing the statistic
        dti_metric : DTIMetric
            The type of DTI metric
        atlas : Atlas
            The atlas defining the region
        atlas_label : int
            The specific label within the atlas

        Returns
        -------
        float
            The computed statistical value
        """
        dti_values = self.extract_dti_values_by_region(
            subject, dti_metric, atlas, atlas_label
        )
        return statistic_strategy(dti_values)

    def compute_center_normative_values_by_atlas(
        self, center: Center, dti_metric: DTIMetric, atlas: Atlas
    ) -> list[NormativeValue]:
        """
        Compute the normative values for a given center, metric, and atlas.

        Parameters
        ----------
        center : Center
            The medical center to compute normative values for
        dti_metric : DTIMetric
            The DTI metric to analyze
        atlas : Atlas
            The atlas to use for segmentation

        Returns
        -------
        list[NormativeValue]
            A list of computed normative values
        """
        results = []

        # Get healthy volunteers from the repository
        healthy_volunteers = self.subjects_repository.find_subjects_by_center(
            center, subject_type=SubjectType.HEALTHY_VOLUNTEER
        )

        # Compute normative values for each healthy volunteer
        for healthy_volunteer in healthy_volunteers:
            for atlas_label in atlas.labels:
                for statistic_strategy in StatisticsStrategies.all():
                    # Compute statistics for the current atlas region
                    statistics_value = self.compute_statistics(
                        healthy_volunteer,
                        statistic_strategy,
                        dti_metric,
                        atlas,
                        atlas_label,
                    )

                    # Create normative value object
                    normative_value = NormativeValue(
                        center=center,
                        dti_metric=dti_metric,
                        atlas=atlas,
                        atlas_label=atlas_label,
                        statistic_strategy=statistic_strategy,
                        value=statistics_value,
                    )

                    # Add the normative value to the results list
                    results.append(normative_value)

                    # Update the progress bar
                    self.update_progress_bar()

        return results

    def compute_all_normative_values(self) -> List[NormativeValue]:
        """
        Compute normative values for all centers, DTI metrics, and atlases.

        Returns
        -------
        List[NormativeValue]
            A list of computed normative values for all centers
        """
        results = []

        # Get all centers and atlases from repositories
        centers = self.centers_repository.get_all_centers()
        atlases = self.atlas_repository.get_all_atlases()

        # Compute normative values for each center, DTI metric, and atlas
        for center in centers:
            for atlas in atlases:
                for dti_metric in DTIMetric:
                    normative_values = self.compute_center_normative_values_by_atlas(
                        center, dti_metric, atlas
                        )
                    results.extend(normative_values)

        return results
