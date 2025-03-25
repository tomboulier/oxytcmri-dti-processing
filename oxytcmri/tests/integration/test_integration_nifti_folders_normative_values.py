"""
Integration tests suite for the MRIExam repository "NiftiFoldersMRIExamRepository",
together with the use case "ComputeDTINormativeValues".
"""
from pathlib import Path
import pytest

from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.ports.repositories import SubjectRepository, AtlasRepository
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues, StatisticsStrategies
from oxytcmri.tests.unit.domain.mocks import test_center


class TestComputeDTINormativeValuesWithNiftiFoldersMRIExamRepository:
    @pytest.fixture
    def folder_base_path(self) -> str:
        test_data_folder = Path(__file__).resolve().parents[1] / 'test-data'
        return str(test_data_folder / "NiftiFoldersMRIExamRepository")

    @pytest.fixture()
    def mock_atlas_repository(self) -> AtlasRepository:
        """
        Mock implementation of the AtlasRepository interface.
        This mock repository does not perform any actual data retrieval.
        It is used for testing purposes only.
        """

        class MockAtlasRepository(AtlasRepository):
            def get_atlas_by_id(self, atlas_id: int) -> Atlas:
                # Mock implementation
                if atlas_id == 2:
                    return Atlas(id=2, labels=[29, 33, 62])
                if atlas_id == 4:
                    return Atlas(id=4, labels=[29, 33, 59, 60, 62])

                raise ValueError(f"Atlas with ID {atlas_id} not found.")

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
            def find_subjects_by_center(self, center, subject_type=None):
                # Mock implementation
                if center.id == 1 and subject_type == SubjectType.HEALTHY_VOLUNTEER:
                    return [
                        Subject(id="01-01-V",
                                subject_type=SubjectType.HEALTHY_VOLUNTEER,
                                center_id=1),
                        Subject(id="01-03-V",
                                subject_type=SubjectType.HEALTHY_VOLUNTEER,
                                center_id=1),
                    ]

                raise LookupError(
                    f"Subjects for center {center} and subject type {subject_type} not found."
                )

        return MockSubjectRepository()

    @pytest.fixture()
    def use_case_instance(self, nifti_folders_instance, mock_subject_repository):
        return ComputeDTINormativeValues(
            mri_repository=nifti_folders_instance,
            subjects_repository=mock_subject_repository,
        )

    def test_compute_mean_of_MD_map_for_atlas_2(self,
                                                use_case_instance,
                                                mock_atlas_repository):
        """
        Test if the ComputeDTINormativeValues use case correctly computes
        the mean of the MD map for atlas 2, label 29.
        """
        mean_statistic_strategy = StatisticsStrategies.all()[0]
        atlas = mock_atlas_repository.get_atlas_by_id(2)
        mean_value = use_case_instance.compute_statistics(
            subject=Subject(id="01-01-V",
                            subject_type=SubjectType.HEALTHY_VOLUNTEER,
                            center_id=1),
            statistic_strategy=mean_statistic_strategy,
            dti_metric=DTIMetric.MD,
            atlas=atlas,
            atlas_label=29,
        )

        assert mean_value == pytest.approx(101.6145)

    def test_use_case_compute_normative_values_center_atlas(self,
                                                            use_case_instance,
                                                            mock_atlas_repository,
                                                            test_center):
        """
        Test if the ComputeDTINormativeValues use case correctly computes
        the normative values for a given center and atlas.
        """
        atlas = mock_atlas_repository.get_atlas_by_id(2)
        normative_values = use_case_instance.execute(
            center=test_center,
            dti_metric=DTIMetric.MD,
            atlas=atlas,
        )

        assert len(normative_values) == 30

        for normative_value in normative_values:
            assert normative_value.center == test_center
            assert normative_value.dti_metric == DTIMetric.MD
            assert normative_value.atlas == atlas
            assert normative_value.atlas_label in atlas.labels
