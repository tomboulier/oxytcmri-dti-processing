# oxytcmri/tests/unit/interface/repositories/test_database_center_repository.py

import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas, MRIExam
from oxytcmri.domain.entities.subject import SubjectId, Subject
from oxytcmri.domain.ports.repositories import EntityIdNotFoundException
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValue, StatisticsStrategies
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseCenterRepository, DataBaseDTINormativeValuesRepository, DataBaseMRIExamRepository,
    DataBaseSubjectRepository)
from oxytcmri.tests.unit.domain.mocks import MockInMemoryDataGateway


class TestDataBaseCenterRepository:
    @pytest.fixture
    def repository(self):
        """Creates a repository instance with the mock gateway."""
        return DataBaseCenterRepository(MockInMemoryDataGateway())

    def test_save_centers(self, repository):
        """Tests that the repository can save a center via the gateway."""
        # Arrange
        centers = [
            Center(id=1, name="Test Center"),
            Center(id=2, name="Test Center 2")
        ]

        # Act
        repository.save_list(centers)

        # Assert
        assert len(repository.list_all()) == 2

    def test_raise_entity_not_found_exception(self, repository):
        """Tests that the repository raises an exception when trying to get a non-existent entity."""
        # Arrange
        with pytest.raises(EntityIdNotFoundException):
            repository.get_by_id(1)

    def test_delete_center(self, repository):
        """Tests that the repository can delete a center."""
        # Arrange
        centers = [
            Center(id=1, name="Test Center"),
            Center(id=2, name="Test Center 2")
        ]
        repository.save_list(centers)

        # Act
        repository.delete(centers[0])

        # Assert
        assert len(repository.list_all()) == 1


class TestDataBaseMRIExamRepository:
    @pytest.fixture
    def repository(self) -> DataBaseMRIExamRepository:
        """Creates a repository instance with the mock gateway."""
        return DataBaseMRIExamRepository(MockInMemoryDataGateway())

    def test_get_exam_for_subject(self, repository):
        """Tests the method `get_exam_for_subject`"""
        # Arrange
        mri_exam = MRIExam.from_string_exam_id("01_01v_mr_170913")
        repository.save(mri_exam)

        # Act
        first_exam = repository.get_exam_for_subject(SubjectId("01-01-V"))

        # Assert
        assert first_exam == mri_exam


class TestDataBaseDTINormativeValuesRepository:
    @pytest.fixture
    def repository(self):
        """Creates a repository instance with the mock gateway."""

    def test_get_all_normative_values(self):
        repository = DataBaseDTINormativeValuesRepository(MockInMemoryDataGateway())
        # Arrange
        test_center = Center(id=1, name="Test Center")
        test_atlas_label = 1
        test_atlas = Atlas(id=1, labels=[test_atlas_label])
        test_normative_value = NormativeValue(
            center=test_center,
            dti_metric=DTIMetric.MD,
            atlas=test_atlas,
            atlas_label=1,
            statistic_strategy=StatisticsStrategies.MEAN_STRATEGY,
            value=100.0
        )
        repository.save(test_normative_value)

        assert repository.exists(center=test_center,
                                 atlas_label=test_atlas_label,
                                 atlas=test_atlas,
                                 dti_metric=DTIMetric.MD,
                                 statistic_strategy=StatisticsStrategies.MEAN_STRATEGY)


class TestDataBaseSubjectRepository:
    @pytest.fixture
    def repository(self) -> DataBaseSubjectRepository:
        """Creates a repository instance with the mock gateway."""
        return DataBaseSubjectRepository(MockInMemoryDataGateway())

    def test_find_subjects_by_center(self, repository: DataBaseSubjectRepository):
        """
        Tests the method `find_subjects_by_center` in the DataBaseSubjectRepository.
        """
        # Arrange
        center_1 = Center(id=1, name="Test Center")
        subjects = [
            Subject.from_string_id("01-01-V"),
            Subject.from_string_id("01-02-P"),
            Subject.from_string_id("02-02-V"),
        ]
        repository.save_list(subjects)

        # Act
        retrieved_subjects = repository.find_subjects_by_center(center_1)

        # Assert
        assert retrieved_subjects == subjects[0:2]  # Only the first two subjects belong to center_1
