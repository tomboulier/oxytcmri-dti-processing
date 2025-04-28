import unittest.mock as mock

from oxytcmri.domain.entities.mri import DTIMetric
from oxytcmri.domain.use_cases.compute_dti_normative_values import StatisticsStrategies
from oxytcmri.interface.controllers import Controller
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
            # Configure a mock instance
            mock_instance = mock_use_case.return_value

            # Call the method we want to test
            dti_metrics = [DTIMetric.FA]
            statistics_strategies = StatisticsStrategies.all()[:2]  # Just take the first two for the test
            controller.compute_normative_dti_values(
                dti_metrics=dti_metrics,
                statistics_strategies=statistics_strategies
            )

            # Verify ComputeDTINormativeValues was called once
            mock_use_case.assert_called_once()
