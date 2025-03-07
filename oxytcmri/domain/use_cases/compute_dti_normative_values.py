from dataclasses import dataclass
from typing import List
import numpy as np

from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.ports.repositories import SubjectRepository

@dataclass
class StatisticStrategy:
    """
    Une stratégie de calcul statistique qui encapsule à la fois le type 
    et la méthode de calcul.
    """
    name: str
    calculate: callable

    def __call__(self, values: List[float]) -> float:
        """Permet d'appeler directement la stratégie comme une fonction"""
        return self.calculate(values)

class StatisticsStrategies:
    """
    Classe qui définit toutes les stratégies de calcul statistique.
    C'est ici que réside la vraie logique de stratégie.
    """
    @staticmethod
    def mean(values: List[float]) -> float:
        return float(np.mean(values)) if values else 0.0

    @staticmethod
    def std_dev(values: List[float]) -> float:
        return float(np.std(values)) if values else 0.0

    @staticmethod
    def quartile_25(values: List[float]) -> float:
        return float(np.percentile(values, 25)) if values else 0.0

    @staticmethod
    def quartile_75(values: List[float]) -> float:
        return float(np.percentile(values, 75)) if values else 0.0

    @staticmethod
    def iqr(values: List[float]) -> float:
        if not values:
            return 0.0
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        return float(q3 - q1)

    # Définition des stratégies disponibles
    MEAN = StatisticStrategy("mean", mean)
    STD_DEV = StatisticStrategy("standard deviation", std_dev)
    QUARTILE_25 = StatisticStrategy("quartile 25", quartile_25)
    QUARTILE_75 = StatisticStrategy("quartile 75", quartile_75)
    IQR = StatisticStrategy("interquartile range", iqr)

    # Permet d'itérer sur toutes les stratégies
    @classmethod
    def all(cls):
        return [
            cls.MEAN, 
            cls.STD_DEV, 
            cls.QUARTILE_25, 
            cls.QUARTILE_75, 
            cls.IQR
        ]

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
    statistic_type: str
    value: float

class ComputeDTINormativeValues:
    def __init__(self, subjects_repository: SubjectRepository) -> None:
        self.subjects_repository = subjects_repository
    
    def extract_dti_values_by_region(self,
                                    subject: Subject,
                                    dti_metric: DTIMetric,
                                    atlas: Atlas, 
                                    atlas_label: int) -> list[float]:
        # TODO: Implement actual DTI value extraction
        return [0., 0., 0.]
    
    def compute_statistics(self,
                          subject: Subject,
                          statistic_strategy: StatisticStrategy,
                          dti_metric: DTIMetric,
                          atlas: Atlas, 
                          atlas_label: int) -> float:
        dti_values = self.extract_dti_values_by_region(subject, dti_metric, atlas, atlas_label)
        return statistic_strategy(dti_values)
    
    def execute(self, center: Center, dti_metric: DTIMetric, atlas: Atlas) -> list[NormativeValue]:
        results = []
        healthy_volunteers = self.subjects_repository.find_subjects_by_center(
            center, subject_type=SubjectType.HEALTHY_VOLUNTEER
        )

        for healthy_volunteer in healthy_volunteers:
            for atlas_label in atlas.labels:
                for statistic_strategy in StatisticsStrategies.all():
                    statistics_value = self.compute_statistics(
                        healthy_volunteer, 
                        statistic_strategy, 
                        dti_metric, 
                        atlas, 
                        atlas_label)
                    
                    normative_value = NormativeValue(
                        center=center,
                        dti_metric=dti_metric,
                        atlas=atlas,
                        atlas_label=atlas_label,
                        statistic_type=statistic_strategy.name,
                        value=statistics_value
                    )
                    results.append(normative_value)

        return results
