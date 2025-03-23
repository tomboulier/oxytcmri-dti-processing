import pytest
from oxytcmri.domain.entities.mri import MRIExamId, MRIExam  # Remplace "your_module" par le nom réel du fichier/module

class TestMRIExamId:
    @pytest.mark.parametrize("exam_id,expected_subject_id", [
        ("06-08P-MR-170918", "06-08-P"),
        ("10_03V_MR301015", "10-03-V"),
        ("13-03P-190717", "13-03-P"),
        ("01_04T_MR_101117", "01-04-T"),
        ("23-99V-MR-220101", "23-99-V"),
        ("11-03-VR", "11-03-V"),
        ("18_01_V_GT", "18-01-V")
    ])
    def test_to_subject_id_valid_formats(self, exam_id, expected_subject_id):
        assert MRIExamId(exam_id).to_subject_id() == expected_subject_id

    @pytest.mark.parametrize("invalid_id", [
        "10-03X-MR301015",     # invalid subject type
        "AB_CDZ_MR000000",     # totally invalid
        "01-04-MR-191216",     # missing subject type
        "MR-01-04P-191216",    # incorrect order
    ])
    def test_to_subject_id_invalid_formats_raise(self, invalid_id):
        with pytest.raises(ValueError):
            MRIExamId(invalid_id).to_subject_id()


class TestMRIExam:
    def test_mri_exam_id(self):
        # Test if the MRIExamId is set correctly
        mri_exam = MRIExam(id="06-08P-MR-170918")
        assert mri_exam.id == MRIExamId("06-08P-MR-170918")
        assert mri_exam.subject_id == "06-08-P"
