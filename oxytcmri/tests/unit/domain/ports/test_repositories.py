import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.subject import SubjectType
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemorySubjectRepository,
    MockCenterRepository,
    MockAtlasRepository
)


class TestSubjectRepository:
    @pytest.fixture
    def test_center(self):
        return Center(id=1, name="Test Center")

    def test_find_subjects_by_center(self, test_center):
        # definitions
        repository = MockInMemorySubjectRepository()

        # execution
        all_subjects = repository.find_subjects_by_center(test_center)
        healthy_volunteers = repository.find_subjects_by_center(
            test_center, subject_type=SubjectType.HEALTHY_VOLUNTEER
        )
        patients = repository.find_subjects_by_center(
            test_center, subject_type=SubjectType.PATIENT
        )

        # assertions
        assert len(all_subjects) == 3
        assert len(healthy_volunteers) == 2
        assert len(patients) == 1


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
        atlases = repository.get_all_atlases()
        assert len(atlases) == 2
