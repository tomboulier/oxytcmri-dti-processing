"""
Controllers for the OxyTCMRI project.
"""
import csv
from typing import List

from sqlalchemy.orm import Session
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume
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


class DatabaseController:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def import_data(self, subjects_list_csv_file_path: str, mri_data_path: str) -> None:
        """Import data from a CSV file into the database.
        First, import the subjects from the CSV file.
        Then, add the MRI volumes to the database.

        :param subjects_list_csv_file_path: str, path to the CSV file
        :param mri_data_path: str, path to the MRI data folder
        :return: None
        """
        self.import_subjects_from_csv(subjects_list_csv_file_path)
        self.add_mri_volumes(mri_data_path)

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
                existing_subject = self.db_session.query(Subject).filter_by(id=subject_id).first()

                # If the subject doesn't exist, create a new one
                if not existing_subject:
                    new_subject = Subject(
                        id=subject_id,
                        subject_type=subject_type,
                        center=center,
                    )
                    self.db_session.add(new_subject)

        # Commit changes to the database
        self.db_session.commit()

    def get_or_create_center(self, center_id: int, center_name: str) -> Center:
        """Get or create a center in the database:
            - If the center doesn't exist, create a new one and return it.
            - If the center exists, return it.

        :param center_id: int, the center id
        :param center_name: str, the center name
        :return: the center
        :rtype: Center
        """
        # Check if the center already exists in the database
        existing_center = self.db_session.query(Center).filter_by(id=center_id).first()

        # If the center doesn't exist, create a new one
        if not existing_center:
            new_center = Center(id=center_id, name=center_name)
            self.db_session.add(new_center)
            self.db_session.commit()
            return new_center

        return existing_center

    def add_mri_volumes(self, data_path: str):
        """Add MRI volumes to the database.

        For each subject in the database, this method will look up for all the
        .nii.gz files in the folder corresponding to the subject, and add a corresponding
        volume to the MRIExam model. If this latter does not exists, it will be created.
        The structure of the data folder is the following:
        - it has two subfolders "Healthy" and "Patient"
        - in each subfolder, there are subfolders for each center, denoted "CXX" where XX is the center id
        - in each center subfolder, there are subfolders for each subject, denoted "XX" where XX is the subject id

        :param data_path:
        :return:
        """
        subjects = self.get_all_subjects()

        # For each subject, look up for the corresponding .nii.gz files
        for subject in subjects:
            # Check if the MRIExam already exists in the database
            mri_exam = self.db_session.query(MRIExam).filter_by(subject=subject).first()

            # If the MRIExam doesn't exist, create a new one
            if not mri_exam:
                mri_exam = MRIExam(subject=subject)
                self.db_session.add(mri_exam)

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
                self.db_session.add(mri_volume)

        # Commit changes to the database
        self.db_session.commit()

    def get_all_subjects(self) -> List[Subject]:
        """Get all the subjects from the database"""
        return self.db_session.query(Subject).all()

    def get_subject(self, subject_id: str) -> Subject:
        """Get a subject from the database.

        :param subject_id: str, the subject id
        :return: the subject
        :rtype: Suject
        """
        subject = self.db_session.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            raise ValueError(f"Subject not found: {subject_id}")

        return subject

    def get_mri_volume(self, subject_id: str, volume_name: str) -> MRIVolume:
        """Get an MRI volume from the database.

        :param subject_id: str, the subject id
        :param volume_name: str, the volume name
        :return: the MRI volume
        :rtype: MRIVolume
        """
        subject = self.db_session.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            raise ValueError(f"Subject not found: {subject_id}")

        mri_exam = self.db_session.query(MRIExam).filter_by(subject=subject).first()
        if not mri_exam:
            raise ValueError(f"MRI exam not found for subject {subject_id}")

        mri_volume = self.db_session.query(MRIVolume).filter_by(name=volume_name,
                                                                exam=mri_exam).first()
        if not mri_volume:
            raise ValueError(f"Volume not found: {volume_name} for MRI Exam {mri_exam.id}")

        return mri_volume

    def export_md_lesions_to_csv(self, csv_file_path: str, quantiles: str = "7_94") -> None:
        """Export all MD lesions (high and low) to a CSV file.

        :param csv_file_path: str, path to the CSV file
        :param quantiles: should be "7_94" or "5_95", which means that we take the 7% and 94% quantiles or the 5% and 95% quantiles
        :return: None
        """
        # Get all the subjects from the database
        subjects = self.get_all_subjects()

        # Create the CSV file
        with open(csv_file_path, mode='w') as csv_file:
            fieldnames = ['subject_id',
                          'subject_type',
                          'center_id',
                          'center_name',
                          'low_MD_lesions_in_mL',
                          'high_MD_lesions_in_mL']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()

            # For each subject, get the volume corresponding to the MD lesions
            for subject in subjects:
                if subject.subject_type == "Healthy Control":
                    continue

                try:
                    # Get the volume corresponding to the MD lesions
                    low_md_lesions_volume = subject.compute_mean_diffusivity_lesions_volume(quantiles, "low")
                    high_md_lesions_volume = subject.compute_mean_diffusivity_lesions_volume(quantiles, "high")
                except ValueError as error:
                    low_md_lesions_volume = error
                    high_md_lesions_volume = error

                # Write the data to the CSV file
                writer.writerow({'subject_id': subject.id,
                                 'subject_type': subject.subject_type,
                                 'center_id': subject.center.id,
                                 'center_name': subject.center.name,
                                 'low_MD_lesions_in_mL': low_md_lesions_volume,
                                 'high_MD_lesions_in_mL': high_md_lesions_volume})
