import pytest
from oxytcmri.domain.entities.mri import Atlas
from oxytcmri.tests.unit.domain.mocks import MockInMemoryMRIRepository


class TestAtlasSegmentation:
    @pytest.fixture
    def atlas_segmentation(self):
        atlas = Atlas(id=2, labels=[29, 33, 62])
        mock_mri_exam_repository = MockInMemoryMRIRepository([atlas])
        mri_exam = mock_mri_exam_repository.get_exam_for_subject("01-01-V")
        return mri_exam.get_atlas_segmentation(atlas)

    def test_create_mask(self, atlas_segmentation):
        mask = atlas_segmentation.create_mask([29])
        assert mask is not None
        assert isinstance(mask.voxel_data.get_value_at(0, 0, 0), bool)
