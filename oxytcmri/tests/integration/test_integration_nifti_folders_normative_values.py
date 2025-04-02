"""
Integration tests suite for the MRIExam repository "NiftiFoldersMRIExamRepository",
together with the use case "ComputeDTINormativeValues".
"""
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.ports.repositories import SubjectRepository, AtlasRepository, CenterRepository
from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.interface.repositories.database_repositories import DataBaseDTINormativeValuesRepository
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import (
    ComputeDTINormativeValues,
    StatisticsStrategies,
    StatisticStrategy,
    NormativeValueRepository
)
from oxytcmri.tests.unit.domain.mocks import test_center, MockAtlasRepository, MockInMemoryNormativeValuesRepository
from oxytcmri.tests.fixtures import path_to_test_data_folder


class TestComputeDTINormativeValuesWithNiftiFoldersMRIExamRepository:
    @pytest.fixture
    def folder_base_path(self) -> str:
        return str(path_to_test_data_folder() / "NiftiFoldersMRIExamRepository")

    @pytest.fixture()
    def mock_atlas_repository(self) -> AtlasRepository:
        """
        Mock implementation of the AtlasRepository interface.
        This mock repository does not perform any actual data retrieval.
        It is used for testing purposes only.
        """
        return MockAtlasRepository()

    @pytest.fixture()
    def nifti_folders_instance(self,
                               folder_base_path,
                               mock_atlas_repository: AtlasRepository
                               ) -> NiftiFoldersMRIExamRepository:
        return NiftiFoldersMRIExamRepository(folder_base_path,
                                             mock_atlas_repository)

    @pytest.fixture()
    def mock_subject_repository(self) -> SubjectRepository:
        """
        Mock implementation of the SubjectRepository interface.
        This mock repository does not perform any actual data retrieval.
        It is used for testing purposes only.
        """

        class MockSubjectRepository(SubjectRepository):
            def save(self, subject: Subject) -> None:
                pass

            def find_by_id(self, subject_id) -> Optional[Subject]:
                pass

            def __init__(self):
                subjects_id_list = [
                    "01-01-V",
                    "01-03-V",
                    "02-01-V",
                    "02-02-V",
                    "02-03-V",
                    "02-04-V",
                    "03-01-V",
                    "03-02-V",
                    "03-03-V",
                ]
                self.subjects = {}
                for subject_id in subjects_id_list:
                    self.subjects[subject_id] = Subject.from_string_id(subject_id)

            def find_subjects_by_center(self, center, subject_type=None):
                # Mock implementation
                result = []
                if subject_type is None:
                    result = [subject for subject in self.subjects.values()
                              if subject.center_id == center.id]
                else:
                    result = [subject for subject in self.subjects.values()
                              if subject.center_id == center.id and subject.subject_type == subject_type]

                if not result:
                    # If no subjects are found, raise an exception
                    raise LookupError(
                        f"Subjects for center {center} and subject type {subject_type} not found."
                    )
                return result

        return MockSubjectRepository()

    @pytest.fixture()
    def mock_center_repository(self):
        """
        Mock implementation of the CenterRepository interface.
        This mock repository does not perform any actual data retrieval.
        It is used for testing purposes only.
        """

        class MockCenterRepository(CenterRepository):
            def save_centers(self, centers: List[Center]) -> None:
                pass

            def get_all_centers(self) -> List[Center]:
                # Mock implementation
                return [
                    Center(id=1, name="Center 1"),
                    Center(id=2, name="Center 2"),
                    Center(id=3, name="Center 3"),
                ]

        return MockCenterRepository()

    @staticmethod
    def compute_normative_values(
            nifti_folders_instance,
            mock_subject_repository,
            mock_center_repository,
            mock_atlas_repository,
            normative_values_repository: NormativeValueRepository
    ) -> ComputeDTINormativeValues:
        """
        Fixture to create an instance of the ComputeDTINormativeValues use case
        with mock repositories.
        """
        return ComputeDTINormativeValues(
            mri_repository=nifti_folders_instance,
            subjects_repository=mock_subject_repository,
            centers_repository=mock_center_repository,
            atlas_repository=mock_atlas_repository,
            normative_values_repository=normative_values_repository
        )

    @pytest.fixture()
    def use_case_with_mock_in_memory_normative_value_repository(
            self,
            nifti_folders_instance,
            mock_subject_repository,
            mock_center_repository,
            mock_atlas_repository
    ) -> ComputeDTINormativeValues:
        return self.compute_normative_values(
            nifti_folders_instance,
            mock_subject_repository,
            mock_center_repository,
            mock_atlas_repository,
            MockInMemoryNormativeValuesRepository()
        )

    @pytest.mark.parametrize(
        "atlas_id, subject_id, dti_metric, statistics_strategy, atlas_label, expected_value",
        [
            (2, "01-01-V", DTIMetric.MD, StatisticsStrategies.MEAN, 29, 101.6145),
            (2, "01-01-V", DTIMetric.MD, StatisticsStrategies.STD_DEV, 29, 25.00),
            (4, "01-01-V", DTIMetric.MD, StatisticsStrategies.MEAN, 59, 104.4757),
            (2, "01-03-V", DTIMetric.MD, StatisticsStrategies.MEAN, 62, 115.0622),
        ]
    )
    def test_compute_statistics_parameterized(
            self,
            use_case_with_mock_in_memory_normative_value_repository,
            mock_atlas_repository,
            atlas_id,
            subject_id,
            dti_metric,
            statistics_strategy,
            atlas_label,
            expected_value
    ):
        """
        Parametrized test for computing statistics using different parameters.
        This test checks if the computed statistics match the expected values
        for various combinations of atlas ID, subject ID, DTI metric, strategy index,
        atlas label, and expected value.
        The expected values were obtained using ITK-SNAP.

        Parameters
        ----------
        use_case_with_mock_in_memory_normative_value_repository : ComputeDTINormativeValues
            The instance of the ComputeDTINormativeValues use case (provided by pytest fixture)
        mock_atlas_repository : AtlasRepository
            The mock implementation of the AtlasRepository interface (provided by pytest fixture)
        atlas_id : int
            The ID of the atlas
        subject_id : str
            The ID of the subject
        dti_metric : DTIMetric
            The type of DTI metric
        statistics_strategy : StatisticStrategy
            The strategy for computing the statistic (MEAN, STD_DEV, etc.)
        atlas_label : int
            The specific label within the atlas
        expected_value : float
        """
        atlas = mock_atlas_repository.get_atlas_by_id(atlas_id)

        computed_value = use_case_with_mock_in_memory_normative_value_repository.compute_statistics(
            subject=Subject(
                id=subject_id,
                subject_type=SubjectType.HEALTHY_VOLUNTEER,
                center_id=1
            ),
            statistic_strategy=statistics_strategy,
            dti_metric=dti_metric,
            atlas=atlas,
            atlas_label=atlas_label,
        )

        assert computed_value == pytest.approx(expected_value, abs=1e-2)

    def test_use_case_compute_normative_values_center_atlas(self,
                                                            use_case_with_mock_in_memory_normative_value_repository,
                                                            mock_atlas_repository,
                                                            test_center):
        """
        Test if the ComputeDTINormativeValues use case correctly computes
        the normative values for a given center and atlas.
        """
        atlas_2 = mock_atlas_repository.get_atlas_by_id(2)

        # Mock the compute_statistics method to return a fixed value
        def mock_compute_statistics(subject: Subject,
                                    statistic_strategy: StatisticStrategy,
                                    dti_metric: DTIMetric,
                                    atlas: Atlas,
                                    atlas_label: int) -> float:
            return 100.0

        use_case_with_mock_in_memory_normative_value_repository.compute_statistics = mock_compute_statistics

        use_case_with_mock_in_memory_normative_value_repository.compute_center_normative_values_by_atlas(
            center=test_center,
            dti_metric=DTIMetric.MD,
            atlas=atlas_2,
        )
        normative_values = use_case_with_mock_in_memory_normative_value_repository.normative_values_repository.get_all()

        # Check if the returned normative values are correct
        healthy_volunteer_subjects_count = len(
            use_case_with_mock_in_memory_normative_value_repository.subjects_repository.find_subjects_by_center(
                center=test_center,
                subject_type=SubjectType.HEALTHY_VOLUNTEER
            )
        )
        atlas_labels_count = len(atlas_2.labels)
        statistics_strategies_count = len(StatisticsStrategies.all())
        assert len(normative_values) == 30

        # Check if the normative values have the expected attributes
        for normative_value in normative_values:
            assert normative_value.center == test_center
            assert normative_value.dti_metric == DTIMetric.MD
            assert normative_value.atlas == atlas_2
            assert normative_value.atlas_label in atlas_2.labels

    @staticmethod
    def dummy_compute_statistics(
            subject,
            statistic_strategy,
            dti_metric,
            atlas,
            atlas_label):
        return 100.0

    def test_compute_all_normative_values(self,
                                          use_case_with_mock_in_memory_normative_value_repository):
        """
        Test if the ComputeDTINormativeValues use case correctly computes
        the normative values for all subjects in the repository.
        """
        use_case_with_mock_in_memory_normative_value_repository.compute_statistics = self.dummy_compute_statistics
        use_case_with_mock_in_memory_normative_value_repository()

        # Check if the returned normative values are correct
        healthy_volunteer_subjects_count = 9
        total_atlas_labels_count = 8
        statistics_strategies_count = len(StatisticsStrategies.all())
        dti_metric_count = len(DTIMetric)
        expected_normative_values_count = (
                healthy_volunteer_subjects_count * total_atlas_labels_count *
                statistics_strategies_count * dti_metric_count
        )

        # Compare the expected and actual counts
        actual_normative_values_count = len(
            use_case_with_mock_in_memory_normative_value_repository.normative_values_repository.get_all())
        assert actual_normative_values_count == expected_normative_values_count

    @pytest.fixture()
    def temp_db_path(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture()
    def database_normative_values_repository(self, temp_db_path):
        gateway = SQLModelSQLiteDataGateway(temp_db_path)
        return DataBaseDTINormativeValuesRepository(gateway)

    @pytest.fixture()
    def use_case_with_database_normative_values_repository(
            self,
            nifti_folders_instance,
            mock_subject_repository,
            mock_center_repository,
            mock_atlas_repository,
            database_normative_values_repository
    ) -> ComputeDTINormativeValues:
        return self.compute_normative_values(
            nifti_folders_instance,
            mock_subject_repository,
            mock_center_repository,
            mock_atlas_repository,
            database_normative_values_repository
        )

    def test_compute_all_normative_values_with_database(
            self,
            use_case_with_database_normative_values_repository,
            temp_db_path):
        use_case_with_database_normative_values_repository.compute_statistics = self.dummy_compute_statistics
        use_case_with_database_normative_values_repository()

        # Verify correct number of centers imported by
        # making a SQL request to the SQLite database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check number of normative values in the persistent database
        cursor.execute("SELECT COUNT(*) FROM DTI_normative_values")
        count = cursor.fetchone()[0]
        assert count > 0
