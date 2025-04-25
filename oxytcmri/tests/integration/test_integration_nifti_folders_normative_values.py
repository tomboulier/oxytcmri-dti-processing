"""
Integration tests suite for the MRIExam repository "NiftiFoldersMRIExamRepository",
together with the use case "ComputeDTINormativeValues".
"""
import os
import tempfile
from typing import List

import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, RegionOfInterest
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.repositories import SubjectRepository, AtlasRepository, CenterRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import (
    ComputeDTINormativeValues,
    StatisticsStrategies,
    NormativeValueRepository
)
from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.interface.repositories.database_repositories import DataBaseDTINormativeValuesRepository
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository
from oxytcmri.tests.fixtures import path_to_test_data_folder
from oxytcmri.tests.unit.domain.mocks import (
    MockAtlasRepository,
    MockInMemoryNormativeValuesRepository,
    MockInMemorySubjectRepository
)


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
        return MockInMemorySubjectRepository(
            subject_ids=[
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
        )

    @pytest.fixture()
    def mock_center_repository(self):
        """
        Mock implementation of the CenterRepository interface.
        This mock repository does not perform any actual data retrieval.
        It is used for testing purposes only.
        """

        class MockCenterRepository(CenterRepository):
            def get_center_by_id(self, center_id: int) -> Center:
                # Mock implementation
                raise NotImplementedError

            def save_centers(self, centers: List[Center]) -> None:
                raise NotImplementedError

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
        "subject_id, dti_metric, statistics_strategy, atlas_id, atlas_label, expected_value",
        [
            ("01-01-V", DTIMetric.MD, StatisticsStrategies.MEAN_STRATEGY, 2, 29, 101.6145),
            ("01-01-V", DTIMetric.MD, StatisticsStrategies.STD_DEV_STRATEGY, 2, 29, 25.00),
            ("01-01-V", DTIMetric.MD, StatisticsStrategies.MEAN_STRATEGY, 4, 59, 104.4757),
            ("01-03-V", DTIMetric.MD, StatisticsStrategies.MEAN_STRATEGY, 2, 62, 115.0622),
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
            The strategy for computing the statistic (MEAN_STRATEGY, STD_DEV_STRATEGY, etc.)
        atlas_label : int
            The specific label within the atlas
        expected_value : float
        """
        atlas = mock_atlas_repository.get_atlas_by_id(atlas_id)
        dti_values = use_case_with_mock_in_memory_normative_value_repository.collect_dti_values_for_region(
            dti_metric=dti_metric,
            subjects=[Subject.from_string_id(subject_id)],
            region_of_interest=RegionOfInterest(atlas=atlas, labels=[atlas_label]),
        )
        computed_value = statistics_strategy(dti_values)
        assert computed_value == pytest.approx(expected_value, abs=1e-2)

    def test_use_case_process_center(self,
                                     use_case_with_mock_in_memory_normative_value_repository,
                                     mock_atlas_repository):
        """
        Test if the ComputeDTINormativeValues use case correctly computes
        the normative values for a given center and atlas.

        The expected values were obtained using ITK-SNAP. Since all the MRI exams are
        the same in the test data, this expected value as in test_compute_statistics_parameterized
        with the following parameters:
        - subject_id: 01-01-V
        - dti_metric: MD
        - statistics_strategy: StatisticsStrategies.MEAN_STRATEGY
        - atlas_id: 2
        - atlas_label: 29
        """
        test_center = Center(id=1, name="Test Center")
        atlas_2 = mock_atlas_repository.get_atlas_by_id(2)

        use_case_with_mock_in_memory_normative_value_repository.process_center(
            center=test_center,
            dti_metric=DTIMetric.MD,
            statistic_strategy=StatisticsStrategies.MEAN_STRATEGY,
            region_of_interest=RegionOfInterest(atlas=atlas_2, labels=atlas_2.labels[:1])
        )

        normative_values = use_case_with_mock_in_memory_normative_value_repository.normative_values_repository.get_all()

        assert len(normative_values) == 1
        result = normative_values[0]

        # Check if the normative value have the expected attributes
        assert result.center == test_center
        assert result.dti_metric == DTIMetric.MD
        assert result.atlas == atlas_2
        assert result.atlas_label in atlas_2.labels
        assert result.statistic_strategy == StatisticsStrategies.MEAN_STRATEGY
        assert result.value == pytest.approx(101.6145, abs=1e-4)

    @staticmethod
    def dummy_compute_statistics(
            subject,
            statistic_strategy,
            dti_metric,
            atlas,
            atlas_label):
        return 100.0

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
