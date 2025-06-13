import pytest

from oxytcmri.domain.use_cases.compute_lesions_volumes import ComputeBrainLesionsVolumes
from oxytcmri.tests.unit.domain.mocks import MockInMemoryRepositoriesRegistry


class TestComputeBrainLesionsVolumes:
    @pytest.fixture
    def compute_brain_lesions_volumes(self) -> ComputeBrainLesionsVolumes:
        repositories_registry = MockInMemoryRepositoriesRegistry()
        return ComputeBrainLesionsVolumes(repositories_registry=repositories_registry)

    def test_execute_use_case(self,
                              compute_brain_lesions_volumes: ComputeBrainLesionsVolumes):
        """
        Test if the ComputeBrainLesionsVolumes use case workflow is executed
        without errors. It does not check the correctness of the results.
        """
        compute_brain_lesions_volumes()
