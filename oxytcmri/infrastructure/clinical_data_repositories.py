import csv

from oxytcmri.models import Subject
from oxytcmri.usecases.add_clinical_data import AdditionalClinicalDataRepository


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
