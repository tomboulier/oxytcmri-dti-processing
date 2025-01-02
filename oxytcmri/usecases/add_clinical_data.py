"""
This use case is to add clinical data to the file containing the clinical data.

Dependency injection is used to model the inputs:
- clinical data: ClinicalDataRepository
- additional clinical data: AdditionalClinicalDataRepository
"""

class ClinicalDataRepository:
    def __init__(self):
        pass

class AdditionalClinicalDataRepository:
    def __init__(self):
        pass

class AddClinicalDataUseCase:
    def __init__(self,
                 clinical_data_repo: ClinicalDataRepository,
                 additional_clinical_data_repo: AdditionalClinicalDataRepository):
        self.clinical_data_repo = clinical_data_repo
        self.additional_clinical_data_repo = additional_clinical_data_repo

    def execute(self) -> None:
        pass