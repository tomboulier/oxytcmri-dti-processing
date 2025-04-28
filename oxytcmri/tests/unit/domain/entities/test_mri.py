import pytest

from oxytcmri.domain.entities.mri import Atlas, MRIExamId, MRIExam
from oxytcmri.domain.entities.subject import SubjectId
from oxytcmri.tests.unit.domain.mocks import MockSyntheticMRIExamRepository


class TestMRIExamId:
    @pytest.mark.parametrize("exam_id,expected_subject_id", [
        ("06-78P-MR-170918", "06-78-P"),
        ("10_73V_MR301015", "10-73-V"),
        ("13-73P-190717", "13-73-P"),
        ("01_74T_MR_101117", "01-74-T"),
        ("23-69V-MR-220101", "23-69-V"),
        ("11-73-VR", "11-73-V"),
        ("18_71_V_GT", "18-71-V")
    ])
    def test_to_subject_id_valid_formats(self, exam_id, expected_subject_id):
        assert MRIExamId(exam_id).to_subject_id() == SubjectId(expected_subject_id)

    @pytest.mark.parametrize("invalid_id", [
        "10-03X-MR301015",  # invalid subject type
        "AB_CDZ_MR000000",  # totally invalid
        "01-04-MR-191216",  # missing subject type
        "MR-01-74P-191216",  # incorrect order
        "xyz",  # too short
    ])
    def test_to_subject_id_invalid_formats_raise(self, invalid_id):
        with pytest.raises(ValueError):
            MRIExamId(invalid_id).to_subject_id()


class TestMRIExam:
    def test_mri_exam_id(self):
        # Test if the MRIExamId is set correctly
        string_exam_id = "06-78P-MR-170918"
        mri_exam = MRIExam.from_string_exam_id(string_exam_id)
        assert mri_exam.id == MRIExamId(string_exam_id)
        assert mri_exam.subject_id == SubjectId("06-78-P")

class TestAtlasSegmentation:
    @pytest.fixture
    def atlas_segmentation(self):
        atlas = Atlas(id=2, labels=[29, 33, 62])
        mock_mri_exam_repository = MockSyntheticMRIExamRepository([atlas])
        mri_exam = mock_mri_exam_repository.get_exam_for_subject("01-71-V")
        return mri_exam.get_atlas_segmentation(atlas)

    def test_create_mask(self, atlas_segmentation):
        mask = atlas_segmentation.create_mask([29])
        assert mask is not None
        assert isinstance(mask.voxel_data.get_value_at(0, 0, 0), bool)
