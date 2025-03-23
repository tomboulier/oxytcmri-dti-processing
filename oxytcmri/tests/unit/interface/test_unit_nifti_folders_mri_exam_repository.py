from pathlib import Path
import pytest
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository


class TestNiftiFoldersMRIExamRepository:
    @pytest.fixture
    def folder_base_path(self):
        test_data_folder = Path(__file__).resolve().parents[2] / 'test-data'
        return str(test_data_folder / "NiftiFoldersMRIExamRepository")

    def test_inexistence_of_base_path(self):
        # Test if ValueError is raised when the base path does not exist
        with pytest.raises(FileNotFoundError):
            NiftiFoldersMRIExamRepository("non/existent/path")

    def test_create_niti_folders_instance(self, folder_base_path):
        nifti_folders = NiftiFoldersMRIExamRepository(folder_base_path)
