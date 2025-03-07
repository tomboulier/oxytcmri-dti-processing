from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.use_cases.compute_dti_reference_values import ComputeDTIReferenceValues
import pytest


# Entities
class TestSubject:
    def test_create_subject(self):
        new_subject = Subject.from_string_id("01-01-P")
        assert new_subject.center_id == 1
        assert new_subject.subject_type == SubjectType.PATIENT

        healthy_volunteer = Subject.from_string_id("02-03-V")
        assert healthy_volunteer.subject_type == SubjectType.HEALTHY_VOLUNTEER
        assert healthy_volunteer.center_id == 2

    def test_subject_id_invalid(self):
        with pytest.raises(ValueError):
            Subject.from_string_id("01-01-INVALID")

        with pytest.raises(ValueError):
            Subject.from_string_id("XX-01-P")

        with pytest.raises(ValueError):
            Subject.from_string_id("01-YY-H")

    def test_subject_type(self):
        assert SubjectType.PATIENT == SubjectType.from_string("P")
        assert SubjectType.HEALTHY_VOLUNTEER == SubjectType.from_string("V")
        assert SubjectType.TEST_PATIENT == SubjectType.from_string("T")

        with pytest.raises(ValueError):
            SubjectType.from_string("INVALID")


# Use cases
class TestComputeDTIReferenceValues:
    def test_execute_use_case(self):
        # definitions
        center = Center(id=1, name="Grenoble")
        dti_metric = DTIMetric.MD
        atlas = Atlas(id=2, labels=[1,2,3], name="Neuromorphometrics atlas + GM parcels size ≤5cm3")

        # execution
        use_case = ComputeDTIReferenceValues()
        result = use_case.execute(center, dti_metric, atlas)

        # assertions
        assert result is not None
        assert all(item.center == center for item in result)
        assert all(item.dti_metric == dti_metric for item in result)
        assert all(item.atlas == atlas for item in result)
        assert all(isinstance(item.value, float) for item in result)
