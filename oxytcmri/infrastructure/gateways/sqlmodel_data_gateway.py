from __future__ import annotations

from abc import ABC, abstractmethod, abstractclassmethod
from pathlib import Path
from typing import Type, Any, Optional, List, Dict, TypeVar, Generic

from sqlmodel import SQLModel, Session, create_engine, select, Field, JSON

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas
from oxytcmri.interface.repositories.database_repositories import DataBaseGateway

# Define SQLModel models for entities
EntityType = TypeVar('EntityType')  # Generic type variable for entities


class BaseDTO(SQLModel, Generic[EntityType], ABC):
    """Base class for all Data Transfer Objects with entity conversion methods."""

    @classmethod
    @abstractmethod
    def from_entity(cls, entity: EntityType) -> BaseDTO[EntityType]:
        """Create a DTO from a domain entity."""

    @abstractmethod
    def to_entity(self) -> EntityType:
        """Convert the DTO to a domain entity."""


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


class AtlasDTO(BaseDTO[Atlas], table=True):
    """DTO for Atlas entity with database mapping."""
    __tablename__ = "atlases"

    id: int = Field(primary_key=True)
    name: str
    labels: List[int] = Field(sa_type=JSON)

    @classmethod
    def from_entity(cls, entity: Atlas) -> AtlasDTO:
        return cls(id=entity.id, name=entity.name, labels=entity.labels)

    def to_entity(self) -> Atlas:
        return Atlas(id=self.id, name=self.name, labels=self.labels)


class SQLModelSQLiteDataGateway(DataBaseGateway[EntityType]):
    """SQLModel implementation of DataBaseGateway for SQLite."""

    def update(self, entity: EntityType) -> None:
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
            Center: CenterDTO,
            Atlas: AtlasDTO
        }

    def _get_model_class(self, entity_type: Type[EntityType]) -> Type[SQLModel]:
        """Get the SQLModel class corresponding to the entity type."""
        if entity_type not in self.entity_to_model_map:
            raise ValueError(f"No model mapping found for entity type {entity_type.__name__}")
        return self.entity_to_model_map[entity_type]

    @staticmethod
    def _entity_to_model(entity: EntityType) -> SQLModel:
        """Convert an entity to a SQLModel instance."""
        if isinstance(entity, Center):
            return CenterDTO.from_entity(entity)
        raise ValueError(f"No conversion implemented for entity type {type(entity).__name__}")

    @staticmethod
    def _model_to_entity(model: SQLModel, entity_type: Type[EntityType]) -> EntityType:
        """Convert a SQLModel instance to an entity."""
        if entity_type == Center and isinstance(model, CenterDTO):
            return model.to_entity()
        raise ValueError(f"No conversion implemented for model type {type(model).__name__}")

    def find_by_id(self, entity_type: Type[EntityType], id_value: Any) -> Optional[EntityType]:
        """Retrieve an entity by its ID."""
        model_class = self._get_model_class(entity_type)

        with Session(self.engine) as session:
            statement = select(model_class).where(model_class.id == id_value)
            model = session.exec(statement).first()

            if model is None:
                return None

            return self._model_to_entity(model, entity_type)

    def find_all(self, entity_type: Type[EntityType]) -> List[EntityType]:
        """Retrieve all entities of the given type."""
        model_class = self._get_model_class(entity_type)

        with Session(self.engine) as session:
            statement = select(model_class)
            models = session.exec(statement).all()

            # Convert models to entities
            entities = [self._model_to_entity(model, entity_type) for model in models]
            return entities

    def save(self, entity: EntityType) -> EntityType:
        """Save an entity (create or update)."""
        model = self._entity_to_model(entity)

        with Session(self.engine) as session:
            # Use merge to handle both insert and update
            model = session.merge(model)
            session.commit()
            session.refresh(model)

            return self._model_to_entity(model, type(entity))

    def delete(self, entity: EntityType) -> None:
        """Delete an entity."""
        model_class = self._get_model_class(type(entity))

        with Session(self.engine) as session:
            statement = select(model_class).where(model_class.id == entity.id)
            model = session.exec(statement).first()

            if model:
                session.delete(model)
                session.commit()
