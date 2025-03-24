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
        self.base_path = Path(base_path)

        # Ensure that the base path exists
        if not self.base_path.exists():
            raise FileNotFoundError(f"path '{base_path}' does not exist.")

        self.mri_exam_list = self.scan_nifti_folders()

    def scan_nifti_folders(self) -> list[MRIExam]:
        """
        Scan the base path for NIfTI folders and create MRIExam objects.

        Returns
        -------
        list[MRIExam]
            A list of MRIExam objects representing the NIfTI folders found in the base path.
        """
        result = []

        for mri_exam_folder in self.base_path.iterdir():
            if mri_exam_folder.is_dir():
                mri_exam = self._create_mri_exam_from_folder(mri_exam_folder)
                if mri_exam is not None:
                    result.append(mri_exam)

        return result

    @staticmethod
    def _create_mri_exam_from_folder(folder_path: Path) -> MRIExam:
        """
        Create an MRIExam object from a folder containing NIfTI files.

        Parameters
        ----------
        folder_path : Path
            Path to the folder containing NIfTI files

        Returns
        -------
        MRIExam
            A fully initialized MRIExam object with loaded data
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Path '{folder_path}' does not exist.")
        if not folder_path.is_dir():
            raise ValueError(f"Path '{folder_path}' is not a directory.")
        mri_exam_id = folder_path.name

        # Create basic MRIExam object
        mri_exam = MRIExam(id=mri_exam_id)

        # Load associated data (implement according to your file structure)
        # Example: mri_data = self._load_mri_data_from_folder(folder_path)
        # mri_exam.data = mri_data

        return mri_exam

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        """Retrieve the MRI exam for a specific subject.

        Parameters
        ----------
        subject_id : str
            The ID of the subject

        Returns
        -------
        MRIExam
            The MRI exam for the subject
        """
        for mri_exam in self.mri_exam_list:
            if mri_exam.subject_id == subject_id:
                return mri_exam

        raise ValueError(f"No MRI exam found for subject {subject_id}")
