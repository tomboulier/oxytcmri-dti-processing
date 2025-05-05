import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMap, MRIExamId, DTIMetric, AtlasSegmentation, MRIExam, Atlas
from oxytcmri.domain.entities.subject import SubjectId
from oxytcmri.domain.ports.repositories import CenterRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue
from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentDTIAbnormalValues, AbnormalVoxelData, \
    AbnormalValueType, ThresholdStrategy, DTIThresholds
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemoryRepositoriesRegistry, MockVoxelData, MockMaskData, MockSegmentationData
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


class TestSegmentDTIAbnormalValues:
    @pytest.fixture
    def segment_dti_abnormal_values(self) -> SegmentDTIAbnormalValues:
        repositories_registry = MockInMemoryRepositoriesRegistry()
        return SegmentDTIAbnormalValues(
            repositories_registry,
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

    def test_segment_dti_map_for_atlas(self,
                                       segment_dti_abnormal_values: SegmentDTIAbnormalValues):
        """
        Test the segment_dti_map_for_atlas method to ensure it properly identifies and marks
        abnormal voxels. This test specifically focuses on the loop that processes abnormal values
        and checks if voxels with values outside of thresholds are correctly marked as both
        HIGH and LOW abnormalities.
        """
        
        # Create a mock DTI VoxelData class that returns abnormal values based on coordinates
        class MockDTIVoxelDataWithAbnormalValues(MockVoxelData):
            def get_value_at(self, x: int, y: int, z: int) -> float:
                # Return HIGH value for first set of coordinates, LOW value for second set
                if (x, y, z) == (1, 2, 3):
                    return 0.9  # HIGH value (above 0.8 threshold)
                elif (x, y, z) == (4, 5, 6):
                    return 0.2  # LOW value (below 0.3 threshold)
                else:
                    return 0.5  # Normal value
        
        # Create a mock mask that returns specific coordinates
        class MockMaskWithCoordinates(MockMaskData):
            def get_true_voxel_coordinates(self):
                # Return some coordinates for testing
                return [(1, 2, 3), (4, 5, 6), (7, 8, 9)]  # 3rd set should be normal
        
        # Create a mock atlas segmentation that returns our custom mask
        class MockAtlasSegmentationWithCoordinates(AtlasSegmentation):
            def create_mask(self, labels):
                return MockMaskWithCoordinates()
        
        # Create a DTI map with the custom voxel data
        dti_image = DTIMap(
            mri_exam_id=MRIExamId("01_02t_mr_150316"),
            voxel_data=MockDTIVoxelDataWithAbnormalValues(),
            dti_metric=DTIMetric.FA
        )
        
        # Get an atlas from the repository
        atlas = segment_dti_abnormal_values.atlas_repository.list_all()[0]
        
        # Create a mock MRIExam with our custom atlas segmentation
        mri_exam = MRIExam(
            id=dti_image.mri_exam_id,
            subject_id=SubjectId("01-02-T"),
            data=[
                MockAtlasSegmentationWithCoordinates(
                    mri_exam_id=dti_image.mri_exam_id,
                    voxel_data=MockSegmentationData(),
                    atlas=atlas
                )
            ]
        )
        
        # Override the get_by_id method in mri_repository to return our custom MRIExam
        original_get_by_id = segment_dti_abnormal_values.mri_repository.find_by_id
        segment_dti_abnormal_values.mri_repository.find_by_id = lambda id: mri_exam if id == dti_image.mri_exam_id else original_get_by_id(id)
        
        # Execute the method being tested
        result = segment_dti_abnormal_values.segment_dti_map_for_atlas(dti_image, atlas)
        
        # Verify that abnormal voxels were detected and marked correctly
        # Check HIGH abnormality
        assert result.voxel_data.is_abnormal(1, 2, 3), "First test coordinate should be marked as abnormal (HIGH)"
        assert result.voxel_data.get_value_at(1, 2, 3) == AbnormalValueType.HIGH, "Expected HIGH abnormality type"
        
        # Check LOW abnormality
        assert result.voxel_data.is_abnormal(4, 5, 6), "Second test coordinate should be marked as abnormal (LOW)"
        assert result.voxel_data.get_value_at(4, 5, 6) == AbnormalValueType.LOW, "Expected LOW abnormality type"
        
        # Check that normal values are not marked as abnormal
        assert not result.voxel_data.is_abnormal(7, 8, 9), "Third test coordinate should not be marked as abnormal"
