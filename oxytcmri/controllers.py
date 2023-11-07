import csv
from sqlalchemy.orm import Session
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume
from pathlib import Path


def get_center_id_from_subject_id(subject_id: str) -> int:
    """Get the center id from a subject id.

        In our database, the subject id starts with the center id. As an example,
        the subject "08_001" is from the center "08".

    :param subject_id: str, the subject id
    :return: the center id
    :rtype: int
    """
    try:
        return int(subject_id[:2])
    except ValueError:
        raise ValueError(f"Invalid center id in subject id: '{subject_id}'. "
                         f"The subject id should start with the center id.")


def get_subject_folder_path(data_path: str, subject: Subject) -> Path:
    """Get the path to the subject folder.

    """
    if subject.subject_type == "Healthy Control":
        if subject.center.id < 10:
            subject_folder = f"{data_path}/Healthy/C0{subject.center.id}/{subject.id}"
        else:
            subject_folder = f"{data_path}/Healthy/C{subject.center.id}/{subject.id}"
    else:
        if subject.center.id < 10:
            subject_folder = f"{data_path}/Patient/C{subject.center.id}/{subject.id}"
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
        # Get all the subjects from the database
        subjects = self.db_session.query(Subject).all()

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

    def get_subject_details(self, subject_id: str) -> dict:
        """Get the details of a subject from the database.

        :param subject_id: str, the subject id
        :return: the subject details
        :rtype: dict
        """
        subject = self.db_session.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            raise ValueError(f"Subject not found: {subject_id}")

        return {
            "id": subject.id,
            "subject_type": subject.subject_type,
            "center_id": subject.center.id,
            "center_name": subject.center.name,
        }

