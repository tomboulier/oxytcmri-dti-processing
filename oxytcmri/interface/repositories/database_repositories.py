from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Type, Any, List
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas, MRIExam
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.ports.repositories import CenterRepository, AtlasRepository, MRIExamRepository, SubjectRepository

T = TypeVar('T')


class DataBaseGateway(Generic[T], ABC):
    """Abstract base class for database access to repositories."""

    @abstractmethod
    def find_by_id(self, entity_type: Type[T], id_value: Any) -> Optional[T]:
        """Find an entity by its ID."""

    @abstractmethod
    def find_all(self, entity_type: Type[T]) -> list[T]:
        """Find all entities of a given type."""

    @abstractmethod
    def save(self, entity: T) -> None:
        """Save an entity to the database."""

    def save_list(self, entities: List[T]) -> None:
        """Save a list of entities to the database."""
        for entity in entities:
            self.save(entity)

    @abstractmethod
    def delete(self, entity: T) -> None:
        """Delete an entity from the database."""

    @abstractmethod
    def update(self, entity: T) -> None:
        """Update an entity in the database."""

    def delete_all(self, entity_type: Type[T]) -> None:
        """Delete all entities of a given type from the database."""
        for entity in self.find_all(entity_type):
            self.delete(entity)


class DataBaseCenterRepository(CenterRepository):
    """Persistence layer for Center entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        self.data_gateway = data_gateway

    def get_all_centers(self) -> list[Center]:
        return self.data_gateway.find_all(Center)

    def save_centers(self, centers: List[Center]) -> None:
        self.data_gateway.save_list(centers)


class DataBaseAtlasRepository(AtlasRepository):
    """Persistence layer for Atlas entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        self.data_gateway = data_gateway

    def get_atlas_by_id(self, atlas_id: int) -> Atlas:
        return self.data_gateway.find_by_id(Atlas, atlas_id)

    def get_all_atlases(self) -> List[Atlas]:
        return self.data_gateway.find_all(Atlas)

    def save_atlas(self, atlas: Atlas) -> None:
        self.data_gateway.save(atlas)


class DataBaseMRIExamRepository(MRIExamRepository):
    """Persistence layer for MRIExam entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        self.data_gateway = data_gateway

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        return self.data_gateway.find_by_id(MRIExam, subject_id)

    def save(self, mri_exam: MRIExam) -> None:
        self.data_gateway.save(mri_exam)


class DataBaseSubjectRepository(SubjectRepository):
    """Persistence layer for Subject entities using a database gateway."""
    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        self.data_gateway = data_gateway

    def find_subjects_by_center(self, center: Center, subject_type: Optional[SubjectType] = None) -> List[Subject]:
        all_subjects = self.data_gateway.find_all(Subject)

        results = []

        for subject in all_subjects:
            # filter by center
            if subject.center_id == center.id:
                # filter by subject type
                if subject_type is None or subject.subject_type == subject_type:
                    results.append(subject)

        return results

    def find_by_id(self, subject_id) -> Optional[Subject]:
        return self.data_gateway.find_by_id(Subject, subject_id)

    def save(self, subject: Subject) -> None:
        self.data_gateway.save(subject)
