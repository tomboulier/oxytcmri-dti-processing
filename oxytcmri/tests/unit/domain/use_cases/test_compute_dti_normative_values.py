
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemoryRepositoriesRegistry
)


class TestComputeDTINormativeValues:
    def test_execute_use_case(self):
        """
        Test if the ComputeDTINormativeValues use case workflow is executed
        without errors. It does not check the correctness of the results.
        """
        # definitions
        compute_normative_values = ComputeDTINormativeValues(
            MockInMemoryRepositoriesRegistry(),
        )

        # execution
        compute_without_errors = True
        try:
            compute_normative_values()
        except Exception:
            compute_without_errors = False

        # assertions
        assert compute_without_errors
