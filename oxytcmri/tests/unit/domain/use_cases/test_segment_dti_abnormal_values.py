from typing import List
from unittest.mock import Mock

import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMap, MRIExamId, DTIMetric, Atlas, DTIAbnormalValues, AtlasSegmentation, \
    AbnormalValueType, MRIData
from oxytcmri.domain.ports.repositories import CenterRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue
from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentDTIAbnormalValues, ThresholdStrategy, \
    DTIThresholds, MeanThresholdStrategy, InterQuartileRangeThresholdStrategy, \
    SegmentationMerger
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemoryRepositoriesRegistry, MockVoxelData, MockSegmentationData, MockSyntheticMRIExamRepository
)


class FixedThresholdStrategy(ThresholdStrategy):
    """
    A simple strategy that uses fixed thresholds for all DTI metrics.

    This is a dummy implementation for development and testing.
    In a real application, thresholds would depend on the DTI metric.
    """

    def __init__(self,
                 normative_value_repository: NormativeValueRepository,
                 center_repository: CenterRepository,
                 high_threshold: float = 0.8,
                 low_threshold: float = 0.3):
        """
        Initialize with fixed threshold values.

        Parameters
        ----------
        normative_value_repository : NormativeValueRepository
            The repository to fetch normative values
        center_repository : CenterRepository
            The repository to fetch center information
        high_threshold : float
            Fixed high threshold value to use for all metrics
        low_threshold : float
            Fixed low threshold value to use for all metrics
        """
        super().__init__(normative_value_repository, center_repository)
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    def compute_thresholds(self, dti_image: DTIMap, atlas: Atlas, atlas_label: int) -> DTIThresholds:
        """
        Return fixed thresholds regardless of inputs.

        This is a simplified dummy implementation.

        Parameters
        ----------
        dti_image : DTIMap
            Not used in this implementation
        atlas : Atlas
            Not used in this implementation
        atlas_label : int
            Not used in this implementation

        Returns
        -------
        DTIThresholds
            Fixed threshold values
        """
        return DTIThresholds(high_threshold=self.high_threshold, low_threshold=self.low_threshold)


class DummySegmentationMerger(SegmentationMerger):
    """
    A dummy implementation of the SegmentationMerger interface for testing purposes.
    This class does not perform any actual merging but serves as a placeholder.
    """

    def merge(self, segmentations: List[DTIAbnormalValues]) -> DTIAbnormalValues:
        """
        Dummy merge method that simply returns the first segmentation.

        Parameters
        ----------
        segmentations : List[DTIAbnormalValues]
            List of segmentations to merge

        Returns
        -------
        DTIAbnormalValues
            The first segmentation in the list
        """
        if not segmentations:
            raise ValueError("No segmentations provided for merging.")
        return segmentations[0]


class TestThresholdStrategies:
    """
    Unit tests for the threshold strategies used in the DTI segmentation process.
    """

    @pytest.fixture
    def mock_center_repository(self):
        repo = Mock(spec=CenterRepository)
        center = Mock(spec=Center)
        repo.get_by_mri_exam_id.return_value = center
        return repo, center

    @pytest.fixture
    def mock_normative_value_repository(self):
        repo = Mock(spec=NormativeValueRepository)

        # Configure the mock to return specific values for different statistic strategies
        def mock_get_by_parameters(statistic_strategy, **kwargs):
            mock_normative = Mock(spec=NormativeValue)
            match statistic_strategy.name:
                case "mean":
                    mock_normative.value = 0.6
                case "standard deviation":
                    mock_normative.value = 0.1
                case "quartile 25":
                    mock_normative.value = 0.4
                case "quartile 75":
                    mock_normative.value = 0.8
                case _:
                    raise ValueError(f"Unexpected statistic strategy: {statistic_strategy.name}")
            return mock_normative

        repo.get_by_parameters = Mock(side_effect=mock_get_by_parameters)
        return repo

    @staticmethod
    def strategy_builder(threshold_strategy: ThresholdStrategy,
                         mock_normative_value_repository,
                         mock_center_repository):
        center_repo, _ = mock_center_repository
        # Create the strategy with custom deviation factors
        # for the mean strategy
        if threshold_strategy == MeanThresholdStrategy:
            return MeanThresholdStrategy(
                normative_value_repository=mock_normative_value_repository,
                center_repository=center_repo,
                high_deviation_factor=2.5,
                low_deviation_factor=1.5
            )
        elif threshold_strategy == InterQuartileRangeThresholdStrategy:
            return InterQuartileRangeThresholdStrategy(
                normative_value_repository=mock_normative_value_repository,
                center_repository=center_repo,
                low_deviation_factor=0.2,
                high_deviation_factor=0.3
            )
        else:
            raise ValueError(f"Test not implement for threshold strategy: {threshold_strategy}")

    @pytest.fixture
    def dti_image(self):
        return DTIMap(
            mri_exam_id=MRIExamId("01_02t_mr_150316"),
            voxel_data=MockVoxelData(),
            dti_metric=DTIMetric.FA
        )

    @pytest.fixture
    def atlas(self):
        mock_atlas = Mock(spec=Atlas)
        mock_atlas.name = "test_atlas"
        return mock_atlas

    @pytest.mark.parametrize(
        "threshold_strategy, expected_high_threshold, expected_low_threshold",
        [
            (MeanThresholdStrategy, 0.85, 0.45),  # Mean strategy with custom deviation factors
            (InterQuartileRangeThresholdStrategy, 0.92, 0.32),  # IQR strategy with fixed thresholds
        ])
    def test_compute_thresholds(self,
                                threshold_strategy: ThresholdStrategy,
                                expected_low_threshold: float,
                                expected_high_threshold: float,
                                dti_image,
                                atlas,
                                mock_center_repository,
                                mock_normative_value_repository):
        """Test that thresholds are correctly computed using mean and standard deviation."""
        center_repo, _ = mock_center_repository

        # Create the strategy based on the parameterized input
        threshold_strategy_instance = self.strategy_builder(threshold_strategy,
                                                            mock_normative_value_repository,
                                                            mock_center_repository)

        # Compute thresholds
        atlas_label = 42
        thresholds = threshold_strategy_instance.compute_thresholds(dti_image, atlas, atlas_label)

        # Verify the center was retrieved correctly
        center_repo.get_by_mri_exam_id.assert_called_once_with(dti_image.mri_exam_id)

        # Verify the repository was queried for the mean and standard deviation
        assert mock_normative_value_repository.get_by_parameters.call_count == 2

        # Verify the correct thresholds were computed
        assert isinstance(thresholds, DTIThresholds)
        assert thresholds.high_threshold == pytest.approx(expected_high_threshold, rel=1e-8)
        assert thresholds.low_threshold == pytest.approx(expected_low_threshold, rel=1e-8)


class TestSegmentDTIAbnormalValues:
    @pytest.fixture
    def segment_dti_abnormal_values(self) -> SegmentDTIAbnormalValues:
        repositories_registry = MockInMemoryRepositoriesRegistry()

        # Mock the MRIExamRepository to return synthetic data
        def mock_build_synthetic_data(self, synthetic_mri_exam_id: MRIExamId) -> list[MRIData]:
            atlas_data = [
                AtlasSegmentation(
                    mri_exam_id=synthetic_mri_exam_id,
                    voxel_data=MockSegmentationData(),
                    atlas=atlas,
                )
                for atlas in self.atlases
            ]
            dti_data = [
                DTIMap(
                    mri_exam_id=synthetic_mri_exam_id,
                    voxel_data=MockVoxelData(),
                    dti_metric=metric,
                )
                for metric in DTIMetric
            ]
            # Create synthetic DTIAbnormalValues for AD only
            segmented_dti_map = [
                DTIAbnormalValues.from_dti_map(dti_map)
                for dti_map in dti_data if dti_map.dti_metric == DTIMetric.AD
            ]
            # marks some voxels as abnormal for testing purposes
            for dti_abnormal_values in segmented_dti_map:
                dti_abnormal_values.voxel_data.set_value_at(0, 0, 0, AbnormalValueType.LOW)

            return atlas_data + dti_data + segmented_dti_map

        # Patch the method to return synthetic data
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(MockSyntheticMRIExamRepository, '_build_synthetic_data_from_subject_id',
                            mock_build_synthetic_data)

        return SegmentDTIAbnormalValues(
            repositories_registry=repositories_registry,
            segmentation_merger=DummySegmentationMerger(),
            threshold_strategy=FixedThresholdStrategy(
                normative_value_repository=repositories_registry.get_repository(NormativeValue),
                center_repository=repositories_registry.get_repository(Center),
            )
        )

    def test_execute_use_case(self,
                              segment_dti_abnormal_values: SegmentDTIAbnormalValues):
        """
        Test if the ComputeDTINormativeValues use case workflow is executed
        without errors. It does not check the correctness of the results.
        """
        segment_dti_abnormal_values()

    def test_segmented_abnormal_values(self,
                                       segment_dti_abnormal_values: SegmentDTIAbnormalValues):
        """
        Test if the DTIAbnormalValues are correctly segmented and stored in the repository.
        """
        # Execute the use case
        segment_dti_abnormal_values()

        # Check if the abnormal values are computed and stored
        patient = segment_dti_abnormal_values.subjects_repository.list_all_patients()[0]
        mri_exam = segment_dti_abnormal_values.mri_repository.get_exam_for_subject(patient)

        abnormal_md_values = mri_exam.get_segmented_dti_abnormal_values(DTIMetric.MD)

        # Assert that the abnormal values are computed
        assert abnormal_md_values is not None, "Expected DTIAbnormalValues for MD to be computed and stored."
