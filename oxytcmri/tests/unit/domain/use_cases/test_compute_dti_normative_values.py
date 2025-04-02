
from oxytcmri.domain.entities.mri import DTIMetric
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemorySubjectRepository,
    MockInMemoryMRIRepository,
    MockCenterRepository,
    MockAtlasRepository,
    MockInMemoryNormativeValuesRepository,
)


class TestComputeDTINormativeValues:
    def test_execute_use_case(self):
        """
        Test if the ComputeDTINormativeValues use case workflow is executed
        without errors. It does not check the correctness of the results.
        """
        # definitions
        dti_metric = DTIMetric.MD
        atlas_repository = MockAtlasRepository()
        centers_repository = MockCenterRepository()
        test_center = centers_repository.get_all_centers()[0]

        # execution
        compute_normative_values = ComputeDTINormativeValues(
            subjects_repository=MockInMemorySubjectRepository(test_center),
            mri_repository=MockInMemoryMRIRepository(atlases=atlas_repository.get_all_atlases()),
            centers_repository=centers_repository,
            atlas_repository=atlas_repository,
            normative_values_repository=MockInMemoryNormativeValuesRepository(),
        )

        compute_without_errors = True
        try:
            compute_normative_values()
        except Exception as e:
            compute_without_errors = False

        # assertions
        assert compute_without_errors
