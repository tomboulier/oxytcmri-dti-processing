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

        Parameters
        ----------
        None

        Returns
        -------
        list[MRIExam]
            A list of MRIExam objects representing the NIfTI folders found in the base path.
        """
        result = []

        for mri_exam_folder in self.base_path.iterdir():
            if mri_exam_folder.is_dir():
                mri_exam_id = mri_exam_folder.name
                mri_exam = MRIExam(id=mri_exam_id)
                result.append(mri_exam)

        return result

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
