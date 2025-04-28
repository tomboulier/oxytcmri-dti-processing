from typing import Optional

from oxytcmri.domain.entities.mri import DTIMetric
from oxytcmri.domain.ports.monitoring import Listener, EventDispatcher
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues, StatisticStrategy, \
    StatisticsStrategies
from oxytcmri.interface.importers import (
    Importer)
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseGateway,
    DataBaseRepositoriesRegistry
)


class Controller:
    def __init__(self,
                 persistence_gateway: DataBaseGateway,
                 importers: list[Importer],
                 listeners: Optional[list[Listener]] = None):
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
        self.repository_registry = DataBaseRepositoriesRegistry(persistence_gateway)

        # import data from files
        for importer in importers:
            importer.register_repository(self.repository_registry.list_all_repositories())
            importer.import_data()

    def compute_normative_dti_values(self,
                                     dti_metrics: Optional[list[DTIMetric]] = None,
                                     statistics_strategies: Optional[list[StatisticStrategy]] = None):

        # default values
        dti_metrics = dti_metrics or list(DTIMetric)
        statistics_strategies = statistics_strategies or StatisticsStrategies.all()
        compute_normative_dti_values = ComputeDTINormativeValues(
            repositories_registry=self.repository_registry,
            dispatcher=self.event_dispatcher
        )
        compute_normative_dti_values(
            dti_metrics=dti_metrics,
            statistics_strategies=statistics_strategies,)
