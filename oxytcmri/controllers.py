"""
Controllers for the OxyTCMRI project.
"""

import os
from pathlib import Path
from typing import List
import warnings
from sqlalchemy.exc import SAWarning

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker

from oxytcmri.data_export import DataExporter
from oxytcmri.logger import get_logger, log_and_raise
from oxytcmri.models import (
    Subject,
    Center,
    MRIExam,
    MRIVolume,
    Base,
    SubjectType,
    MDLesionVolume,
)
from oxytcmri.data_import import DataImporter
from oxytcmri.utils import get_subject_type_from_initials


class DatabaseError(Exception):
    """Exception raised for errors in the database.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class DatabaseController:
    """A class to control the database.

    This class is responsible for managing the database, including creating the database,
    adding objects to the database, and querying the database.

    Attributes
    ----------
    settings : Dynaconf
        The settings.

    db_file_path : Path
        The path to the database file.

    engine : Engine
        The SQLAlchemy engine.

    database_session : Session
        The SQLAlchemy session.

    logger : Logger
        Logger object, used to log messages.
    """

    def __init__(self, settings, overwrite: bool = False):
        """Create a DatabaseController instance.

        Parameters
        ----------
        settings : Dynaconf
            The settings.

        overwrite : bool
            Whether to overwrite_database_file the database file if it already exists. Default is False.
        """
        # get logger
        self.logger = get_logger(settings)

        # Parse the database URL to extract the file path (for SQLite)
        parsed_url = settings.database.url.replace("sqlite:///", "")
        db_file_path = Path(parsed_url)
        self.db_file_path = db_file_path

        # Check if the database file exists
        if db_file_path.exists() and not overwrite:
            self.logger.info(
                f"Database file {db_file_path} exists. Using the existing database."
            )
        else:
            if db_file_path.exists():
                self.logger.info(
                    f"Database file {db_file_path} exists. Overwriting database."
                )
                os.remove(db_file_path)
            self.logger.info(f"Creating database at {db_file_path}.")
            # ensure that the parent directory exists
            db_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.engine = create_engine(settings.database.url)
            Base.metadata.create_all(self.engine)
        except Exception as error:
            self.logger.error(
                f"Error while creating the database engine or tables: {error}"
            )
            raise DatabaseError(
                f"Error while creating the database engine or tables: {error}"
            )

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
            # Capture SAWarnings and log them
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always", SAWarning)
                # Add objects to the session if they are not already in it
                session.add_all(obj for obj in session.new if obj not in session)
                # Commit the changes
                session.commit()
                # Log any SAWarnings that were captured
                for warning in w:
                    self.logger.warning(f"SQLAlchemy warning: {warning.message}")
        except SQLAlchemyError as error:
            session.rollback()
            self.logger.error(f"Error while committing changes to database: {error}")
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
            self.database_session.add(obj) if obj not in self.database_session else None
            self.commit_changes()
            self.logger.info(
                f"{obj} added to the database located in {self.db_file_path}."
            )
        except Exception as error:
            self.logger.error(f"Error while adding object{obj}: {error}")
            raise error

    def add_mean_diffusivity_lesions_volume(
        self, md_lesion_volumes: MDLesionVolume, overwrite_data: bool
    ) -> None:
        """Add a MDLesionVolume object to the database."""
        try:
            # Check if the MD lesion volume already exists
            existing_volume = (
                self.database_session.query(MDLesionVolume)
                .filter_by(
                    subject_id=md_lesion_volumes.subject_id,
                    quantiles=md_lesion_volumes.quantiles,
                    lesion_type=md_lesion_volumes.lesion_type,
                    localisation=md_lesion_volumes.localisation,
                )
                .first()
            )

            if existing_volume:
                if overwrite_data:
                    existing_volume.volume_value_in_mL = (
                        md_lesion_volumes.volume_value_in_mL
                    )
                    self.logger.info(
                        f"{existing_volume} updated to {md_lesion_volumes}."
                    )
                else:
                    self.logger.info(
                        f"{md_lesion_volumes.subject_id} already exists and will not be overwritten."
                    )
                    return
            else:
                self.add_object(md_lesion_volumes)

            self.commit_changes()
        except Exception as error:
            self.logger.error(
                f"Error while adding/updating {md_lesion_volumes}: {error}"
            )
            raise error

    def add_objects_list(self, objects_list) -> None:
        """Add a list of objects to the database.

        It allows to commit changes less often than committing each time we add an object.

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
            self.logger.error(f"Error while adding object{obj}: {error}")
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
        existing_center = (
            self.database_session.query(Center).filter_by(id=center_id).first()
        )

        # If the center doesn't exist, create a new one
        if not existing_center:
            new_center = Center(id=center_id, name=center_name)
            self.database_session.add(new_center)
            self.database_session.commit()
            self.logger.info(f"{new_center} created.")
            return new_center

        return existing_center

    def get_all_subjects(self) -> List[Subject]:
        """Get all the subjects from the database"""
        try:
            return self.get_all_objects(Subject)
        except OperationalError as error:
            log_and_raise(
                self.logger,
                DatabaseError,
                f"An error occurred while fetching all subjects from the database, with the "
                f"following message: '{error.args[0]}'",
            )

    def get_all_objects(self, model):
        """
        Get all objects of a given model from the database.

        This method queries the database to retrieve all objects of a given model.

        Parameters
        ----------
        model : DeclarativeMeta
            The SQLAlchemy model class to query.

        Returns
        -------
        list
            A list of all objects of the given model in the database.

        Raises
        ------
        Exception
            Propagates exceptions from the underlying database query, typically
            if there's an issue with database connectivity or the query itself.

        Examples
        --------
        >>> all_subjects = get_all_objects(Subject)
        >>> print(all_subjects)
        [Subject1, Subject2, ...]
        """
        try:
            result = self.database_session.query(model).all()
        except Exception as e:
            raise e
        return result

    def delete_all_objects(self, model: Base) -> None:
        """Delete all objects of a given model from the database.

        This method deletes all objects of a given model from the database.

        Parameters
        ----------
        model : DeclarativeMeta
            The SQLAlchemy model class to query.

        Returns
        -------
        None

        Raises
        ------
        Exception
            Propagates exceptions from the underlying database query, typically
            if there's an issue with database connectivity or the query itself.

        Examples
        --------
        >>> delete_all_objects(Subject)
        """
        try:
            self.database_session.query(model).delete()
            self.commit_changes()
        except Exception as e:
            raise e

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
            message = f"Subject not found: {subject_id}"
            log_and_raise(self.logger, ValueError, message)

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
            message = f"Subject not found: {subject_id}"
            log_and_raise(self.logger, ValueError, message)

        mri_exam = (
            self.database_session.query(MRIExam).filter_by(subject=subject).first()
        )
        if not mri_exam:
            log_and_raise(
                self.logger, ValueError, f"MRI exam not found for subject {subject_id}"
            )

        mri_volume = (
            self.database_session.query(MRIVolume)
            .filter_by(name=volume_name, exam=mri_exam)
            .first()
        )
        if not mri_volume:
            log_and_raise(
                self.logger,
                ValueError,
                f"Volume not found: {volume_name} for MRI Exam {mri_exam.id}",
            )

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
            result = (
                self.database_session.query(MRIExam).filter_by(subject=subject).first()
            )
        except Exception as e:
            raise e
        return result

    def export_data_to_csv(self, csv_file_path: str) -> None:
        """Export all MD lesions (high and low) to a CSV file.

        Parameters
        ----------
        csv_file_path : str
            The path to the CSV file.

        Returns
        -------
        None
        """
        db_exporter = DataExporter(self)
        db_exporter.export_data_to_csv(csv_file_path)

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
        if secondary_id is None:
            message = "trying to find a subject with a None secondary id."
            self.logger.error(message)
            raise DatabaseError(message)
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

    def count_patients(self) -> int:
        """Count the number of subjects with subject_type 'Patient'."""
        return (
            self.database_session.query(Subject)
            .filter_by(subject_type=SubjectType.patient)
            .count()
        )

    def get_distinct_localizations(self) -> list:
        """Get the list of distinct localizations from the md_lesion_volume table."""
        try:
            result = (
                self.database_session.query(MDLesionVolume.localisation)
                .distinct()
                .all()
            )
            return [row[0] for row in result]
        except Exception as e:
            raise e
