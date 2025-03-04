from oxytcmri.domain.entities.subject import Subject, SubjectType
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


# Use cases
class TestComputeDTIReferenceValues:
    def test_execute_use_case(self):
        use_case = ComputeDTIReferenceValues()
        use_case.execute()
