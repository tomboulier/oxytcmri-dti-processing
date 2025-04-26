import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam
from oxytcmri.domain.entities.subject import SubjectType
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemorySubjectRepository,
    MockCenterRepository,
    MockAtlasRepository,
    MockInMemoryMRIExamRepository
)


class TestSubjectRepository:
    @pytest.fixture
    def test_center(self):
        return Center(id=1, name="Test Center")

    def test_find_subjects_by_center(self, test_center):
        # definitions
        repository = MockInMemorySubjectRepository()

        # execution
        all_subjects_in_test_center = repository.find_subjects_by_center(test_center)
        healthy_volunteers_in_test_center = repository.find_subjects_by_center(
            test_center, subject_type=SubjectType.HEALTHY_VOLUNTEER
        )
        patients_in_test_center = repository.find_subjects_by_center(
            test_center, subject_type=SubjectType.PATIENT
        )

        # assertions
        assert len(all_subjects_in_test_center) == 2
        assert len(healthy_volunteers_in_test_center) == 1
        assert len(patients_in_test_center) == 1


class TestCenterRepository:
    def test_list_all_centers(self):
        """
        List all centers in the repository, and test the count.
        """
        repository = MockCenterRepository()
        centers = repository.get_all_centers()
        assert len(centers) == 3


class TestAtlasRepository:
    def test_list_all_atlases(self):
        """
        List all atlases in the repository, and test the count.
        """
        repository = MockAtlasRepository()
        atlases = repository.list_all()
        assert len(atlases) == 2


class TestMRIExamRepository:
    def test_get_exam_for_subject(self):
        mri_repo = MockInMemoryMRIExamRepository()
        subject_id = "01-02-P"
        mri_repo.save(
            MRIExam(
                id=f"exam_{subject_id}",
                subject_id=subject_id,
                data=[]
            )
        )
        mri_exam = mri_repo.get_exam_for_subject(subject_id)
        assert mri_exam.subject_id == subject_id
