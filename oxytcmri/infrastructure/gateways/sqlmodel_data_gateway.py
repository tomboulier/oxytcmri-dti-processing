from __future__ import annotations
from pathlib import Path
from typing import Type, Any, Optional, List, Dict, TypeVar, Generic

from sqlmodel import SQLModel, Session, create_engine, select, Field

from oxytcmri.domain.entities.center import Center
from oxytcmri.interface.repositories.database_repositories import DataBaseGateway


# Define SQLModel models for entities
T = TypeVar('T')  # Generic type variable for entities

class BaseDTO(SQLModel, Generic[T]):
    """Base class for all Data Transfer Objects with entity conversion methods."""

    @classmethod
    def from_entity(cls, entity: T) -> BaseDTO[T]:
        """Create a DTO from a domain entity."""
        raise NotImplementedError("Subclasses must implement from_entity")

    def to_entity(self) -> T:
        """Convert the DTO to a domain entity."""
        raise NotImplementedError("Subclasses must implement to_entity")


class CenterDTO(BaseDTO[Center], table=True):
    """DTO for Center entity with database mapping."""
    __tablename__ = "centers"

    id: int = Field(primary_key=True)
    name: str

    @classmethod
    def from_entity(cls, entity: Center) -> CenterDTO:
        return cls(id=entity.id, name=entity.name)

    def to_entity(self) -> Center:
        return Center(id=self.id, name=self.name)


class SQLModelSQLiteDataGateway(DataBaseGateway[T]):
    """SQLModel implementation of DataBaseGateway for SQLite."""

    def update(self, entity: T) -> None:
        pass

    def __init__(self, database_path: str):
        """
        Initialize the gateway with the path to the database.

        Parameters
        ----------
        database_path : str
            Path to the SQLite file
        """
        self.database_path = Path(database_path)
        # Ensure the parent directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create the engine
        self.engine = create_engine(f"sqlite:///{database_path}", echo=False)

        # Create tables if they don't exist
        SQLModel.metadata.create_all(self.engine)

        # Mapping from entity types to SQLModel model classes
        self.entity_to_model_map: Dict[Type, Type[SQLModel]] = {
            Center: CenterDTO
        }

    def _get_model_class(self, entity_type: Type[T]) -> Type[SQLModel]:
        """Get the SQLModel class corresponding to the entity type."""
        if entity_type not in self.entity_to_model_map:
            raise ValueError(f"No model mapping found for entity type {entity_type.__name__}")
        return self.entity_to_model_map[entity_type]

    def _entity_to_model(self, entity: T) -> SQLModel:
        """Convert an entity to a SQLModel instance."""
        if isinstance(entity, Center):
            return CenterDTO.from_entity(entity)
        raise ValueError(f"No conversion implemented for entity type {type(entity).__name__}")

    def _model_to_entity(self, model: SQLModel, entity_type: Type[T]) -> T:
        """Convert a SQLModel instance to an entity."""
        if entity_type == Center and isinstance(model, CenterDTO):
            return model.to_entity()
        raise ValueError(f"No conversion implemented for model type {type(model).__name__}")

    def find_by_id(self, entity_type: Type[T], id_value: Any) -> Optional[T]:
        """Retrieve an entity by its ID."""
        model_class = self._get_model_class(entity_type)

        with Session(self.engine) as session:
            statement = select(model_class).where(model_class.id == id_value)
            model = session.exec(statement).first()

            if model is None:
                return None

            return self._model_to_entity(model, entity_type)

    def find_all(self, entity_type: Type[T]) -> List[T]:
        """Retrieve all entities of the given type."""
        model_class = self._get_model_class(entity_type)

        with Session(self.engine) as session:
            statement = select(model_class)
            models = session.exec(statement).all()

            # Convert models to entities
            entities = [self._model_to_entity(model, entity_type) for model in models]
            return entities

    def save(self, entity: T) -> T:
        """Save an entity (create or update)."""
        model = self._entity_to_model(entity)

        with Session(self.engine) as session:
            # Use merge to handle both insert and update
            model = session.merge(model)
            session.commit()
            session.refresh(model)

            return self._model_to_entity(model, type(entity))

    def delete(self, entity: T) -> None:
        """Delete an entity."""
        model_class = self._get_model_class(type(entity))

        with Session(self.engine) as session:
            statement = select(model_class).where(model_class.id == entity.id)
            model = session.exec(statement).first()

            if model:
                session.delete(model)
                session.commit()
