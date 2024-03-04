"""

"""
import csv
import logging
from abc import ABC, abstractmethod

import pandas

from oxytcmri.models import get_center_id_from_subject_id, Subject
from oxytcmri.utils import marshall_score_string_to_int, get_sex_from_initials


class Importer(ABC):
    """
    Abstract base class for data importers.

    This class defines the interface that all data importer subclasses must implement.

    Methods
    -------
    import_data()
        Abstract method to import data from a specified source.
    """

    @abstractmethod
    def import_data(self):
        pass


class SubjectsListImporter(Importer):
    """
    Imports a list of subjects from a CSV file.

    This importer reads subjects' data from a CSV file and updates the database accordingly.
    This CSV file must contain 3 columns: 'subjectId', 'center', and 'subjectType'.

    Parameters
    ----------
    settings
        The application settings object, containing paths and configuration.
    database_controller : DatabaseController
        The database controller responsible for database operations.

    Methods
    -------
    import_data()
        Reads the CSV file specified in settings, and creates centers and subjects accordingly.
    """

    def __init__(self, settings, database_controller):
        self.filepath = settings.paths.SubjectsList
        self.database_controller = database_controller

    def import_data(self):
        with open(self.filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Extract data from the CSV row
                subject_id = row['subjectId']
                center_name = row['center']
                subject_type = row['subjectType']

                # Look up the center by id or create it if it doesn't exist
                center = self.database_controller.get_or_create_center(get_center_id_from_subject_id(subject_id),
                                                                       center_name)

                # Check if the subject already exists in the database
                existing_subject = self.database_controller.database_session.query(Subject) \
                    .filter_by(id=subject_id) \
                    .first()

                # If the subject doesn't exist, create a new one
                if not existing_subject:
                    new_subject = Subject(
                        id=subject_id,
                        subject_type=subject_type,
                        center=center,
                        gose_6_months=None,
                        gose_12_months=None
                    )
                    self.database_controller.database_session.add(new_subject)

        # Commit changes to the database
        self.database_controller.database_session.commit()


class ClinicalDataImporter(Importer):
    """
    Import clinical data from an Excel (*.xlsx) file into the database.
    
    Parameters
    ----------
    settings
        The application settings object, containing the path to the *.xlsx file containing the clinical data,
         and configuration.
    database_controller : DatabaseController
        The database controller responsible for database operations.

    Methods
    -------
    import_data()
        Reads the Excel file specified in settings and updates the database with clinical information.
    """

    def __init__(self, settings, database_controller):
        self.filepath = settings.paths.ClinicalData
        self.database_controller = database_controller

    def import_data(self):
        outcome_data = pandas.read_excel(self.filepath, sheet_name="data")

        for index, row in outcome_data.iterrows():
            # Extract data from the CSV row
            patient_secondary_id = row["id_secondaire"]
            gose_6_month = row["GOSE_6M"]
            gose_12_month = row["GOSE_12M"]
            impact_score_mortality = row["impact_mort_ext_pred"]
            impact_score_neurological_outcome = row["impact_cfuo_ext_pred"]
            marshall_score = marshall_score_string_to_int(row["tdmadm_marshall_score"])
            age = row["age_adm"]
            sex = get_sex_from_initials(row["sexe_patient"])
            glasgow_coma_scale = float("nan") if row["char_gcs_tot"] == "nan" else row["char_gcs_tot"]

            # Find the subject in the database
            patient = self.database_controller.find_subject_by_secondary_id(patient_secondary_id)

            # Update the subject in the database
            if patient is not None:
                patient.update_gose(delay_in_month=6, gose_score=gose_6_month)
                patient.update_gose(delay_in_month=12, gose_score=gose_12_month)
                patient.impact_score_mortality = impact_score_mortality
                patient.impact_score_neurological_outcome = impact_score_neurological_outcome
                patient.marshall_score = marshall_score
                patient.age = age
                patient.sex = sex
                patient.glasgow_coma_scale = glasgow_coma_scale

        self.database_controller.database_session.commit()
        logging.info(f"Imported outcome data from {self.filepath}")


class DataImporter:
    """
    Manages the import of different types of data through multiple importers.

    This class holds a list of data importers and iterates over them to import data from various sources.

    Parameters
    ----------
    settings
        The application settings object, containing paths and configuration.
    database_controller : DatabaseController
        The database controller responsible for database operations.

    Methods
    -------
    import_data()
        Executes the import_data method of each importer in the importers_list.
    """

    def __init__(self, settings, database_controller):
        self.database_controller = database_controller
        self.importers_list = [
            SubjectsListImporter(settings, database_controller),
            ClinicalDataImporter(settings, database_controller),
            # Add other importers here...
        ]

    def import_data(self):
        for importer in self.importers_list:
            importer.import_data()
