"""
Controllers for the OxyTCMRI project.
"""
import csv
import logging
from typing import List, Optional
import pandas

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume, Base
from pathlib import Path


def get_center_id_from_subject_id(subject_id: str) -> int:
    """Get the center id from a subject id.

    In our database, the subject id starts with the center id. As an example,
    the subject "08_001" is from the center "08".

    Parameters
    ----------
    subject_id : str
        The subject id.

    Returns
    -------
    int
        The center id.
    """
    try:
        return int(subject_id[:2])
    except ValueError:
        raise ValueError(f"Invalid center id in subject id: '{subject_id}'. "
                         f"The subject id should start with the center id.")


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

    where XX is the center id and subject_id_YY is the subject id.

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
    if subject.subject_type == "Healthy Control":
        if subject.center.id < 10:
            subject_folder = f"{data_path}/Healthy/C0{subject.center.id}/{subject.id}"
        else:
            subject_folder = f"{data_path}/Healthy/C{subject.center.id}/{subject.id}"
    else:
        if subject.center.id < 10:
            subject_folder = f"{data_path}/Patient/C0{subject.center.id}/{subject.id}"
        else:
            subject_folder = f"{data_path}/Patient/C{subject.center.id}/{subject.id}"
    return Path(subject_folder)


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


class DatabaseController:
    def __init__(self, database_url: str):
        """Create a DatabaseController instance.

        Parameters
        ----------
        database_url : str
            URL of the database.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.database_session = Session(self.engine)

    def import_data(self,
                    subjects_list_csv_file_path: str,
                    clinical_data_csv_file_path: str,
                    dti_data_path: str,
                    structural_mri_data_path: str
                    ) -> None:
        """Import data from a CSV file into the database.

        First, import the subjects from the CSV file.
        Second, import the clinical data from the Excel file.
        Then, add the MRI volumes to the database (DTI and structural MRI).

        Parameters
        ----------
        subjects_list_csv_file_path : str
            Path to the CSV file containing the subjects list.
        clinical_data_csv_file_path : str
            Path to the Excel file containing the clinical data.
        dti_data_path : str
            Path to the DTI (Diffusion Tensor Imaging) data folder.
        structural_mri_data_path : str
            Path to the "structural" MRI (T1, T2, etc.) data folder.

        Returns
        -------
        None
        """
        self.import_subjects_from_csv(subjects_list_csv_file_path)
        self.import_outcome_data_from_xlsx(clinical_data_csv_file_path)
        self.add_mri_volumes(dti_data_path)
        self.add_mri_volumes(structural_mri_data_path)

    def import_subjects_from_csv(self, csv_file_path: str):
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Extract data from the CSV row
                subject_id = row['subjectId']
                center_name = row['center']
                subject_type = row['subjectType']

                # Look up the center by id or create it if it doesn't exist
                center = self.get_or_create_center(get_center_id_from_subject_id(subject_id),
                                                   center_name)

                # Check if the subject already exists in the database
                existing_subject = self.database_session.query(Subject).filter_by(id=subject_id).first()

                # If the subject doesn't exist, create a new one
                if not existing_subject:
                    new_subject = Subject(
                        id=subject_id,
                        subject_type=subject_type,
                        center=center,
                        gose_6_months=None,
                        gose_12_months=None
                    )
                    self.database_session.add(new_subject)

        # Commit changes to the database
        self.database_session.commit()

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

    def export_md_lesions_to_csv(self, csv_file_path: str, quantiles: str = "7_94") -> None:
        """Export all MD lesions (high and low) to a CSV file.

        Parameters
        ----------
        csv_file_path : str
            Path to the CSV file.

        quantiles : str
            Should be "7_94" or "5_95", which means that we take the 7% and 94% quantiles
            or the 5% and 95% quantiles.

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
                          'low_MD_lesions_in_mL',
                          'high_MD_lesions_in_mL',
                          'gose_6_months',
                          'gose_12_months']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()

            # For each subject, get the volume corresponding to the MD lesions
            for subject in subjects:
                if subject.subject_type != "Patient":
                    continue

                try:
                    # Get the volume corresponding to the MD lesions
                    low_md_lesions_volume = subject.compute_mean_diffusivity_lesions_volume(quantiles, "low")
                    high_md_lesions_volume = subject.compute_mean_diffusivity_lesions_volume(quantiles, "high")
                except ValueError:
                    low_md_lesions_volume = ""
                    high_md_lesions_volume = ""

                # Write the data to the CSV file
                writer.writerow({'subject_id': subject.id,
                                 'center_id': subject.center.id,
                                 'center_name': subject.center.name,
                                 'low_MD_lesions_in_mL': low_md_lesions_volume,
                                 'high_MD_lesions_in_mL': high_md_lesions_volume,
                                 'gose_6_months': subject.gose_6_months,
                                 'gose_12_months': subject.gose_12_months, }
                                )

    def import_outcome_data_from_xlsx(self, outcome_data_xlsx_file_path: str) -> None:
        """
        Import clinical data from a CSV file into the database.

        Parameters
        ----------
        outcome_data_xlsx_file_path : str
            Path to the CSV file containing the clinical data.
        """
        outcome_data = pandas.read_excel(outcome_data_xlsx_file_path, sheet_name="data")
        logging.info(f"Imported outcome data from {outcome_data_xlsx_file_path}")

        for index, row in outcome_data.iterrows():
            # Extract data from the CSV row
            patient_secondary_id = row["id_secondaire"]
            gose_6_month = row["GOSE_6M"]
            gose_12_month = row["GOSE_12M"]

            # Find the subject in the database
            patient = self.find_subject_by_secondary_id(patient_secondary_id)

            # Update the subject in the database
            if patient is not None:
                patient.update_gose(delay_in_month=6, gose_score=gose_6_month)
                patient.update_gose(delay_in_month=12, gose_score=gose_12_month)

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
