"""
This use case is to add clinical data to the file containing the clinical data.

Dependency injection is used to model the inputs:
- clinical data: ClinicalDataRepository
- additional clinical data: AdditionalClinicalDataRepository
"""
from abc import ABC, abstractmethod
from typing import ItemsView, Callable

from oxytcmri.models import Subject


class AdditionalClinicalData[T]:
    """
    Model for additional clinical data.

    Attributes:
    ------------

    name: str
        Name of the clinical data.

    values: dict
        Dictionary with the subject as key and the clinical data as a string representing the value.
    """

    def __init__(self, name: str):
        """
        Create an instance of the AdditionalClinicalData class.
        """
        self.name = name
        self.values = {}

    def add(self, subject: Subject, string_value: str) -> None:
        """
        Add a clinical data to the dictionary.
        """
        self.values[subject] = string_value

    def get(self, subject) -> str | None:
        """
        Get the clinical data of a subject.
        """
        try:
            return self.values[subject]
        except KeyError:
            return None

    def get_all(self) -> ItemsView[Subject, T]:
        """
        Get all the clinical data.
        """
        return self.values.items()

class ClinicalDataDecoder[T]:
    def __init__(self, new_name: str, decoder: Callable[[str], T]):
        """
        Create an instance of the ClinicalDataDecoder class, which is used to "decode" clinical data, meaning that
        it converts the string representation of the data into the appropriate representation.

        Parameters
        ----------
        new_name : str
            The name of the new clinical data.

        decoder : Callable[[str], T]
            A function that takes a string as input and returns a value of type T.
        """
        self.new_name = new_name
        self.decoder = decoder

    def decode(self, additional_clinical_data: AdditionalClinicalData) -> AdditionalClinicalData:
        """
        Decode the clinical data.

        Parameters
        ----------
        additional_clinical_data : AdditionalClinicalData
            The clinical data to be decoded.
        """
        new_additional_clinical_data = AdditionalClinicalData(name=self.new_name)
        for subject, value in additional_clinical_data.get_all():
            new_additional_clinical_data.add(subject, self.decoder(value))
        return new_additional_clinical_data

class ClinicalDataRepository(ABC):
    @abstractmethod
    def import_additional_clinical_data(self,
                                        clinical_data: AdditionalClinicalData,
                                        decoder: ClinicalDataDecoder) -> None:
        """
        Import a dictionary of clinical data into the clinical data file.
        """
        pass

class AdditionalClinicalDataRepository(ABC):
    @abstractmethod
    def extract_data(self) -> AdditionalClinicalData:
        """
        Extract data from the additional clinical data file.
        It returns a dictionary with the subject as key and the clinical data as value.
        """
        pass

class AddClinicalData:
    def __init__(self,
                 clinical_data_repo: ClinicalDataRepository,
                 additional_clinical_data_repo: AdditionalClinicalDataRepository,
                 clinical_data_decoder: ClinicalDataDecoder = ClinicalDataDecoder(new_name="new_data",
                                                                                  decoder= lambda x:x)
                 ):
        self.clinical_data_repo = clinical_data_repo
        self.additional_clinical_data_repo = additional_clinical_data_repo
        self.clinical_data_decoder = clinical_data_decoder

    def execute(self) -> None:
        additional_clinical_data = self.additional_clinical_data_repo.extract_data()
        self.clinical_data_repo.import_additional_clinical_data(additional_clinical_data,self.clinical_data_decoder)