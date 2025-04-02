
from oxytcmri.domain.ports.monitoring import Listener, EventDispatcher
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
from oxytcmri.interface.importers import (
    CSVCenterImporter, CSVAtlasImporter, NiftiFoldersImporter)
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseCenterRepository, DataBaseAtlasRepository, DataBaseSubjectRepository, DataBaseMRIExamRepository,
    DataBaseDTINormativeValuesRepository, DataBaseGateway
)


class Controller:
    def __init__(self,
                 centers_list_path: str,
                 atlases_list_path: str,
                 nifti_files_folder_path: str,
                 persistence_gateway: DataBaseGateway,
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
        overwrite_database_file : bool, optional
            If True, overwrite_database_file the database file if it already exists.
        listeners : list[Listener], optional
            List of listeners to register.
        """
        # event dispatcher
        self.event_dispatcher = EventDispatcher()
        if listeners is not None:
            for listener in listeners:
                self.event_dispatcher.register(listener)

        # create repositories
        self.atlas_repository = DataBaseAtlasRepository(persistence_gateway)
        self.center_repository = DataBaseCenterRepository(persistence_gateway)
        self.subjects_repository = DataBaseSubjectRepository(persistence_gateway)
        self.mri_exams_repository = DataBaseMRIExamRepository(persistence_gateway)
        self.normative_values_repository = DataBaseDTINormativeValuesRepository(persistence_gateway)

        # create importers
        center_importer = CSVCenterImporter(centers_list_path, self.center_repository)
        atlas_importer = CSVAtlasImporter(atlases_list_path, self.atlas_repository)
        nifti_folder_importer = NiftiFoldersImporter(
            base_path=nifti_files_folder_path,
            atlas_repository=self.atlas_repository,
            subject_repository=self.subjects_repository,
            mri_exam_repository=self.mri_exams_repository
        )

        # import data
        center_importer.import_data()
        atlas_importer.import_data()
        nifti_folder_importer.import_data()

    def compute_normative_dti_values(self):

        compute_normative_dti_values = ComputeDTINormativeValues(
            atlas_repository=self.atlas_repository,
            normative_values_repository=self.normative_values_repository,
            centers_repository=self.center_repository,
            subjects_repository=self.subjects_repository,
            mri_repository=self.mri_exams_repository,
            dispatcher=self.event_dispatcher
        )
        compute_normative_dti_values()
