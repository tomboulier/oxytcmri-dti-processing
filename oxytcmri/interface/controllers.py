from typing import Optional

from oxytcmri.domain.entities.mri import DTIMetric, MRIExamId, RegionOfInterest
from oxytcmri.domain.ports.monitoring import Listener, EventDispatcher
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues, StatisticStrategy, \
    StatisticsStrategies
from oxytcmri.domain.use_cases.compute_lesions_volumes import ComputeBrainLesionsVolumes
from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentDTIAbnormalValues
from oxytcmri.interface.importers import (
    Importer)
from oxytcmri.interface.mri.staple_segmenter import C3DSTAPLESegmentationMerger
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

    def segment_dti_abnormal_values(self,
                                    dti_metrics: Optional[list[DTIMetric]] = None,
                                    mri_exam_id: Optional[MRIExamId] = None):
        """
        Segment DTI abnormal values using the C3DSTAPLE algorithm.

        Parameters:
        ----------
        dti_metrics: Optional[list[DTIMetric]]
            List of DTI metrics to segment. If None, all available metrics will be used.
        mri_exam_id: Optional[MRIExamId]
            ID of the MRI exam to segment. If None, all available exams will be used.
        """
        # create the use case
        segment_dti_abnormal_values = SegmentDTIAbnormalValues(
            repositories_registry=self.repository_registry,
            segmentation_merger=C3DSTAPLESegmentationMerger(),
            dispatcher=self.event_dispatcher
        )

        # run the use case
        segment_dti_abnormal_values(
            dti_metrics=dti_metrics,
            mri_exam_id=mri_exam_id
        )

    def compute_brain_lesions_volumes(self,
                                      dti_metrics: Optional[list[DTIMetric]] = None,
                                      mri_exam_id: Optional[MRIExamId] = None,
                                      regions_of_interest: Optional[list[RegionOfInterest]] = None):
        """
        Compute brain lesions volumes for the specified DTI metrics and MRI exam.
        """
        # create the use case
        compute_brain_lesions_volumes = ComputeBrainLesionsVolumes(
            repositories_registry=self.repository_registry,
            dispatcher=self.event_dispatcher
        )

        # run the use case
        compute_brain_lesions_volumes(
            dti_metrics=dti_metrics,
            mri_exam_id=mri_exam_id,
            regions_of_interest=regions_of_interest
        )
