from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Type, Any, List
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.ports.repositories import CenterRepository

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
