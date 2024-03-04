"""
Controllers for the OxyTCMRI project.
"""
import csv
import logging
import os
from typing import List
from urllib.parse import urlparse

from sqlalchemy import create_engine, exists
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume, Base
from oxytcmri.data_import import DataImporter
from oxytcmri.utils import get_subject_type_from_initials


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

    def commit_changes(self) -> None:
        """Commit changes to the database, after some operations (such as adding objects).

        Returns
        -------
        None
        """
        session = self.database_session
        try:
            session.commit()
        except SQLAlchemyError as error:
            session.rollback()
            logging.error(f"Error while committing changes to database: {error}")
            raise error

    def import_data(self, settings) -> None:
        """Import data from various sources into the database.

        Parameters
        ----------
        settings : Dynaconf
            The settings, containing filepaths to different sources.

        Returns
        -------
        None
        """
        DataImporter(settings).import_data(self)

    def add_object(self, obj):
        """
        Add an object to the database and commit the changes.

        This method adds a given object to the current database session and attempts to commit the changes. If an exception occurs during the commit, the error is logged and the exception is re-raised.

        Parameters
        ----------
        obj : DeclarativeBase
            An instance of a SQLAlchemy model to be added to the database.

        Raises
        ------
        Exception
            Re-raises any exception that occurs during the addition or commit to allow for custom error handling by the caller.

        Examples
        --------
        >>> db_controller = DatabaseController(settings)
        >>> new_subject = Subject(id='123', subject_type='Example', center_id=1)
        >>> db_controller.add_object(new_subject)
        """
        try:
            self.database_session.add(obj)
            self.commit_changes()
        except Exception as error:
            logging.error(f"Error while adding object{obj}: {error}")
            raise error

    def add_objects_list(self, objects_list) -> None:
        """Add a list of objects to the database.

        It allows to commit changes less often than commiting each time we add an object.

        Parameters
        ----------
        objects_list
            a list of objects

        Returns
        -------
        None
        """
        try:
            for obj in objects_list:
                self.database_session.add(obj)
            self.commit_changes()
        except Exception as error:
            logging.error(f"Error while adding object{obj}: {error}")
            raise error

    def object_exists(self, model, **kwargs):
        """
        Check if an object of a given model exists in the database based on provided criteria.

        This method queries the database to check for the existence of an object
        matching the criteria specified by keyword arguments.

        Parameters
        ----------
        model : DeclarativeMeta
            The SQLAlchemy model class to query.
        **kwargs : dict
            Keyword arguments specifying the filtering criteria. These should
            correspond to the attributes of the model.

        Returns
        -------
        bool
            True if at least one object matching the criteria exists, False otherwise.

        Raises
        ------
        Exception
            Propagates exceptions from the underlying database query, typically
            if there's an issue with database connectivity or the query itself.

        Examples
        --------
        >>> exists = object_exists(Subject, id='01_01V_MR_170615')
        >>> print(exists)
        True or False based on the database content
        """
        try:
            result = self.database_session.query(model).filter_by(**kwargs).first()
        except Exception as e:
            raise e
        return result is not None

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

    def get_mri_exam(self, subject: Subject) -> MRIExam:
        """Get the MRIExam associated with a patient.

        Parameters
        ----------
        subject : Subject
            The subject.

        Returns
        -------
        MRIExam
            The MRIExam associated with the subject.
        """
        try:
            result = self.database_session.query(MRIExam).filter_by(subject=subject).first()
        except Exception as e:
            raise e
        return result

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
