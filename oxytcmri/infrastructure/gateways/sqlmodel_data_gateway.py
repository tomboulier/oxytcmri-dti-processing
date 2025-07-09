"""
A module using SQLModel ORM, with SQLite as the database engine.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Type, Any, Optional, List, Dict, TypeVar, Generic, cast, ClassVar

from sqlalchemy.exc import ProgrammingError, IntegrityError
from sqlmodel import SQLModel, Session, create_engine, select, Field, JSON, Relationship

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas, MRIExam, MRIData, AtlasSegmentation, DTIMap, DTIMetric, MRIExamId, \
    DTIAbnormalValues, RegionOfInterest, AbnormalValueType
from oxytcmri.domain.entities.subject import Subject, SubjectId
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValue, \
    StatisticsStrategies, StatisticStrategy
from oxytcmri.domain.use_cases.compute_lesions_volumes import BrainLesionsVolume
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData, NiftiAbnormalVoxelData
from oxytcmri.interface.repositories.database_repositories import DataBaseGateway, Entity

logger = logging.getLogger(__name__)

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
    DTI_ABNORMAL_VALUES = "dti_abnormal_values"


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
    source_dti_path: Optional[str] = Field(default=None)

    @classmethod
    def from_entity(cls, entity: MRIData) -> "MRIDataDTO":
        if not isinstance(entity.get_voxel_data(), NiftiVoxelData):
            raise ValueError(f"Unsupported voxel data type: {type(entity.voxel_data)}")

        # ensure voxel_data is of type NiftiVoxelData
        voxel_data = cast(NiftiVoxelData, entity.voxel_data)

        # default values
        data_type = MRIDataType.GENERIC
        atlas_id = None
        dti_metric = None
        source_dti_path = None

        if isinstance(entity, AtlasSegmentation):
            data_type = MRIDataType.ATLAS_SEGMENTATION
            atlas_id = entity.atlas.id
        elif isinstance(entity, DTIMap):
            data_type = MRIDataType.DTI_MAP
            dti_metric = str(entity.dti_metric)
        elif isinstance(entity, DTIAbnormalValues):
            data_type = MRIDataType.DTI_ABNORMAL_VALUES
            dti_metric = str(entity.source_dti_map.dti_metric)
            source_dti_path = entity.source_dti_map.voxel_data.get_nifti_absolute_path_string()

        return cls(id=f"{entity.mri_exam_id}_{entity.name}",
                   mri_exam_id=str(entity.mri_exam_id),
                   name=entity.name,
                   nifti_data_path=voxel_data.get_nifti_absolute_path_string(),
                   data_type=data_type,
                   atlas_id=atlas_id,
                   dti_metric=dti_metric,
                   source_dti_path=source_dti_path)

    def to_entity(self) -> MRIData:
        if self.data_type == MRIDataType.ATLAS_SEGMENTATION:
            return AtlasSegmentation(mri_exam_id=MRIExamId(self.mri_exam_id),
                                     voxel_data=NiftiVoxelData(Path(self.nifti_data_path)),
                                     atlas=self.atlas.to_entity())
        elif self.data_type == MRIDataType.DTI_MAP:
            return DTIMap(mri_exam_id=MRIExamId(self.mri_exam_id),
                          voxel_data=NiftiVoxelData(Path(self.nifti_data_path)),
                          dti_metric=self.dti_metric)
        elif self.data_type == MRIDataType.DTI_ABNORMAL_VALUES:
            source_voxel_data = NiftiVoxelData(Path(self.source_dti_path))
            source_dti_map = DTIMap(mri_exam_id=MRIExamId(self.mri_exam_id),
                                    voxel_data=source_voxel_data,
                                    dti_metric=self.dti_metric)
            abnormal_voxel_data = NiftiAbnormalVoxelData(
                nifti_path=Path(self.nifti_data_path),
                source_voxel_data=source_voxel_data
            )
            return DTIAbnormalValues(mri_exam_id=MRIExamId(self.mri_exam_id),
                                     voxel_data=abnormal_voxel_data,
                                     source_dti_map=source_dti_map, )
        return MRIData(mri_exam_id=MRIExamId(self.mri_exam_id),
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
        return cls(id=str(entity.id), subject_id=str(entity.subject_id))

    def to_entity(self) -> MRIExam:
        return MRIExam.from_string_exam_id(
            exam_id=self.id,
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


class RegionOfInterestDTO(BaseDTO[RegionOfInterest], table=True):
    """DTO for RegionOfInterest entity with database mapping."""
    __tablename__ = "regions_of_interest"

    name: str = Field(primary_key=True)
    atlas_id: int = Field(foreign_key="atlases.id")
    atlas: AtlasDTO = Relationship()
    atlas_labels: List[int] = Field(sa_type=JSON, default=[])

    @classmethod
    def from_entity(cls, entity: EntityType) -> "RegionOfInterestDTO":
        if entity.name is None:
            raise ValueError(f"Region of interest {entity} must have a name in order to be stored in the database.")

        return cls(
            name=entity.name,
            atlas_id=entity.atlas.id,
            atlas_labels=entity.labels
        )

    def to_entity(self) -> RegionOfInterest:
        return RegionOfInterest(
            name=self.name,
            atlas=self.atlas.to_entity(),
            labels=self.atlas_labels
        )


class BrainLesionsVolumeDTO(BaseDTO[BrainLesionsVolume], table=True):
    """DTO for BrainLesionsVolume entity with database mapping."""
    __tablename__ = "brain_lesions_volumes"
    WHOLE_BRAIN_ROI_NAME: ClassVar[str] = "Whole Brain"

    mri_exam_id: str = Field(foreign_key="mri_exams.id", primary_key=True)
    mri_exam: MRIExamDTO = Relationship()
    dti_metric: str = Field(primary_key=True)
    region_of_interest_name: Optional[str] = Field(default=WHOLE_BRAIN_ROI_NAME, foreign_key="regions_of_interest.name", primary_key=True)
    region_of_interest: RegionOfInterestDTO = Relationship()
    abnormal_value_type: str = Field(primary_key=True)
    value_ml: float

    @classmethod
    def from_entity(cls, entity: BrainLesionsVolume) -> "BrainLesionsVolumeDTO":
        return cls(
            mri_exam_id=str(entity.mri_exam_id),
            dti_metric=str(entity.dti_metric),
            region_of_interest_name=str(entity.region_of_interest.id) if entity.region_of_interest else None,
            abnormal_value_type=str(entity.abnormal_value_type),
            value_ml=entity.value_ml
        )

    def to_entity(self) -> BrainLesionsVolume:
        abnormal_type = {
            "high": AbnormalValueType.HIGH,
            "low": AbnormalValueType.LOW
        }[self.abnormal_value_type]

        return BrainLesionsVolume(
            mri_exam_id=MRIExamId(self.mri_exam_id),
            dti_metric=DTIMetric.from_acronym(self.dti_metric),
            region_of_interest=self.region_of_interest.to_entity() if self.region_of_interest else None,
            abnormal_value_type=abnormal_type,
            value_ml=self.value_ml
        )


class SQLModelSQLiteDataGateway(DataBaseGateway[EntityType]):
    """SQLModel implementation of DataBaseGateway for SQLite."""

    def update(self, entity: EntityType) -> None:
        raise NotImplementedError("Update method is not implemented yet.")  # pragma: no cover

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
        self.entity_to_model_map: Dict[Type, Type[BaseDTO]] = {
            Center: CenterDTO,
            Subject: SubjectDTO,
            Atlas: AtlasDTO,
            MRIExam: MRIExamDTO,
            MRIData: MRIDataDTO,
            AtlasSegmentation: MRIDataDTO,
            DTIAbnormalValues: MRIDataDTO,
            DTIMap: MRIDataDTO,
            NormativeValue: NormativeValuesDTO,
            RegionOfInterest: RegionOfInterestDTO,
            BrainLesionsVolume: BrainLesionsVolumeDTO,
        }

        # Define type converters for different entity types
        self.type_converters = {
            SubjectId: lambda x: str(x),
            MRIExamId: lambda x: str(x),
            DTIMetric: lambda x: str(x),
            StatisticStrategy: lambda x: x.name,
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
        converted_id_value = self._convert_id_value(id_value)
        try:
            with Session(self.engine) as session:
                statement = select(model_class).where(model_class.id == converted_id_value)
                model = session.exec(statement).first()

                if model is None:
                    return None

                return self._model_to_entity(model, entity_type)
        except ProgrammingError as programming_error:
            raise RuntimeError(f"Error executing query: {statement} "
                               f"when trying to find entity {entity_type} "
                               f"with id {id_value}") \
                from programming_error

    def _convert_id_value(self, id_value: Any) -> Any:
        """
        Convert the ID value to the appropriate type for the database.
        """
        if type(id_value) in self.type_converters:
            return self.type_converters[type(id_value)](id_value)
        return id_value

    def _prepare_filters_for_query(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Convert filter values to SQLite-compatible types.
        Uses a mapping system for different entity types.
        """
        processed_filters = {}

        for key, value in filters.items():
            # Handle special case: None value for region_of_interest in BrainLesionsVolumeDTO
            if key == 'region_of_interest' and value is None:
                processed_filters['region_of_interest_name'] = BrainLesionsVolumeDTO.WHOLE_BRAIN_ROI_NAME
                continue
            # Check if we have a specific converter for this type
            value_type = type(value)
            if value_type in self.type_converters:
                processed_filters[key] = self.type_converters[value_type](value)
            # Generic handling for other types
            elif isinstance(value, Enum):
                processed_filters[key] = str(value)
            else:
                processed_filters[key] = value

        return processed_filters

    def find_by_filters(self, entity_type: Type[Entity], filters: dict[str, Any]) -> Optional[Entity]:
        """Retrieve an entity by filters."""
        model_class = self._get_model_class(entity_type)

        with Session(self.engine) as session:
            # Start with a base query
            query = select(model_class)

            # Process filters to make them compatible with SQLite
            processed_filters = self._prepare_filters_for_query(filters)

            # Apply filters to the query
            for key, value in processed_filters.items():
                if not hasattr(model_class, key):
                    continue

                attr = getattr(model_class, key)

                # If the attribute is a relationship, we need to join the related model
                if hasattr(attr, 'property') and hasattr(attr.property, 'mapper'):
                    related_model = attr.property.mapper.class_
                    # Perform a join
                    query = query.join(related_model)

                    # Obtain the primary key name of the related model
                    primary_key_column = related_model.__table__.primary_key.columns.values()[0]
                    primary_key_name = primary_key_column.name

                    # Filter by the primary key of the related model
                    if hasattr(value, primary_key_name):
                        pk_value = getattr(value, primary_key_name)
                        query = query.where(getattr(related_model, primary_key_name) == pk_value)
                    else:
                        raise ValueError(f"Value {value} does not have the primary key {primary_key_name} "
                                         f"for related model {related_model.__name__}")
                else:
                    # When the attribute is not a relationship, we can filter directly
                    query = query.where(attr == value)

            model = session.exec(query).first()

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
        self.save_list([entity])

    def save_list(self, entities: List[EntityType]) -> None:
        """Save a list of entities to the database in a single transaction."""
        if not entities:
            return

        try:
            with Session(self.engine) as session:
                for entity in entities:
                    model = self._entity_to_model(entity)
                    session.merge(model)
                session.commit()
        except IntegrityError as integrity_error:
            # Handle integrity errors (e.g., unique constraint violations)
            # session.rollback()
            raise RuntimeError(
                f"Integrity error while saving entities {entities}: {integrity_error}") from integrity_error

    def delete(self, entity: EntityType) -> None:
        """Delete an entity."""
        model_class = self._get_model_class(type(entity))

        with Session(self.engine) as session:
            statement = select(model_class).where(model_class.id == entity.id)
            model = session.exec(statement).first()

            if model:
                session.delete(model)
                session.commit()
