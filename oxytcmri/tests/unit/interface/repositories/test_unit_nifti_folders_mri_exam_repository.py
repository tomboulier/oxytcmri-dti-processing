from pathlib import Path
import random
from typing import List

import pytest

from oxytcmri.domain.entities.mri import Atlas, MRIExam, DTIMetric
from oxytcmri.domain.ports.repositories import AtlasRepository
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository
from oxytcmri.tests.fixtures import path_to_test_data_folder


class TestNiftiFoldersMRIExamRepository:
    @pytest.fixture
    def folder_base_path(self):
        """Get the path to the test data folder."""
        return str(path_to_test_data_folder() / "NiftiFoldersMRIExamRepository")

    @pytest.fixture
    def mock_atlas_repository(self) -> AtlasRepository:
        # Mock an instance of AtlasRepository
        class MockAtlasRepository(AtlasRepository):
            def save_atlas(self, atlas: Atlas) -> None:
                pass

            def get_all_atlases(self) -> List[Atlas]:
                pass

            def get_atlas_by_id(self, atlas_id: int) -> Atlas:
                """Mock method to return a random atlas."""
                return Atlas(id=atlas_id, labels=[])

        return MockAtlasRepository()

    @pytest.fixture()
    def nifti_folders_instance(self, folder_base_path, mock_atlas_repository) -> NiftiFoldersMRIExamRepository:
        return NiftiFoldersMRIExamRepository(folder_base_path, mock_atlas_repository)

    def test_inexistence_of_base_path(self, mock_atlas_repository):
        # Test if ValueError is raised when the base path does not exist
        with pytest.raises(FileNotFoundError):
            NiftiFoldersMRIExamRepository("non/existent/path", mock_atlas_repository)

    def test_scan_nifti_folders_identifies_correct_number_of_folders(self, nifti_folders_instance):
        # Test if the scan_nifti_folders method correctly identifies folders
        mri_exam_list = nifti_folders_instance.scan_nifti_folders()
        assert len(mri_exam_list) == 23

    def test_create_mri_exam_from_folder_creates_mri_exam_object(self, nifti_folders_instance):
        # Unit test for _create_mri_exam_from_folder method
        folder_path = Path(nifti_folders_instance.base_path) / "01_01v_mr_170913"
        mri_exam = nifti_folders_instance._create_mri_exam_from_folder(folder_path)
        assert isinstance(mri_exam, MRIExam)
        assert len(mri_exam.data) == 3

        assert mri_exam.get_dti_map(DTIMetric.MD) is not None

        atlas = Atlas(id=2, labels=[29, 33, 62])
        assert mri_exam.get_atlas_segmentation(atlas=atlas) is not None

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
