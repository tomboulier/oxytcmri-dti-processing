
from oxytcmri.domain.ports.monitoring import Listener, EventDispatcher
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
from oxytcmri.interface.importers import (
    Importer)
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseCenterRepository, DataBaseAtlasRepository, DataBaseSubjectRepository, DataBaseMRIExamRepository,
    DataBaseDTINormativeValuesRepository, DataBaseGateway
)


class Controller:
    def __init__(self,
                 persistence_gateway: DataBaseGateway,
                 importers: list[Importer],
                 listeners: list[Listener] = None):
        """
        Initialize the controller.

        Parameters:
        -----------
        persistence_gateway: DataBaseGateway
            The persistence gateway for database operations.
        importers: list[Importer]
            List of importers to use for importing data.
        listeners: list[Listener], optional
            List of listeners for event dispatching.
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
        all_repositories = [
            self.atlas_repository,
            self.center_repository,
            self.subjects_repository,
            self.mri_exams_repository,
            self.normative_values_repository
        ]

        # import data
        for importer in importers:
            importer.register_repository(all_repositories)
            importer.import_data()

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
