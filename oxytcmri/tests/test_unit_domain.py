from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas, MRIExam, MRIData
from oxytcmri.domain.ports.repositories import SubjectRepository, MRIRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
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


class MockInMemoryMRIRepository(MRIRepository):
    def __init__(self):
        # Créer quelques données fictives pour les tests
        from pathlib import Path
        
        # Créer un atlas fictif
        self.atlas_data = MRIData(
            id="atlas1", 
            name="2",  # Correspond à l'ID de l'atlas dans le test
            filepath=Path("/mock/path/to/atlas")
        )
        # Ajouter un attribut (simule l'ID de l'atlas)
        self.atlas_data.atlas_id = 2
        
        # Créer des données DTI fictives
        self.dti_md_data = MRIData(
            id="dti_md", 
            name=DTIMetric.MD.value,
            filepath=Path("/mock/path/to/dti_md")
        )
        
        # Ajouter une méthode apply_mask fictive aux données
        def mock_apply_mask(mask):
            return [0.1, 0.2, 0.3]  # Retourne des valeurs fictives
            
        def mock_create_mask(labels):
            class MockMask:
                pass
            return MockMask()
            
        # Ajouter les méthodes aux données
        self.dti_md_data.get_voxel_data = lambda: type('obj', (object,), {'apply_mask': mock_apply_mask})
        self.atlas_data.get_voxel_data = lambda: type('obj', (object,), {'create_mask': mock_create_mask})

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        # Créer et retourner un examen MRI avec les données fictives
        return MRIExam(
            id=f"exam_{subject_id}", 
            subject_id=subject_id, 
            data=[self.dti_md_data, self.atlas_data]
        )

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
        use_case = ComputeDTINormativeValues(
            subjects_repository=MockInMemorySubjectRepository(center),
            mri_repository=MockInMemoryMRIRepository()
        )
        result = use_case.execute(center, dti_metric, atlas)

        # assertions
        assert result is not None
        assert all(item.center == center for item in result)
        assert all(item.dti_metric == dti_metric for item in result)
        assert all(item.atlas == atlas for item in result)
        assert all(isinstance(item.value, float) for item in result)
