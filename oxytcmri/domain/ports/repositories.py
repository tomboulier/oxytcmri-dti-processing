from typing import List, Optional
from abc import ABC, abstractmethod
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas


class Repository(ABC):
    """
    Abstract base class for repositories.
    Defines the interface for all repositories in the application.
    """


class SubjectRepository(Repository):
    @abstractmethod
    def find_subjects_by_center(
            self, center: Center, subject_type: Optional[SubjectType] = None
    ) -> List[Subject]:
        """
        Find subjects for a given center, optionally filtered by type.

        Parameters
        ----------
        center : Center
            The center to find subjects for
        subject_type : Optional[SubjectType], default=None
            If provided, only return subjects of this type

        Returns
        -------
        List[Subject]
            List of matching subjects
        """

    @abstractmethod
    def find_by_id(self, subject_id) -> Optional[Subject]:
        """
        Find a subject by its ID.

        Parameters
        ----------
        subject_id : str
            The ID of the subject

        Returns
        -------
        Subject
            The subject object if found, otherwise None
        """

    @abstractmethod
    def save(self, subject: Subject) -> None:
        """
        Save a subject to the repository.

        Parameters
        ----------
        subject : Subject
            The subject to save
        """


class MRIExamRepository(Repository):
    """
    Abstract base class for MRI repository.
    Defines the interface for retrieving MRI exam data.
    """

    @abstractmethod
    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        """
        Retrieve the MRI exam for a specific subject.

        Parameters
        ----------
        subject_id : str
            The ID of the subject

        Returns
        -------
        MRIExam
            The MRI exam for the subject
        """

    @abstractmethod
    def save(self, mri_exam: MRIExam) -> None:
        """
        Save an MRI exam to the repository.

        Parameters
        ----------
        mri_exam : MRIExam
            The MRI exam to save
        """


class AtlasRepository(Repository):
    """Abstract base class for Atlas repository.
    Defines the interface for retrieving atlas data.
    """

    @abstractmethod
    def get_atlas_by_id(self, atlas_id: int) -> Atlas:
        """
        Retrieve an atlas by its ID.

        Parameters
        ----------
        atlas_id : int
            The ID of the atlas

        Returns
        -------
        Atlas
            The atlas object
        """

    @abstractmethod
    def get_all_atlases(self) -> List[Atlas]:
        """
        Retrieve all atlases.

        Returns
        -------
        List[Atlas]
            List of all atlases
        """

    @abstractmethod
    def save_atlas(self, atlas: Atlas) -> None:
        """
        Save an atlas to the repository.

        Parameters
        ----------
        atlas : Atlas
            The atlas to save
        """


class CenterRepository(Repository):
    """Abstract base class for Center repository."""

    @abstractmethod
    def get_all_centers(self) -> List[Center]:
        """
        Retrieve all centers.

        Returns
        -------
        List[Center]
            List of all centers
        """

    @abstractmethod
    def save_centers(self, centers: List[Center]) -> None:
        """
        Save centers to the repository.

        Parameters
        ----------
        centers : List[Center]
            List of centers to save
        """
