from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas

class ComputeDTIReferenceValues:
    def execute(self, center: Center, dti_metric: DTIMetric, atlas: Atlas) -> None:
        pass
