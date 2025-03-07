from dataclasses import dataclass
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.ports.repositories import SubjectRepository
from enum import Enum

class StatisticType(str, Enum):
    """Types of statistics that can be calculated for DTI metrics."""
    MEAN = "mean"
    STD_DEV = "std_dev"
    QUARTILE_25 = "quartile_25"
    QUARTILE_75 = "quartile_75"
    IQR = "iqr"


@dataclass(frozen=True)
class NormativeValue:
    """
    A normative value for a DTI metric.
    
    Represents a statistical value calculated from healthy subjects
    for a specific DTI metric, in a specific anatomical region (atlas label),
    from a specific center.
    """
    center: Center
    dti_metric: DTIMetric
    atlas: Atlas
    atlas_label: int
    statistic_type: StatisticType
    value: float

class ComputeDTINormativeValues:
    def __init__(self,
                subjects_repository: SubjectRepository) -> None:
        self.subjects_repository = subjects_repository

    def extract_dti_values_by_region(self,
                                    subject: Subject,
                                    dti_metric: DTIMetric,
                                    atlas: Atlas, 
                                    atlas_label: int) -> list[float]:
        return [0., 0., 0.]

    def compute_statistics(self,
                          subject: Subject,
                          statistic_type: StatisticType,
                          dti_metric: DTIMetric,
                          atlas: Atlas, 
                          atlas_label: int) -> float:
        dti_values = self.extract_dti_values_by_region(subject, dti_metric, atlas, atlas_label)
        return sum(dti_values) / len(dti_values)
        
    def execute(self, center: Center, dti_metric: DTIMetric, atlas: Atlas) -> list[NormativeValue]:
        results = []

        # get healthy volunteers from center
        healthy_volunteers = self.subjects_repository.find_subjects_by_center(
            center=center, subject_type=SubjectType.HEALTHY_VOLUNTEER
        )

        for healthy_volunteer in healthy_volunteers:
            for atlas_label in atlas.labels:
                for statistic_type in StatisticType:
                    statistics_value = self.compute_statistics(
                        healthy_volunteer, 
                        statistic_type, 
                        dti_metric, 
                        atlas, 
                        atlas_label)
                    normative_value = NormativeValue(
                        center=center,
                        dti_metric=dti_metric,
                        atlas=atlas,
                        atlas_label=atlas_label,
                        statistic_type=statistic_type,
                        value=statistics_value
                    )
                    results.append(normative_value)

        return results
