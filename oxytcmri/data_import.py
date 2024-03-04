"""

"""
import csv
import logging
import warnings
from abc import ABC, abstractmethod

import pandas

from oxytcmri.models import get_center_id_from_subject_id, Subject, MRIExam, MRIVolume
from oxytcmri.utils import marshall_score_string_to_int, get_sex_from_initials, get_subject_folder_path, \
    convert_pbto2_code_to_boolean


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
        self.outcome_data_filepath = settings.paths.ClinicalData
        self.pbto2_data_filepath = settings.paths.PbtO2Data
        self.database_controller = database_controller

    def import_data(self):
        self.import_outcome_data(source_filepath=self.outcome_data_filepath)
        self.import_pbto2_data(source_filepath=self.pbto2_data_filepath)

    def import_pbto2_data(self, source_filepath):
        """
                Import pbto2 data from a CSV file into the database.

                Parameters
                ----------
                source_filepath : str
                    Path to the CSV file containing the pbto2 data.
                """
        pbto2_data = pandas.read_csv(source_filepath, sep=";")

        for index, row in pbto2_data.iterrows():
            # Extract data from the CSV row
            patient_secondary_id = row["ID_SECONDAIRE"]
            pbto2 = convert_pbto2_code_to_boolean(row["CODE_BRAS"])

            # Find the subject in the database
            patient = self.database_controller.find_subject_by_secondary_id(patient_secondary_id)

            # Update the subject in the database
            if patient is not None:
                patient.pbto2 = pbto2

        self.database_controller.database_session.commit()
        logging.info(f"Imported pbto2 data from {source_filepath}")

    def import_outcome_data(self, source_filepath):
        outcome_data = pandas.read_excel(source_filepath, sheet_name="data")

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
        logging.info(f"Imported outcome data from {source_filepath}")


class MRIVolumesImporter(Importer):
    """Add MRI volumes to the database.

    Parameters
    ----------
    mri_data_folder: str
        Path to the MRI data folder.
    database_controller : DatabaseController
        The database controller responsible for database operations.

    Returns
    -------
    None
    """

    def __init__(self, settings, mri_type, database_controller):
        self.database_controller = database_controller

        if mri_type == "structural":
            self.mri_data_folder = settings.paths.StructuralDataPath
        elif mri_type == "dti":
            self.mri_data_folder = settings.paths.DTIDataPath
        else:
            raise ValueError(f"Unsupported mri_type: {mri_type}. Expected 'structural' or 'dti'.")

    def import_data(self):
        """Add MRI volumes to the database.

        For each subject in the database, this method will look up for all the
        .nii.gz files in the folder corresponding to the subject, and add a corresponding
        volume to the MRIExam model. If this latter does not exists, it will be created.
        The structure of the data folder is the following:
        - it has two subfolders "Healthy" and "Patient"
        - in each subfolder, there are subfolders for each center, denoted "CXX" where XX is the center id
        - in each center subfolder, there are subfolders for each subject, denoted "XX" where XX is the subject id
        """
        subjects = self.database_controller.get_all_subjects()

        # For each subject, look up for the corresponding .nii.gz files
        for subject in subjects:
            # Check if the MRIExam already exists in the database
            mri_exam = self.database_controller.database_session.query(MRIExam).filter_by(subject=subject).first()

            # If the MRIExam doesn't exist, create a new one
            if not mri_exam:
                mri_exam = MRIExam(subject=subject)
                self.database_controller.database_session.add(mri_exam)

            subject_folder = get_subject_folder_path(self.mri_data_folder, subject)

            if not subject_folder.exists():
                logging.warning(f"MRIVolumes import failed, folder does not exist: {subject_folder}")
                continue  # Skip to the next subject if the folder does not exist

            # Get the path to the .nii.gz files
            nii_files = subject_folder.glob("*.nii.gz")

            # For each .nii.gz file, add a volume to the MRIExam model
            for nii_file in nii_files:
                # see https://stackoverflow.com/questions/31890341/clean-way-to-get-the-true-stem-of-a-path-object
                nii_file_basename = nii_file.stem.split('.')[0]

                # Add the volume to the MRIExam
                mri_volume = MRIVolume(name=nii_file_basename,
                                       filepath=str(nii_file),
                                       exam=mri_exam)
                self.database_controller.database_session.add(mri_volume)

        # Commit changes to the database
        self.database_controller.database_session.commit()


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
            MRIVolumesImporter(settings, "structural", database_controller),
            MRIVolumesImporter(settings, "dti", database_controller),
            # Add other importers here...
        ]

    def import_data(self):
        for importer in self.importers_list:
            importer.import_data()
