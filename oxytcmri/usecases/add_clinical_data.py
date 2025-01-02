"""
This use case is to add clinical data to the file containing the clinical data.

Dependency injection is used to model the inputs:
- clinical data: ClinicalDataRepository
- additional clinical data: AdditionalClinicalDataRepository
"""
from abc import ABC, abstractmethod
import csv

from oxytcmri.models import Subject


class ClinicalDataRepository(ABC):
    @abstractmethod
    def import_dictionary_of_clinical_data(self, clinical_data: dict) -> None:
        """
        Import a dictionary of clinical data into the clinical data file.
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

class CSVAdditionalClinicalDataRepository(AdditionalClinicalDataRepository):
    def __init__(self, filepath: str,
                 subject_id_column_name: str,
                 clinical_data_column_name: str,
                 delimiter: str):
        self.filepath = filepath
        self.subject_id_column_name = subject_id_column_name
        self.clinical_data_column_name = clinical_data_column_name
        self.delimiter = delimiter

    def csv_reader(self) -> csv.reader:
        try:
            with open(self.filepath, mode='r') as file:
                reader = csv.DictReader(file, delimiter=self.delimiter)
                for row in reader:
                    yield row
        except FileNotFoundError:
            raise FileNotFoundError(f"File {self.filepath} not found.")

    def extract_data(self) -> dict:
        """
        Extract data from the additional clinical data file.
        It returns a dictionary with the subject as key and the clinical data as value.

        The id of the subject is of the form "XX-YY-P", where:
        - "XX" is the site number,
        - "YY" is the subject number,
        - and "P" stands for "patient".
        This id is used to create an instance of the Subject class.
        It is found in the column whose name is given by the attribute subject_id_column_name.

        The values of the clinical data are found in the columns whose name is given by the attribute
        clinical_data_column_name.
        """
        clinical_data = {}
        for row in self.csv_reader():
            subject_id = row[self.subject_id_column_name]
            clinical_data[Subject(id=subject_id)] = row[self.clinical_data_column_name]
        return clinical_data



class AddClinicalData:
    def __init__(self,
                 clinical_data_repo: ClinicalDataRepository,
                 additional_clinical_data_repo: AdditionalClinicalDataRepository):
        self.clinical_data_repo = clinical_data_repo
        self.additional_clinical_data_repo = additional_clinical_data_repo

    def execute(self) -> None:
        additional_clinical_data = self.additional_clinical_data_repo.extract_data()
        self.clinical_data_repo.import_dictionary_of_clinical_data(additional_clinical_data)