from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.ports.repositories import SubjectRepository
from oxytcmri.domain.use_cases.compute_dti_reference_values import ComputeDTINormativeValues
import pytest
from typing import List, Optional


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


# repositories
@pytest.fixture
def test_center():
    return Center(id=1, name="Test Center")

class MockInMemorySubjectRepository(SubjectRepository):
    def __init__(self, test_center: Center):
        # Subjects from the center
        self.subject1 = Subject(id="S1", subject_type=SubjectType.HEALTHY_VOLUNTEER, center_id=test_center.id)
        self.subject2 = Subject(id="S2", subject_type=SubjectType.PATIENT, center_id=test_center.id)

        # Subject from a different center
        self.subject3 = Subject(id="S3", subject_type=SubjectType.HEALTHY_VOLUNTEER, center_id=2)

        # All subjects
        self.all_subjects = [self.subject1, self.subject2, self.subject3]
        
    def find_subjects_by_center(self, center: Center, subject_type: Optional[SubjectType] = None) -> List[Subject]:
        if subject_type is None:
            return self.all_subjects
        
        return [subject for subject in self.all_subjects if subject.subject_type == subject_type]

class TestSubjectRepository:
    def test_find_subjects_by_center(self, test_center):
        # definitions
        repository = MockInMemorySubjectRepository(test_center)
        
        # execution
        all_subjects = repository.find_subjects_by_center(test_center)
        healthy_volunteers = repository.find_subjects_by_center(test_center, subject_type=SubjectType.HEALTHY_VOLUNTEER)
        patients = repository.find_subjects_by_center(test_center, subject_type=SubjectType.PATIENT)
        
        # assertions
        assert len(all_subjects) == 3
        assert len(healthy_volunteers) == 2
        assert len(patients) == 1

# Use cases
class TestComputeDTIReferenceValues:
    def test_execute_use_case(self):
        # definitions
        center = Center(id=1, name="Grenoble")
        dti_metric = DTIMetric.MD
        atlas = Atlas(id=2, labels=[1,2,3], name="Neuromorphometrics atlas + GM parcels size ≤5cm3")

        # execution
        use_case = ComputeDTINormativeValues()
        result = use_case.execute(center, dti_metric, atlas)

        # assertions
        assert result is not None
        assert all(item.center == center for item in result)
        assert all(item.dti_metric == dti_metric for item in result)
        assert all(item.atlas == atlas for item in result)
        assert all(isinstance(item.value, float) for item in result)
