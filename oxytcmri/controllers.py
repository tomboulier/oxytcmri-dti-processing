"""
Controllers for the OxyTCMRI project.
"""
import csv
import logging
import os
import warnings
from typing import List, Optional
from urllib.parse import urlparse

import pandas

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume, Base
from oxytcmri.data_import import DataImporter
from pathlib import Path

from oxytcmri.utils import marshall_score_string_to_int, get_sex_from_initials


def get_subject_folder_path(data_path: str, subject: Subject) -> Path:
    """Get the path to the subject folder.

    MRI Volumes from Pixyl are organized in a tree directory with the
    following structure:

    .. code-block:: text

        ├── Healthy/
           ├── CXX/
                ├── subject_id_YY/
                ├── ...
        ├── Patient
            ├── ...

    where XX is the center id and subject_id_YY is the subject id (in lowercase).

    Parameters
    ----------
    data_path: str
        The path to the data folder, containing the folder structure described above.

    subject : Subject
        The subject for which we want to get the path to the folder.

    Returns
    -------
    Path
        The absolute path to the subject folder: `data_path/{Healthy|Patient}/CXX/subject_id_YY`
    """
    subject_type_folder = "Healthy" if subject.subject_type == "Healthy Control" else "Patient"
    subject_folder = f"{data_path}/{subject_type_folder}/C{subject.center.id:02}/{subject.id.lower()}"

    subject_folder_path = Path(subject_folder)

    return subject_folder_path


def get_subject_type_from_initials(secondary_id: str) -> str:
    """Get the subject type from the initials of the secondary id.

    Parameters
    ----------
    secondary_id : str
        The secondary id.

    Returns
    -------
    str
        The subject type, which is either "Healthy Control", "Patient" or "Patient Test".

    Raises
    ------
    ValueError
        If the initials are not "V", "P" or "T".
    """
    initials = secondary_id[6]
    if initials == "V":
        return "Healthy Control"
    elif initials == "P":
        return "Patient"
    elif initials == "T":
        return "Patient Test"
    else:
        raise ValueError(f"Invalid subject type: {initials}")


def gose_evaluation_to_score(gose_evaluation: str) -> Optional[int]:
    """Convert a GOSE evaluation to a GOSE score.

    Parameters
    ----------
    gose_evaluation : str
        The GOSE evaluation.

    Returns
    -------
    int
        The GOSE score.

    Raises
    ------
    ValueError
        If the GOSE evaluation is not valid."""
    if gose_evaluation == "":
        return None
    else:
        return int(gose_evaluation[-2])


def convert_pbto2_code_to_boolean(code: str) -> Optional[bool]:
    """Convert the PbtO2 code ("A" or "B") to the presence of PbtO2 (True or False).
    In the CSV file, the PbtO2 code is written as "A" or "B", where:
    - "A" means that the patient is not monitored with PbtO2,
    - "B" means that the patient is monitored with PbtO2.

    Parameters
    ----------
    code : str
        The PbtO2 code.

    Returns
    -------
    bool
        True if the patient has PbtO2, False otherwise.

    Raises
    ------
    ValueError
        If the PbtO2 code is not valid.
    """
    if code == "A":
        return False
    elif code == "B":
        return True
    else:
        raise ValueError(f"Invalid PbtO2 code: {code}")


class DatabaseController:
    def __init__(self, settings, overwrite: bool = False):
        """Create a DatabaseController instance.

        Parameters
        ----------
        settings : Dynaconf
            The settings.
        """
        # Parse the database URL to extract the file path (for SQLite)
        parsed_url = urlparse(settings.database.url)
        db_file_path = parsed_url.path

        # Check if the database file exists
        if os.path.exists(db_file_path) and not overwrite:
            print("Database file exists. Using the existing database.")
        else:
            if os.path.exists(db_file_path):
                print("Overwriting existing database.")
                os.remove(db_file_path)

        self.engine = create_engine(settings.database.url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine, autoflush=False)
        self.database_session = Session()

    def import_data(self, settings) -> None:
        """Import data from a CSV file into the database.

        First, import the subjects from the CSV file.
        Second, import the clinical data from the Excel file.
        Then, add the MRI volumes to the database (DTI and structural MRI).

        Parameters
        ----------
        settings : Dynaconf
            The settings.
        Returns
        -------
        None
        """
        data_importer = DataImporter(settings, self)
        data_importer.import_data()

        self.add_mri_volumes(settings.paths.DTIDataPath)
        self.add_mri_volumes(settings.paths.StructuralDataPath)
        self.import_pbto2_from_csv(settings.paths.PbtO2Data)

    def get_or_create_center(self, center_id: int, center_name: str) -> Center:
        """Get or create a center in the database:
            - If the center doesn't exist, create a new one and return it.
            - If the center exists, return it.


        Parameters
        ----------
        center_id : int
            The center id.

        center_name : str
            The center name.

        Returns
        -------
        Center
            The center.
        """
        # Check if the center already exists in the database
        existing_center = self.database_session.query(Center).filter_by(id=center_id).first()

        # If the center doesn't exist, create a new one
        if not existing_center:
            new_center = Center(id=center_id, name=center_name)
            self.database_session.add(new_center)
            self.database_session.commit()
            return new_center

        return existing_center

    def add_mri_volumes(self, data_path: str) -> None:
        """Add MRI volumes to the database.

        For each subject in the database, this method will look up for all the
        .nii.gz files in the folder corresponding to the subject, and add a corresponding
        volume to the MRIExam model. If this latter does not exists, it will be created.
        The structure of the data folder is the following:
        - it has two subfolders "Healthy" and "Patient"
        - in each subfolder, there are subfolders for each center, denoted "CXX" where XX is the center id
        - in each center subfolder, there are subfolders for each subject, denoted "XX" where XX is the subject id


        Parameters
        ----------
        data_path : str
            Path to the MRI data folder.

        Returns
        -------
        None
        """
        subjects = self.get_all_subjects()

        # For each subject, look up for the corresponding .nii.gz files
        for subject in subjects:
            # Check if the MRIExam already exists in the database
            mri_exam = self.database_session.query(MRIExam).filter_by(subject=subject).first()

            # If the MRIExam doesn't exist, create a new one
            if not mri_exam:
                mri_exam = MRIExam(subject=subject)
                self.database_session.add(mri_exam)

            subject_folder = get_subject_folder_path(data_path, subject)

            if not subject_folder.exists():
                warnings.warn(f"Folder does not exist: {subject_folder}", RuntimeWarning)
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
                self.database_session.add(mri_volume)

        # Commit changes to the database
        self.database_session.commit()

    def get_all_subjects(self) -> List[Subject]:
        """Get all the subjects from the database"""
        return self.database_session.query(Subject).all()

    def get_subject(self, subject_id: str) -> Subject:
        """Get a subject from the database.

        Parameters
        ----------
        subject_id : str
            The subject id.

        Returns
        -------
        Subject
            The subject.
        """
        subject = self.database_session.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            raise ValueError(f"Subject not found: {subject_id}")

        return subject

    def get_mri_volume(self, subject_id: str, volume_name: str) -> MRIVolume:
        """Get an MRI volume from the database.

        Parameters
        ----------
        subject_id : str
            The subject id.

        volume_name : str
            The volume name.

        Returns
        -------
        MRIVolume
            The MRI volume.
        """
        subject = self.database_session.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            raise ValueError(f"Subject not found: {subject_id}")

        mri_exam = self.database_session.query(MRIExam).filter_by(subject=subject).first()
        if not mri_exam:
            raise ValueError(f"MRI exam not found for subject {subject_id}")

        mri_volume = self.database_session.query(MRIVolume).filter_by(name=volume_name,
                                                                      exam=mri_exam).first()
        if not mri_volume:
            raise ValueError(f"Volume not found: {volume_name} for MRI Exam {mri_exam.id}")

        return mri_volume

    def export_md_lesions_to_csv(self, csv_file_path: str) -> None:
        """Export all MD lesions (high and low) to a CSV file.

        Parameters
        ----------
        csv_file_path : str
            Path to the CSV file.

        Returns
        -------
        None
        """
        # Get all the subjects from the database
        subjects = self.get_all_subjects()

        # Create the CSV file
        with open(csv_file_path, mode='w') as csv_file:
            fieldnames = ['subject_id',
                          'center_id',
                          'center_name',
                          'low_MD_lesions_in_mL_7_94',
                          'high_MD_lesions_in_mL_7_94',
                          'low_MD_lesions_in_mL_10_95',
                          'high_MD_lesions_in_mL_10_95',
                          'gose_6_months',
                          'gose_12_months',
                          'impact_score_mortality',
                          'impact_score_neurological_outcome',
                          'marshall_score',
                          'pbto2',
                          'age',
                          'sex',
                          'glasgow_coma_scale',
                          ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()

            # For each subject, get the volume corresponding to the MD lesions
            for subject in subjects:
                if subject.subject_type != "Patient":
                    continue

                try:
                    # Get the volume corresponding to the MD lesions
                    low_md_lesions_volume_7_94 = subject.compute_mean_diffusivity_lesions_volume(quantiles="7_94",
                                                                                                 lesion_type="low")
                    high_md_lesions_volume_7_94 = subject.compute_mean_diffusivity_lesions_volume(quantiles="7_94",
                                                                                                  lesion_type="high")
                    low_md_lesions_volume_10_95 = subject.compute_mean_diffusivity_lesions_volume(quantiles="10_95",
                                                                                                  lesion_type="low")
                    high_md_lesions_volume_10_95 = subject.compute_mean_diffusivity_lesions_volume(quantiles="10_95",
                                                                                                   lesion_type="high")
                except ValueError:
                    low_md_lesions_volume_7_94 = ""
                    high_md_lesions_volume_7_94 = ""
                    low_md_lesions_volume_10_95 = ""
                    high_md_lesions_volume_10_95 = ""

                # Write the data to the CSV file
                writer.writerow({'subject_id': subject.id,
                                 'center_id': subject.center.id,
                                 'center_name': subject.center.name,
                                 'low_MD_lesions_in_mL_7_94': low_md_lesions_volume_7_94,
                                 'high_MD_lesions_in_mL_7_94': high_md_lesions_volume_7_94,
                                 'low_MD_lesions_in_mL_10_95': low_md_lesions_volume_10_95,
                                 'high_MD_lesions_in_mL_10_95': high_md_lesions_volume_10_95,
                                 'gose_6_months': subject.gose_6_months,
                                 'gose_12_months': subject.gose_12_months,
                                 'impact_score_mortality': subject.impact_score_mortality,
                                 'impact_score_neurological_outcome': subject.impact_score_neurological_outcome,
                                 'marshall_score': subject.marshall_score,
                                 'pbto2': subject.pbto2,
                                 'age': subject.age,
                                 'sex': subject.sex,
                                 'glasgow_coma_scale': subject.glasgow_coma_scale,
                                 }
                                )

    def import_pbto2_from_csv(self, pbto2_csv_file_path: str) -> None:
        """
        Import pbto2 data from a CSV file into the database.

        Parameters
        ----------
        pbto2_csv_file_path : str
            Path to the CSV file containing the pbto2 data.
        """
        pbto2_data = pandas.read_csv(pbto2_csv_file_path, sep=";")

        for index, row in pbto2_data.iterrows():
            # Extract data from the CSV row
            patient_secondary_id = row["ID_SECONDAIRE"]
            pbto2 = convert_pbto2_code_to_boolean(row["CODE_BRAS"])

            # Find the subject in the database
            patient = self.find_subject_by_secondary_id(patient_secondary_id)

            # Update the subject in the database
            if patient is not None:
                patient.pbto2 = pbto2

        self.database_session.commit()
        logging.info(f"Imported pbto2 data from {pbto2_csv_file_path}")

    def find_subject_by_secondary_id(self, secondary_id: str) -> Subject:
        """Find a subject by its secondary id.

        The secondary id is encoded in the CSV file as "ID_SECONDAIRE". It is written as
        "XX-YY-Z" where:
         - XX is the center id,
         - YY is the subject's number in the center (method "get_number_within_center"),
         - Z is the subject type (V for healthy volunteer, P for patient, T for Test).

        Parameters
        ----------
        secondary_id : str
            The patient secondary id, which is encoded in the CSV file
            as "ID_SECONDAIRE".
        """
        # Extract the center id from the secondary id
        center_id = int(secondary_id[:2])

        # Extract the subject number within the center from the secondary id
        subject_number_within_center = int(secondary_id[3:5])

        # Extract the subject type from the secondary id
        subject_type = get_subject_type_from_initials(secondary_id)

        # Get the center
        center = self.database_session.query(Center).filter_by(id=center_id).first()

        # Get all the subjects of this center
        subjects = self.database_session.query(Subject).filter_by(center=center).all()

        # Get the subject with the given number within the center, and the given type
        for subject in subjects:
            if subject.get_number_within_center() == subject_number_within_center:
                if subject.subject_type == subject_type:
                    return subject

        return None
