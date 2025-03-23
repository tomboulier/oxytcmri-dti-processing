import os
from pathlib import Path

from oxytcmri.domain.entities.mri import MRIExam
from oxytcmri.domain.ports.repositories import MRIExamRepository

class NiftiFoldersMRIExamRepository(MRIExamRepository):
    def __init__(self, base_path: str):
        """Initialize the repository with a base path for NIfTI files.

        Parameters
        ----------
        base_path : str
            The base path where NIfTI files are stored.
        """
        # Ensure first that the base path exists
        if not os.path.exists(base_path):
            raise ValueError(f"path '{base_path}' does not exist.")
        self.base_path = Path(base_path)

    def get_nifti_file_paths(self):
        # This method would contain logic to retrieve NIfTI file paths
        pass

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        pass
