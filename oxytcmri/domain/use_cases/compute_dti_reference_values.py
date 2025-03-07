from dataclasses import dataclass
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas
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
    def execute(self, center: Center, dti_metric: DTIMetric, atlas: Atlas) -> list[NormativeValue]:
        results = [
            NormativeValue(
                atlas=atlas,
                center=center,
                dti_metric=dti_metric,
                statistic_type=StatisticType.MEAN,
                atlas_label=1,
                value=5.0
            ),
            NormativeValue(
                atlas=atlas,
                center=center,
                dti_metric=dti_metric,
                statistic_type=StatisticType.MEAN,
                atlas_label=2,
                value=4.0
            ),
            NormativeValue(
                atlas=atlas,
                center=center,
                dti_metric=dti_metric,
                statistic_type=StatisticType.STD_DEV,
                atlas_label=1,
                value=1.0
            ),
        ]
        return results
