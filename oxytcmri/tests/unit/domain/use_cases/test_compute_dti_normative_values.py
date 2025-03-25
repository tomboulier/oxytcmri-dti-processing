from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemorySubjectRepository,
    MockInMemoryMRIRepository,
    MockCenterRepository,
    MockAtlasRepository,
    test_center,
)


class TestComputeDTIReferenceValues:
    def test_execute_use_case(self, test_center):
        # definitions
        dti_metric = DTIMetric.MD
        atlas = Atlas(
            id=2,
            labels=[1, 2, 3],
            name="Neuromorphometrics atlas + GM parcels size ≤5cm3",
        )

        # execution
        use_case = ComputeDTINormativeValues(
            subjects_repository=MockInMemorySubjectRepository(test_center),
            mri_repository=MockInMemoryMRIRepository(atlases=[atlas]),
            centers_repository=MockCenterRepository(),
            atlas_repository=MockAtlasRepository(),
        )
        result = use_case.compute_center_normative_values_by_atlas(test_center, dti_metric, atlas)

        # assertions
        assert result is not None
        assert all(item.center == test_center for item in result)
        assert all(item.dti_metric == dti_metric for item in result)
        assert all(item.atlas == atlas for item in result)
        assert all(isinstance(item.value, float) for item in result)
