import csv
from sqlalchemy.orm import Session
from oxytcmri.models import Subject, Center


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


class ImportController:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def import_subjects_from_csv(self, csv_file_path: str):
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Extract data from the CSV row
                subject_id = row['subjectId']
                center_name = row['center']
                subject_type = row['subjectType']

                # Look up the center by name or create it if it doesn't exist
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
