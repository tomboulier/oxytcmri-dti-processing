from oxytcmri.domain.entities.mri import DTIMap, MRIExamId, DTIMetric, AtlasSegmentation, MRIExam
from oxytcmri.domain.entities.subject import SubjectId
from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentDTIAbnormalValues, AbnormalVoxelData, \
    AbnormalValueType
from oxytcmri.tests.unit.domain.mocks import (
    MockInMemoryRepositoriesRegistry, MockVoxelData, MockMaskData, MockSegmentationData
)


class TestSegmentDTIAbnormalValues:
    def test_execute_use_case(self):
        """
        Test if the ComputeDTINormativeValues use case workflow is executed
        without errors. It does not check the correctness of the results.
        """
        # definitions
        compute_normative_values = SegmentDTIAbnormalValues(
            MockInMemoryRepositoriesRegistry(),
        )

        # execution
        compute_normative_values()

    def test_segment_dti_map_for_atlas(self):
        """
        Test the segment_dti_map_for_atlas method to ensure it properly identifies and marks
        abnormal voxels. This test specifically focuses on the loop that processes abnormal values
        and checks if voxels with values outside of thresholds are correctly marked as both
        HIGH and LOW abnormalities.
        """
        # Initialize the use case with mock repositories
        segment_dti = SegmentDTIAbnormalValues(
            MockInMemoryRepositoriesRegistry(),
        )
        
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
            mri_exam_id=MRIExamId("test-exam"),
            voxel_data=MockDTIVoxelDataWithAbnormalValues(),
            dti_metric=DTIMetric.FA
        )
        
        # Get an atlas from the repository
        atlas = segment_dti.atlas_repository.list_all()[0]
        
        # Create a mock MRIExam with our custom atlas segmentation
        mri_exam = MRIExam(
            id=dti_image.mri_exam_id,
            subject_id=SubjectId("01-01-T"),
            data=[
                MockAtlasSegmentationWithCoordinates(
                    mri_exam_id=dti_image.mri_exam_id,
                    voxel_data=MockSegmentationData(),
                    atlas=atlas
                )
            ]
        )
        
        # Override the get_by_id method in mri_repository to return our custom MRIExam
        original_get_by_id = segment_dti.mri_repository.find_by_id
        segment_dti.mri_repository.find_by_id = lambda id: mri_exam if id == dti_image.mri_exam_id else original_get_by_id(id)
        
        # Execute the method being tested
        result = segment_dti.segment_dti_map_for_atlas(dti_image, atlas)
        
        # Verify that abnormal voxels were detected and marked correctly
        # Check HIGH abnormality
        assert result.voxel_data.is_abnormal(1, 2, 3), "First test coordinate should be marked as abnormal (HIGH)"
        assert result.voxel_data.get_value_at(1, 2, 3) == AbnormalValueType.HIGH, "Expected HIGH abnormality type"
        
        # Check LOW abnormality
        assert result.voxel_data.is_abnormal(4, 5, 6), "Second test coordinate should be marked as abnormal (LOW)"
        assert result.voxel_data.get_value_at(4, 5, 6) == AbnormalValueType.LOW, "Expected LOW abnormality type"
        
        # Check that normal values are not marked as abnormal
        assert not result.voxel_data.is_abnormal(7, 8, 9), "Third test coordinate should not be marked as abnormal"
