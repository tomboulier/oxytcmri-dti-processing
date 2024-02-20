"""

"""
import csv
from abc import ABC, abstractmethod

from oxytcmri.models import get_center_id_from_subject_id, Subject


class Importer(ABC):
    @abstractmethod
    def import_data(self):
        pass


class SubjectsListImporter(Importer):
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


class DataImporter:
    def __init__(self, settings, database_controller):
        self.database_controller = database_controller
        self.importers_list = [
            SubjectsListImporter(settings, database_controller),
            # Add other importers here...
        ]

    def import_data(self):
        for importer in self.importers_list:
            importer.import_data()
