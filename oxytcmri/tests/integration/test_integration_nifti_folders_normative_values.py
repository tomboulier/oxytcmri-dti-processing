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
            use_case_instance,
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
        use_case_instance : ComputeDTINormativeValues
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

        computed_value = use_case_instance.compute_statistics(
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
