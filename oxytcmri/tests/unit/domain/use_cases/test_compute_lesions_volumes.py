import pytest

from oxytcmri.domain.entities.mri import AbnormalValueType
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
        without errors. Then, it will check if the brain lesions volumes are
        correctly computed and stored in the repository.
        """
        compute_brain_lesions_volumes()

        # Check if the brain lesions volumes are computed and stored
        brain_lesions_volumes = compute_brain_lesions_volumes.brain_lesions_volume_repository.list_all()

        # Assert that the expected number of brain lesions volumes are computed
        # In this case, we expect 8 brain lesions volumes to be computed:
        # 1 patient * 4 DTI metrics * 2 abnormal value types (HIGH, LOW) * 1 region of interest (whole brain)
        assert len(brain_lesions_volumes) == 8, "Expected 8 brain lesions volumes to be computed and stored."

        # Assert that the volumes are correctly computed
        # By definition in mocks, the volumes should be 8.0 mL for low and 0.0 mL for high abnormal values
        for volume in brain_lesions_volumes:
            if volume.abnormal_value_type == AbnormalValueType.LOW:
                assert volume.value_ml == 8.0, "Expected volume for LOW abnormal values to be 8.0 mL."
            elif volume.abnormal_value_type == AbnormalValueType.HIGH:
                assert volume.value_ml == 0.0, "Expected volume for HIGH abnormal values to be 0.0 mL."
