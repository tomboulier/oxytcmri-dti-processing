import csv

import pandas

from oxytcmri.models import Subject
from oxytcmri.usecases.add_clinical_data import (
    AdditionalClinicalDataRepository,
    ClinicalDataRepository,
    AdditionalClinicalData,
    ClinicalDataDecoder,
)


class CSVAdditionalClinicalDataRepository(AdditionalClinicalDataRepository):
    def __init__(
        self,
        filepath: str,
        subject_id_column_name: str,
        clinical_data_column_name: str,
        delimiter: str,
    ):
        self.filepath = filepath
        self.subject_id_column_name = subject_id_column_name
        self.clinical_data_column_name = clinical_data_column_name
        self.delimiter = delimiter

    def csv_reader(self) -> csv.reader:
        try:
            with open(self.filepath, mode="r") as file:
                reader = csv.DictReader(file, delimiter=self.delimiter)
                for row in reader:
                    yield row
        except FileNotFoundError:
            raise FileNotFoundError(f"File {self.filepath} not found.")

    def extract_data(self) -> AdditionalClinicalData:
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
        additional_clinical_data = AdditionalClinicalData(
            name=self.clinical_data_column_name
        )
        for row in self.csv_reader():
            subject_id = row[self.subject_id_column_name]
            additional_clinical_data.add(
                subject=Subject(id=subject_id),
                string_value=row[self.clinical_data_column_name],
            )
        return additional_clinical_data


class ExcelClinicalDataRepository(ClinicalDataRepository):
    def __init__(self, filepath: str, subject_id_column_name: str):
        self.filepath = filepath
        self.subject_id_column_name = subject_id_column_name

    def import_additional_clinical_data(
        self,
        additional_clinical_data: AdditionalClinicalData,
        decoder: ClinicalDataDecoder,
    ) -> None:
        """
        Import clinical data into the Excel file.

        Parameters
        ----------
        additional_clinical_data : AdditionalClinicalData
            The additional clinical data to be imported into the Excel file.

        decoder: ClinicalDataDecoder
            An instance of ClinicalDataDecoder, meant to decode data into the appropriate representation.
        """
        # decode the Additional Clinical Data
        additional_clinical_data = decoder.decode(additional_clinical_data)

        # open the Excel file located in self.filepath
        df = pandas.read_excel(self.filepath)

        # create a new column with the name of the clinical data
        df[additional_clinical_data.name] = decoder.new_name

        # fill this column with values: for each subject in the column with name self.subject_id_column_name, get the
        # data in the AdditionalClinicalData, and place it in the new column
        for index, row in df.iterrows():
            subject_id = row[self.subject_id_column_name]
            df.at[index, additional_clinical_data.name] = additional_clinical_data.get(
                Subject(id=subject_id)
            )

        # save the new DataFrame in the Excel file
        df.to_excel(self.filepath, index=False)
