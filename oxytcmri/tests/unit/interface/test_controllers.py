import unittest.mock as mock

from oxytcmri.domain.entities.mri import DTIMetric, MRIExamId, RegionOfInterest
from oxytcmri.domain.ports.monitoring import Listener
from oxytcmri.domain.use_cases.compute_dti_normative_values import StatisticsStrategies
from oxytcmri.interface.controllers import Controller
from oxytcmri.interface.importers import Importer
from oxytcmri.tests.unit.domain.mocks import MockInMemoryDataGateway


class TestController:
    def test_compute_normative_dti_values(self):
        # Mock dependencies
        mock_persistence_gateway = MockInMemoryDataGateway()

        # Create a controller instance
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[],
        )

        # Mock the ComputeDTINormativeValues class and its __call__ method
        with mock.patch(
                'oxytcmri.interface.controllers.ComputeDTINormativeValues'
        ) as mock_use_case:
            # Call the method we want to test
            dti_metrics = [DTIMetric.FA]
            statistics_strategies = StatisticsStrategies.all()[:2]  # Just take the first two for the test
            controller.compute_normative_dti_values(
                dti_metrics=dti_metrics,
                statistics_strategies=statistics_strategies
            )

            # Verify ComputeDTINormativeValues was called once
            mock_use_case.assert_called_once()

    def test_compute_normative_dti_values_with_defaults(self):
        """Test compute_normative_dti_values with default parameters."""
        mock_persistence_gateway = MockInMemoryDataGateway()
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[],
        )

        with mock.patch(
                'oxytcmri.interface.controllers.ComputeDTINormativeValues'
        ) as mock_use_case:
            # Call the method with no parameters (should use defaults)
            controller.compute_normative_dti_values()

            # Verify ComputeDTINormativeValues was called once
            mock_use_case.assert_called_once()

    def test_init_with_listeners(self):
        """Test Controller initialization with listeners."""
        mock_persistence_gateway = MockInMemoryDataGateway()
        mock_listener = mock.Mock(spec=Listener)
        
        # Create controller with listeners
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[],
            listeners=[mock_listener]
        )
        
        # Verify the listener was registered with the event dispatcher
        assert controller.event_dispatcher is not None

    def test_init_with_importers(self):
        """Test Controller initialization with importers."""
        mock_persistence_gateway = MockInMemoryDataGateway()
        mock_importer = mock.Mock(spec=Importer)
        
        # Create controller with importers
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[mock_importer]
        )
        
        # Verify the importer methods were called
        mock_importer.register_repository.assert_called_once()
        mock_importer.import_data.assert_called_once()

    def test_segment_dti_abnormal_values(self):
        """Test segment_dti_abnormal_values method."""
        mock_persistence_gateway = MockInMemoryDataGateway()
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[],
        )

        with mock.patch(
                'oxytcmri.interface.controllers.SegmentDTIAbnormalValues'
        ) as mock_use_case:
            # Call the method
            dti_metrics = [DTIMetric.MD]
            mri_exam_id = MRIExamId("test_exam")
            controller.segment_dti_abnormal_values(
                dti_metrics=dti_metrics,
                mri_exam_id=mri_exam_id
            )

            # Verify SegmentDTIAbnormalValues was called
            mock_use_case.assert_called_once()
            mock_use_case.return_value.assert_called_once_with(
                dti_metrics=dti_metrics,
                mri_exam_id=mri_exam_id
            )

    def test_segment_dti_abnormal_values_with_defaults(self):
        """Test segment_dti_abnormal_values with default parameters."""
        mock_persistence_gateway = MockInMemoryDataGateway()
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[],
        )

        with mock.patch(
                'oxytcmri.interface.controllers.SegmentDTIAbnormalValues'
        ) as mock_use_case:
            # Call the method with no parameters
            controller.segment_dti_abnormal_values()

            # Verify SegmentDTIAbnormalValues was called
            mock_use_case.assert_called_once()
            mock_use_case.return_value.assert_called_once_with(
                dti_metrics=None,
                mri_exam_id=None
            )

    def test_compute_brain_lesions_volumes(self):
        """Test compute_brain_lesions_volumes method."""
        mock_persistence_gateway = MockInMemoryDataGateway()
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[],
        )

        with mock.patch(
                'oxytcmri.interface.controllers.ComputeBrainLesionsVolumes'
        ) as mock_use_case:
            # Call the method
            dti_metrics = [DTIMetric.FA]
            mri_exam_id = MRIExamId("test_exam")
            regions_of_interest = [mock.Mock(spec=RegionOfInterest)]
            controller.compute_brain_lesions_volumes(
                dti_metrics=dti_metrics,
                mri_exam_id=mri_exam_id,
                regions_of_interest=regions_of_interest
            )

            # Verify ComputeBrainLesionsVolumes was called
            mock_use_case.assert_called_once()
            mock_use_case.return_value.assert_called_once_with(
                dti_metrics=dti_metrics,
                mri_exam_id=mri_exam_id,
                regions_of_interest=regions_of_interest
            )

    def test_compute_brain_lesions_volumes_with_defaults(self):
        """Test compute_brain_lesions_volumes with default parameters."""
        mock_persistence_gateway = MockInMemoryDataGateway()
        controller = Controller(
            persistence_gateway=mock_persistence_gateway,
            importers=[],
        )

        with mock.patch(
                'oxytcmri.interface.controllers.ComputeBrainLesionsVolumes'
        ) as mock_use_case:
            # Call the method with no parameters
            controller.compute_brain_lesions_volumes()

            # Verify ComputeBrainLesionsVolumes was called
            mock_use_case.assert_called_once()
            mock_use_case.return_value.assert_called_once_with(
                dti_metrics=None,
                mri_exam_id=None,
                regions_of_interest=None
            )
