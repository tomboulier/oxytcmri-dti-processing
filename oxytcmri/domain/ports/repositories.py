from typing import List, Optional, Protocol
from abc import ABC, abstractmethod
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas


class SubjectRepository(Protocol):
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


class MRIExamRepository(ABC):
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


class AtlasRepository(ABC):
    """Abstract base class for Atlas repository.
    Defines the interface for retrieving atlas data.
    """
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


class CenterRepository(ABC):
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
