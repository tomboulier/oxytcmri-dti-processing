"""
This use case is to add clinical data to the file containing the clinical data.

Dependency injection is used to model the inputs:
- clinical data: ClinicalDataRepository
- additional clinical data: AdditionalClinicalDataRepository
"""
from abc import ABC, abstractmethod


class ClinicalDataRepository(ABC):
    @abstractmethod
    def import_dictionary_of_clinical_data(self, clinical_data: dict) -> None:
        """
        Import a dictionary of clinical data into the clinical data file.
        """
        pass

class ExcelClinicalDataRepository(ClinicalDataRepository):
    def __init__(self, filepath: str):
        self.filepath = filepath

    def import_dictionary_of_clinical_data(self, clinical_data: dict) -> None:
        """
        Import a dictionary of clinical data into the clinical data file.

        The clinical data is a dictionary with the subject as key and the clinical data as value.
        """
        pass

class AdditionalClinicalDataRepository(ABC):
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
        additional_clinical_data = self.additional_clinical_data_repo.extract_data()
        self.clinical_data_repo.import_dictionary_of_clinical_data(additional_clinical_data)