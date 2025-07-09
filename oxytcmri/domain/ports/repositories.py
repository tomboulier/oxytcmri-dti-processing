"""
This module defines repositories for the application, storing and retrieving entities.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic, Type

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas, MRIExamId, RegionOfInterest
from oxytcmri.domain.entities.subject import Subject, SubjectType, SubjectId

Entity = TypeVar('Entity')
EntityIdentifier = TypeVar('EntityIdentifier')


class EntityNotFoundException(LookupError):
    """
    Generic exception raised when an entity is not found in the repository.
    """

    def __init__(self, message: str, repository: Repository):
        super().__init__(message)
        self.repository = repository


class EntityIdNotFoundException(EntityNotFoundException):
    """
    Exception raised when an entity is not found based on its ID.
    """

    def __init__(self, entity_id: EntityIdentifier, repository: Repository):
        message = f"Entity with ID {entity_id} not found in repository {repository}"
        super().__init__(message=message, repository=repository)
        self.entity_id = entity_id


class Repository(ABC, Generic[Entity, EntityIdentifier]):
    """
    Abstract base class for repositories.
    Defines the interface for all repositories in the application.
    """

    @abstractmethod
    def exists(self, entity: Entity) -> bool:
        """
        Check if an entity exists in the repository

        Parameters
        ----------
        entity : Entity
            The entity to check for existence

        Returns
        -------
        bool
            True if the entity exists, False otherwise
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
        EntityIdNotFoundException
            If the entity with the given ID does not exist
        """
        entity = self.find_by_id(entity_id)
        if entity is None:
            raise EntityIdNotFoundException(entity_id, self)
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

    def save_list(self, entity_list: List[Entity]) -> None:
        """
        Save a list of entities to the repository.

        Parameters
        ----------
        entity_list : List[Entity]
            The list of entities to save
        """
        for entity in entity_list:
            self.save(entity)

    @abstractmethod
    def delete(self, entity: Entity) -> None:
        """
        Delete an entity from the repository.

        Parameters
        ----------
        entity : Entity
            The entity to delete
        """

    def update(self, entity: Entity) -> None:
        """
        Update an existing entity in the repository, meaning it will first delete it if it exists and then save the
        updated entity.

        Parameters
        ----------
        entity : Entity
            The entity to update
        """
        if self.exists(entity):
            self.delete(entity)
        self.save(entity)


class SubjectRepository(Repository[Subject, SubjectId], ABC):

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
        all_subjects = self.list_all()
        results = []

        for subject in all_subjects:
            # filter by center
            if subject.center_id == center.id:
                # filter by subject type
                if subject_type is None or subject.subject_type == subject_type:
                    results.append(subject)

        return results

    def list_all_patients(self) -> List[Subject]:
        """
        List all patients in the repository.

        Returns
        -------
        List[Subject]
            List of all patients
        """
        all_subjects = self.list_all()
        return [subject for subject in all_subjects if subject.subject_type == SubjectType.PATIENT]


class MRIExamRepository(Repository[MRIExam, MRIExamId]):
    """
    Abstract base class for MRI repository.
    Defines the interface for retrieving MRI exam data.
    """

    @abstractmethod
    def get_exam_for_subject(self, subject: Subject) -> MRIExam:
        """
        Retrieve the MRI exam for a specific subject.

        Parameters
        ----------
        subject : Subject
            The subject to retrieve the MRI exam for

        Returns
        -------
        MRIExam
            The MRI exam for the subject
        """


class AtlasRepository(Repository[Atlas, int], ABC):
    """Abstract base class for Atlas repository.
    Defines the interface for retrieving atlas data.
    """


class RegionOfInterestRepository(Repository[RegionOfInterest, str], ABC):
    """Abstract base class for Region of Interest repository.
    Defines the interface for retrieving regions of interest data.
    """


class CenterRepository(Repository[Center, int], ABC):
    """Abstract base class for Center repository."""

    def get_by_mri_exam_id(self, mri_exam_id: MRIExamId) -> Center:
        """
        Retrieve the center associated with a specific MRI exam ID.

        Parameters
        ----------
        mri_exam_id : MRIExamId
            The ID of the MRI exam

        Returns
        -------
        Center
            The center associated with the MRI exam ID

        Raises
        ------
        EntityNotFoundException
            If the center with the given MRIExamId does not exist
        """
        subject_id: SubjectId = mri_exam_id.to_subject_id()
        center_id = subject_id.center_id
        center = self.find_by_id(center_id)
        if center is None:
            raise EntityNotFoundException(
                f"Center with ID {center_id} not found for MRI exam ID {mri_exam_id}",
                self,
            )
        return center


class RepositoriesRegistry(ABC):
    """
    Abstract base class for a registry responsible for managing the repositories in the application.
    """

    @abstractmethod
    def get_repository(self, entity_type: Type[Entity]) -> Repository[Entity, EntityIdentifier]:
        """Return the repository corresponding to the given entity type."""

    @abstractmethod
    def list_all_repositories(self) -> List[Repository[Entity, EntityIdentifier]]:
        """Return a list of all repositories in the registry."""
