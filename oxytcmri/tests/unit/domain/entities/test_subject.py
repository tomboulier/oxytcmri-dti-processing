import pytest

from oxytcmri.domain.entities.subject import Subject, SubjectType


class TestSubject:
    def test_create_subject(self):
        new_subject = Subject.from_string_id("01-01-P")
        assert new_subject.center_id == 1
        assert new_subject.subject_type == SubjectType.PATIENT

        healthy_volunteer = Subject.from_string_id("02-03-V")
        assert healthy_volunteer.subject_type == SubjectType.HEALTHY_VOLUNTEER
        assert healthy_volunteer.center_id == 2

    def test_subject_number_property(self):
        """Test that subject_number property extracts the correct digits."""
        subject = Subject.from_string_id("01-25-P")
        assert subject.id.subject_number == "25"
        
        subject2 = Subject.from_string_id("03-07-V")
        assert subject2.id.subject_number == "07"

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
