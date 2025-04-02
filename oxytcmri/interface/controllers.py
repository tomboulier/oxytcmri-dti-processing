from pathlib import Path

from oxytcmri.domain.ports.monitoring import Listener, EventDispatcher
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.interface.importers import (
    CSVCenterImporter, CSVAtlasImporter, NiftiFoldersImporter)
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseCenterRepository, DataBaseAtlasRepository, DataBaseSubjectRepository, DataBaseMRIExamRepository,
    DataBaseDTINormativeValuesRepository
)


class Controller:
    def __init__(self,
                 centers_list_path: str,
                 atlases_list_path: str,
                 nifti_files_folder_path: str,
                 sqlite_database_path: str,
                 overwrite: bool = False,
                 listeners: list[Listener] = None):
        """
        Initialize the controller.

        Parameters:
            listeners:
        -----------
        centers_list_path : str
            Path to the CSV file containing center data.
        atlases_list_path : str
            Path to the CSV file containing atlas data.
        nifti_files_folder_path : str
            Path to the folder containing NIfTI files.
        sqlite_database_path : str
            URL of the database.
        overwrite : bool, optional
            If True, overwrite the database file if it already exists.
        listeners : list[Listener], optional
            List of listeners to register.
        """
        # event dispatcher
        self.event_dispatcher = EventDispatcher()
        if listeners is not None:
            for listener in listeners:
                self.event_dispatcher.register(listener)

        # create database gateway for persistent storage
        if Path(sqlite_database_path).exists():
            if overwrite:
                Path(sqlite_database_path).unlink()
            else:
                raise FileExistsError(f"Database file already exists: '{sqlite_database_path}'.")
        else:
            # Create the database file
            Path(sqlite_database_path).touch()
        database_gateway = SQLModelSQLiteDataGateway(sqlite_database_path)

        # create repositories
        atlas_repository = DataBaseAtlasRepository(database_gateway)
        center_repository = DataBaseCenterRepository(database_gateway)
        subjects_repository = DataBaseSubjectRepository(database_gateway)
        mri_exams_repository = DataBaseMRIExamRepository(database_gateway)
        normative_values_repository = DataBaseDTINormativeValuesRepository(database_gateway)

        # create importers
        center_importer = CSVCenterImporter(centers_list_path, center_repository)
        atlas_importer = CSVAtlasImporter(atlases_list_path, atlas_repository)
        nifti_folder_importer = NiftiFoldersImporter(
            base_path=nifti_files_folder_path,
            atlas_repository=atlas_repository,
            subject_repository=subjects_repository,
            mri_exam_repository=mri_exams_repository
        )
        self.atlases_repository = atlas_repository
        self.centers_repository = center_repository
        self.subjects_repository = subjects_repository
        self.mri_exams_repository = mri_exams_repository
        self.normative_values_repository = normative_values_repository

        # import data
        center_importer.import_data()
        atlas_importer.import_data()
        nifti_folder_importer.import_data()

    def compute_normative_dti_values(self):

        compute_normative_dti_values = ComputeDTINormativeValues(
            atlas_repository=self.atlases_repository,
            normative_values_repository=self.normative_values_repository,
            centers_repository=self.centers_repository,
            subjects_repository=self.subjects_repository,
            mri_repository=self.mri_exams_repository,
            dispatcher=self.event_dispatcher
        )
        compute_normative_dti_values()
