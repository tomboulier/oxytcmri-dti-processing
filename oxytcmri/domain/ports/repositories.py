"""
This module defines repositories for the application, storing and retrieving entities.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas
from oxytcmri.domain.entities.subject import Subject, SubjectType

Entity = TypeVar('Entity')
EntityIdentifier = TypeVar('EntityIdentifier')


class EntityNotFoundException(Exception):
    """
    Exception raised when an entity is not found in the repository.
    """

    def __init__(self, entity: Entity, repository: Repository):
        super().__init__(f"Entity {entity} not found in repository {repository}")
        self.entity = entity


class Repository(ABC, Generic[Entity, EntityIdentifier]):
    """
    Abstract base class for repositories.
    Defines the interface for all repositories in the application.
    """

    @abstractmethod
    def find_by_id(self, entity_id: EntityIdentifier) -> Optional[Entity]:
        """
        Retrieve an entity by its ID.

        Parameters
        ----------
        entity_id : EntityIdentifier
            The ID of the entity

        Returns
        -------
        Entity
            The entity object if found, otherwise None
        """

    def get_by_id(self, entity_id: EntityIdentifier) -> Entity:
        """
        Retrieve an entity by its ID.

        Parameters
        ----------
        entity_id : EntityIdentifier
            The ID of the entity

        Returns
        -------
        Entity
            The entity object

        Raises
        -------
        EntityNotFoundException
            If the entity with the given ID does not exist
        """
        entity = self.find_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundException(entity_id, self)
        return entity

    @abstractmethod
    def list_all(self) -> List[Entity]:
        """
        List all entities in the repository.

        Returns
        -------
        List[Entity]
            List of all entities
        """

    @abstractmethod
    def save(self, entity: Entity) -> None:
        """
        Save an entity to the repository.

        Parameters
        ----------
        entity : Entity
            The entity to save
        """

    @abstractmethod
    def delete(self, entity: Entity) -> None:
        """
        Delete an entity from the repository.

        Parameters
        ----------
        entity : Entity
            The entity to delete
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

    @abstractmethod
    def get_center_by_id(self, center_id: int) -> Center:
        """
        Retrieve a center by its ID.

        Parameters
        ----------
        center_id : int
            The ID of the center

        Returns
        -------
        Center
            The center object
        """
