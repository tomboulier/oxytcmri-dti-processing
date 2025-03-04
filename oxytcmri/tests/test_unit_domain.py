from oxytcmri.domain.entities.subject import Subject, SubjectType


class TestSubject:
    def test_create_subject(self):
        new_subject = Subject.from_string_id("01-71-P")
        assert new_subject.center_id == 1
        assert new_subject.subject_type == SubjectType.PATIENT
