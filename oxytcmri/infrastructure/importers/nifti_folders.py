from pathlib import Path

from oxytcmri.domain.entities.mri import MRIExam
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.repositories import SubjectRepository, MRIExamRepository, AtlasRepository, Repository
from oxytcmri.interface.importers import Importer
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository


class NiftiFoldersImporter(Importer):
    """
    Importer for NIfTI folders that extracts MRI exams data and stores them in repositories.

    This class uses a NiftiFoldersMRIExamRepository to scan folders and extract MRI data,
    then stores the extracted data in persistent repositories.

    Parameters
    ----------
    base_path : str
        Path to the folder containing NIfTI data folders
    subject_repository : SubjectRepository
        Repository for storing subject information
    mri_exam_repository : MRIExamRepository
        Persistent repository for storing MRI exam data
    atlas_repository : AtlasRepository
        Repository for storing atlas information
    """

    def __init__(
            self,
            base_path: str,
            subject_repository: SubjectRepository = None,
            mri_exam_repository: MRIExamRepository = None,
            atlas_repository: AtlasRepository = None,
    ):
        self.base_path = Path(base_path)
        # Ensure that the base path exists
        if not self.base_path.exists():
            raise FileNotFoundError(f"Path '{base_path}' does not exist.")
        self.nifti_folders_repository = NiftiFoldersMRIExamRepository(base_path, atlas_repository)

        # persistent repositories
        self.subject_repository = subject_repository
        self.mri_exam_repository = mri_exam_repository

    def register_repository(self, repositories: list[Repository]):
        """
        Register the needed repositories for the importer.

        Parameters
        ----------
        repositories : list[Repository]
            List of repositories to register.
        """
        for repository in repositories:
            if isinstance(repository, SubjectRepository):
                self.subject_repository = repository
            elif isinstance(repository, MRIExamRepository):
                self.mri_exam_repository = repository
            elif isinstance(repository, AtlasRepository):
                self.nifti_folders_repository.atlas_repository = repository

    def import_data(self) -> None:
        """
        Import MRI exam data from NIfTI folders and store in repositories.

        This method scans the NIfTI folders, extracts MRI exam data, and stores
        the data in the subject and MRI exam repositories.
        """
        self.check_repositories()

        # Scan folders and get MRI exams
        mri_exams = self.nifti_folders_repository.scan_nifti_folders()

        # Import each MRI exam
        for mri_exam in mri_exams:
            self._import_mri_exam(mri_exam)

    def check_repositories(self) -> None:
        """
        Check if subject and MRI exam repositories are set.

        Raises
        ------
        ValueError
            If subject or MRI exam repository is not set.
        """
        if self.subject_repository is None:
            raise ValueError("Subject repository is not set.")
        if self.mri_exam_repository is None:
            raise ValueError("MRI exam repository is not set.")
        if self.nifti_folders_repository is None:
            raise ValueError("Nifti folders repository is not set.")
        if self.nifti_folders_repository.atlas_repository is None:
            raise ValueError("Atlas repository is not set in Nifti folders repository.")

    def _import_mri_exam(self, mri_exam: MRIExam) -> None:
        """
        Import a single MRI exam and associated subject.

        Parameters
        ----------
        mri_exam : MRIExam
            MRI exam to import
        """
        # Extract subject ID from MRI exam
        subject_id = mri_exam.subject_id

        # Check if subject already exists
        subject = self.subject_repository.find_by_id(subject_id)
        if subject is None:
            # If subject doesn't exist, create it from the MRI exam ID
            subject = Subject.from_string_id(subject_id)
            self.subject_repository.save(subject)

        # Store the MRI exam in the repository
        self.mri_exam_repository.save(mri_exam)
