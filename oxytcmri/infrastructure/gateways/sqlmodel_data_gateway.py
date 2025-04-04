from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Type, Any, Optional, List, Dict, TypeVar, Generic, cast

from sqlmodel import SQLModel, Session, create_engine, select, Field, JSON, Relationship

from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas, MRIExam, MRIData, AtlasSegmentation, DTIMap, DTIMetric
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValue, \
    StatisticsStrategies
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData
from oxytcmri.interface.repositories.database_repositories import DataBaseGateway

# Define SQLModel models for entities
EntityType = TypeVar('EntityType')  # Generic type variable for entities


class BaseDTO(SQLModel, Generic[EntityType], ABC):
    """Base class for all Data Transfer Objects (DTO) with entity conversion methods."""

    @classmethod
    @abstractmethod
    def from_entity(cls, entity: EntityType) -> "BaseDTO[EntityType]":
        """Create a DTO from a domain entity."""

    @abstractmethod
    def to_entity(self) -> EntityType:
        """Convert the DTO to a domain entity."""


class SubjectDTO(BaseDTO[Subject], table=True):
    """DTO for Subject entity with database mapping."""
    __tablename__ = "subjects"

    id: str = Field(primary_key=True)
    subject_type: str
    center_id: int

    @classmethod
    def from_entity(cls, entity: Subject) -> "SubjectDTO":
        return cls(id=str(entity.id), subject_type=entity.subject_type, center_id=entity.center_id)

    def to_entity(self) -> Subject:
        return Subject.from_string_id(self.id)


class AtlasDTO(BaseDTO[Atlas], table=True):
    """DTO for Atlas entity with database mapping."""
    __tablename__ = "atlases"

    id: int = Field(primary_key=True)
    name: str
    labels: List[int] = Field(sa_type=JSON)

    @classmethod
    def from_entity(cls, entity: Atlas) -> "AtlasDTO":
        return cls(id=entity.id, name=entity.name, labels=entity.labels)

    def to_entity(self) -> Atlas:
        return Atlas(id=self.id, name=self.name, labels=self.labels)


class MRIDataType(str, Enum):
    """Enum for mapping MRIData subtypes."""
    GENERIC = "generic"
    ATLAS_SEGMENTATION = "atlas_segmentation"
    DTI_MAP = "dti_map"


class MRIDataDTO(BaseDTO[MRIData], table=True):
    """DTO for MRIData entity with database mapping.

    Warnings
    --------
    This class assumes that the voxel data is of type NiftiVoxelData.

    Attributes
    ----------
    id : str
        Unique identifier (primary key) of the MRI data
    mri_exam_id  : str
        Unique identifier of the MRI exam (foreign key)
    name : str
        Name of the MRI data
    nifti_data_path : str
        Path to the Nifti file
    """
    __tablename__ = "mri_data"

    id: str = Field(primary_key=True)
    mri_exam_id: str = Field(foreign_key="mri_exams.id")
    mri_exam: "MRIExamDTO" = Relationship(back_populates="mri_data")
    name: str
    nifti_data_path: str
    data_type: MRIDataType = Field(default=MRIDataType.GENERIC)

    # optional fields (when data_type is not generic)
    atlas_id: Optional[int] = Field(default=None, foreign_key="atlases.id")
    atlas: Optional[AtlasDTO] = Relationship()
    dti_metric: Optional[DTIMetric] = Field(default=None)

    @classmethod
    def from_entity(cls, entity: MRIData) -> "MRIDataDTO":
        if type(entity.get_voxel_data()) != NiftiVoxelData:
            raise ValueError(f"Unsupported voxel data type: {type(entity.voxel_data)}")

        # ensure voxel_data is of type NiftiVoxelData
        voxel_data = cast(NiftiVoxelData, entity.voxel_data)

        # default values
        data_type = MRIDataType.GENERIC
        atlas_id = None
        dti_metric = None

        if isinstance(entity, AtlasSegmentation):
            data_type = MRIDataType.ATLAS_SEGMENTATION
            atlas_id = entity.atlas.id
        elif isinstance(entity, DTIMap):
            data_type = MRIDataType.DTI_MAP
            dti_metric = str(entity.dti_metric)

        return cls(id=entity.id,
                   mri_exam_id=str(entity.mri_exam_id),
                   name=entity.name,
                   nifti_data_path=voxel_data.get_nifti_path_string(),
                   data_type=data_type,
                   atlas_id=atlas_id,
                   dti_metric=dti_metric)

    def to_entity(self) -> MRIData:
        if self.data_type == MRIDataType.ATLAS_SEGMENTATION:
            return AtlasSegmentation(id=self.id,
                                     name=self.name,
                                     voxel_data=NiftiVoxelData(Path(self.nifti_data_path)),
                                     atlas=self.atlas.to_entity())
        elif self.data_type == MRIDataType.DTI_MAP:
            return DTIMap(id=self.id,
                          name=self.name,
                          voxel_data=NiftiVoxelData(Path(self.nifti_data_path)),
                          dti_metric=self.dti_metric)
        return MRIData(id=self.id,
                       name=self.name,
                       voxel_data=NiftiVoxelData(Path(self.nifti_data_path)))


class MRIExamDTO(BaseDTO[MRIExam], table=True):
    """DTO for MRIExam entity with database mapping."""
    __tablename__ = "mri_exams"

    id: str = Field(primary_key=True)
    subject_id: str = Field(foreign_key="subjects.id")
    mri_data: list[MRIDataDTO] = Relationship(back_populates="mri_exam")

    @classmethod
    def from_entity(cls, entity: MRIExam) -> "MRIExamDTO":
        return cls(id=str(entity.id), subject_id=entity.subject_id)

    def to_entity(self) -> MRIExam:
        return MRIExam(
            id=self.id,
            subject_id=self.subject_id,
            data=[MRIDataDTO.to_entity(mri_data) for mri_data in self.mri_data]
        )


class CenterDTO(BaseDTO[Center], table=True):
    """DTO for Center entity with database mapping."""
    __tablename__ = "centers"

    id: int = Field(primary_key=True)
    name: str

    @classmethod
    def from_entity(cls, entity: Center) -> "CenterDTO":
        return cls(id=entity.id, name=entity.name)

    def to_entity(self) -> Center:
        return Center(id=self.id, name=self.name)


class NormativeValuesDTO(BaseDTO[NormativeValue], table=True):
    """DTO for NormativeValues entity with database mapping.

    Attributes
    ----------
    id : int
        Unique identifier (primary key) of the normative value
    value : float
        Value of the normative value
    center_id : int
        Unique identifier of the center (foreign key)
    center : CenterDTO
        Center of the normative value
    dti_metric : DTIMetric
        DTI metric of the normative value
    atlas_id : int
        Unique identifier of the atlas (foreign key)
    atlas_label : int
        Label of the atlas
    atlas : AtlasDTO
        Atlas of the normative value
    statistic_strategy : StatisticsStrategies
        Statistic strategy of the normative value
    """
    __tablename__ = "DTI_normative_values"

    id: int = Field(default=None, primary_key=True)
    value: float
    # Center ID is a foreign key to the centers table
    center_id: int = Field(foreign_key="centers.id")
    center: CenterDTO = Relationship()
    # DTI metric is a string representation of the DTIMetric enum
    dti_metric: str
    # Atlas ID is a foreign key to the atlases table
    atlas_id: int = Field(foreign_key="atlases.id")
    atlas_label: int
    atlas: AtlasDTO = Relationship()
    # Statistic strategy is a string representation of the StatisticsStrategies enum
    statistic_strategy: str

    @classmethod
    def from_entity(cls, entity: EntityType) -> "NormativeValuesDTO":
        return cls(
                   center_id=entity.center.id,
                   dti_metric=str(entity.dti_metric),
                   atlas_id=entity.atlas.id,
                   atlas_label=entity.atlas_label,
                   statistic_strategy=entity.statistic_strategy.name,
                   value=entity.value
                   )

    def to_entity(self) -> NormativeValue:
        return NormativeValue(center=self.center.to_entity(),
                              dti_metric=DTIMetric.from_acronym(self.dti_metric),
                              atlas=self.atlas.to_entity(),
                              atlas_label=self.atlas_label,
                              statistic_strategy=StatisticsStrategies.get_by_name(self.statistic_strategy),
                              value=self.value)


class SQLModelSQLiteDataGateway(DataBaseGateway[EntityType]):
    """SQLModel implementation of DataBaseGateway for SQLite."""

    def update(self, entity: EntityType) -> None:
        raise NotImplementedError("Update method is not implemented yet.")

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
            Subject: SubjectDTO,
            Atlas: AtlasDTO,
            MRIExam: MRIExamDTO,
            MRIData: MRIDataDTO,
            AtlasSegmentation: MRIDataDTO,
            DTIMap: MRIDataDTO,
            NormativeValue: NormativeValuesDTO,
        }

    def _get_model_class(self, entity_type: Type[EntityType]) -> Type[SQLModel]:
        """Get the SQLModel class corresponding to the entity type."""
        if entity_type not in self.entity_to_model_map:
            raise ValueError(f"No model mapping found for entity type {entity_type.__name__}")
        return self.entity_to_model_map[entity_type]

    def _entity_to_model(self, entity: EntityType) -> SQLModel:
        """Convert an entity to a SQLModel instance."""
        entity_type = type(entity)
        if entity_type in self.entity_to_model_map:
            model_class = self.entity_to_model_map[entity_type]
            return model_class.from_entity(entity)
        raise ValueError(f"No conversion implemented for entity type {entity_type.__name__}")

    def _model_to_entity(self, model: SQLModel, entity_type: Type[EntityType]) -> EntityType:
        """Convert a SQLModel instance to an entity."""
        if entity_type in self.entity_to_model_map:
            model_class = self.entity_to_model_map[entity_type]
            return model_class.to_entity(model)
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

    def save(self, entity: EntityType) -> None:
        """Save an entity (create or update)."""
        model = self._entity_to_model(entity)

        with Session(self.engine) as session:
            # Use merge to handle both insert and update
            model = session.merge(model)
            session.commit()
            session.refresh(model)

    def delete(self, entity: EntityType) -> None:
        """Delete an entity."""
        model_class = self._get_model_class(type(entity))

        with Session(self.engine) as session:
            statement = select(model_class).where(model_class.id == entity.id)
            model = session.exec(statement).first()

            if model:
                session.delete(model)
                session.commit()
