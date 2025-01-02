"""
This use case is to add clinical data to the file containing the clinical data.

Dependency injection is used to model the inputs:
- clinical data: ClinicalDataRepository
- additional clinical data: AdditionalClinicalDataRepository
"""
from abc import ABC, abstractmethod

class ClinicalDataRepository(ABC):
    @abstractmethod
    def __init__(self):
        pass

class AdditionalClinicalDataRepository(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def extract_data(self) -> dict:
        """
        Extract data from the additional clinical data file.
        It returns a dictionary with the subject as key and the clinical data as value.
        """
        pass

class AddClinicalData:
    def __init__(self,
                 clinical_data_repo: ClinicalDataRepository,
                 additional_clinical_data_repo: AdditionalClinicalDataRepository):
        self.clinical_data_repo = clinical_data_repo
        self.additional_clinical_data_repo = additional_clinical_data_repo

    def execute(self) -> None:
        pass