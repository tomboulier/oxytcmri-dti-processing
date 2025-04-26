import pytest

from oxytcmri.domain.entities.mri import MRIExamId, MRIExam  # Remplace "your_module" par le nom réel du fichier/module


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
        assert MRIExamId(exam_id).to_subject_id() == expected_subject_id

    @pytest.mark.parametrize("invalid_id", [
        "10-03X-MR301015",     # invalid subject type
        "AB_CDZ_MR000000",     # totally invalid
        "01-04-MR-191216",     # missing subject type
        "MR-01-74P-191216",    # incorrect order
        "xyz",  # too short
    ])
    def test_to_subject_id_invalid_formats_raise(self, invalid_id):
        with pytest.raises(ValueError):
            MRIExamId(invalid_id).to_subject_id()


class TestMRIExam:
    def test_mri_exam_id(self):
        # Test if the MRIExamId is set correctly
        mri_exam = MRIExam(id="06-78P-MR-170918")
        assert mri_exam.id == MRIExamId("06-78P-MR-170918")
        assert mri_exam.subject_id == "06-78-P"
