from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository


class TestNiftiFoldersMRIExamRepository:
    def test_create_niti_folders_instance(self):
        nifti_folders = NiftiFoldersMRIExamRepository(
            base_path="/path/to/base"
        )
