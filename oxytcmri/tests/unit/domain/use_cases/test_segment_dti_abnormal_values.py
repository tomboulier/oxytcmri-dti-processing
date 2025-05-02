from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentDTIAbnormalValues
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemoryRepositoriesRegistry
)


class TestSegmentDTIAbnormalValues:
    def test_execute_use_case(self):
        """
        Test if the ComputeDTINormativeValues use case workflow is executed
        without errors. It does not check the correctness of the results.
        """
        # definitions
        compute_normative_values = SegmentDTIAbnormalValues(
            MockInMemoryRepositoriesRegistry(),
        )

        # execution
        compute_normative_values()
