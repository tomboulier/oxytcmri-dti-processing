from pathlib import Path
import pytest
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository


class TestNiftiFoldersMRIExamRepository:
    @pytest.fixture
    def folder_base_path(self):
        test_data_folder = Path(__file__).resolve().parents[2] / 'test-data'
        return str(test_data_folder / "NiftiFoldersMRIExamRepository")

    @pytest.fixture()
    def nifti_folders_instance(self, folder_base_path) -> NiftiFoldersMRIExamRepository:
        return NiftiFoldersMRIExamRepository(folder_base_path)

    def test_inexistence_of_base_path(self):
        # Test if ValueError is raised when the base path does not exist
        with pytest.raises(FileNotFoundError):
            NiftiFoldersMRIExamRepository("non/existent/path")

    def test_scan_nifti_folders_identifies_correct_number_of_folders(self, nifti_folders_instance):
        # Test if the scan_nifti_folders method correctly identifies folders
        mri_exam_list = nifti_folders_instance.scan_nifti_folders()
        assert len(mri_exam_list) == 23

    def test_get_exam_for_subject_raises_value_error(self, nifti_folders_instance):
        # Test if the method raises ValueError when the subject ID is invalid
        subject_id = "invalid_subject_id"
        with pytest.raises(ValueError):
            nifti_folders_instance.get_exam_for_subject(subject_id)

    def test_get_exam_for_subject(self, nifti_folders_instance):
        # Test if the method correctly retrieves the MRI exam for a valid subject ID
        subject_id = "01-01-V"
        mri_exam = nifti_folders_instance.get_exam_for_subject(subject_id)
        assert mri_exam is not None
        assert mri_exam.subject_id == subject_id
