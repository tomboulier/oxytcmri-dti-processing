from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Type, Any, List, Callable

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas, MRIExam, DTIMetric, MRIExamId, RegionOfInterest
from oxytcmri.domain.entities.subject import Subject, SubjectId
from oxytcmri.domain.ports.repositories import CenterRepository, AtlasRepository, MRIExamRepository, SubjectRepository, \
    Repository, RepositoriesRegistry, EntityNotFoundException, RegionOfInterestRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue, \
    StatisticStrategy
from oxytcmri.domain.use_cases.compute_lesions_volumes import BrainLesionsVolume, BrainLesionsVolumeRepository

Entity = TypeVar('Entity')
EntityIdentifier = TypeVar('EntityIdentifier')


class DataBaseGateway(Generic[Entity], ABC):
    """Abstract base class for database access to repositories."""

    @abstractmethod
    def find_by_id(self, entity_type: Type[Entity], id_value: EntityIdentifier) -> Optional[Entity]:
        """Find an entity by its ID."""

    @abstractmethod
    def find_by_filters(self, entity_type: Type[Entity], filters: dict[str, Any]) -> Optional[Entity]:
        """Find an entity by filters. Those filters are the attributes of the entity,
        and are modeled as a dictionary."""

    @abstractmethod
    def find_all(self, entity_type: Type[Entity]) -> list[Entity]:
        """Find all entities of a given type."""

    @abstractmethod
    def save(self, entity: Entity) -> None:
        """Save an entity to the database."""

    @abstractmethod
    def save_list(self, entities: List[Entity]) -> None:
        """Save a list of entities to the database."""

    @abstractmethod
    def delete(self, entity: Entity) -> None:
        """Delete an entity from the database."""

    @abstractmethod
    def update(self, entity: Entity) -> None:
        """Update an entity in the database."""

    def delete_all(self, entity_type: Type[Entity]) -> None:
        """Delete all entities of a given type from the database."""
        for entity in self.find_all(entity_type):
            self.delete(entity)


class DataBaseRepository(Repository[Entity, EntityIdentifier], Generic[Entity, EntityIdentifier]):
    """
    Base class for database access to repositories.
    """

    def __init__(self,
                 data_gateway: DataBaseGateway,
                 entity_type: Type[Entity],
                 id_extractor: Callable[[Entity], EntityIdentifier]):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        entity_type : Type[Entity]
            The type of entity managed by this repository.
        id_extractor : Callable[[Entity], EntityIdentifier]
            A function to extract the ID from an entity.
        """
        self.data_gateway = data_gateway
        self.entity_type = entity_type
        self._get_id = id_extractor

    def exists(self, entity: Entity) -> bool:
        entity_id = self._get_id(entity)
        return self.data_gateway.find_by_id(entity_type=self.entity_type, id_value=entity_id) is not None

    def find_by_id(self, entity_id: EntityIdentifier) -> Optional[Entity]:
        return self.data_gateway.find_by_id(entity_type=self.entity_type,
                                            id_value=entity_id)

    def list_all(self) -> List[Entity]:
        return self.data_gateway.find_all(self.entity_type)

    def save(self, entity: Entity) -> None:
        self.data_gateway.save(entity)

    def delete(self, entity: Entity) -> None:
        self.data_gateway.delete(entity)


class DataBaseCenterRepository(CenterRepository, DataBaseRepository[Center, int]):
    """Persistence layer for Center entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        super().__init__(data_gateway, Center, lambda center: center.id)


class DataBaseAtlasRepository(AtlasRepository, DataBaseRepository[Atlas, int]):
    """Persistence layer for Atlas entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        super().__init__(data_gateway=data_gateway,
                         entity_type=Atlas,
                         id_extractor=lambda atlas: atlas.id)


class DataBaseRegionOfInterestRepository(RegionOfInterestRepository, DataBaseRepository[RegionOfInterest, str]):
    """Persistence layer for RegionOfInterest entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        super().__init__(data_gateway=data_gateway,
                         entity_type=RegionOfInterest,
                         id_extractor=lambda roi: roi.name)


class DataBaseBrainLesionsVolumeRepository(BrainLesionsVolumeRepository):
    """Persistence layer for BrainLesionsVolume entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        self.data_gateway = data_gateway

    def exists(self, entity: BrainLesionsVolume) -> bool:
        """
        Check if a BrainLesionsVolume entity exists in the database.

        Parameters
        ----------
        entity : BrainLesionsVolume
            The BrainLesionsVolume entity to check for existence.

        Returns
        -------
        bool
            True if the entity exists, False otherwise.
        """
        found_brain_lesions_volume = self.data_gateway.find_by_filters(
            entity_type=BrainLesionsVolume,
            filters={
                'mri_exam_id': entity.mri_exam_id,
                'dti_metric': entity.dti_metric,
                'region_of_interest': entity.region_of_interest,
                'abnormal_value_type': entity.abnormal_value_type
            }
        )
        return found_brain_lesions_volume is not None

    def find_by_id(self, entity_id: EntityIdentifier) -> Optional[Entity]:
        raise NotImplementedError("find_by_id is not implemented in this Repository")

    def list_all(self) -> List[BrainLesionsVolume]:
        return self.data_gateway.find_all(BrainLesionsVolume)

    def save(self, brain_lesions_volume: BrainLesionsVolume) -> None:
        self.data_gateway.save(brain_lesions_volume)

    def delete(self, entity: Entity) -> None:
        """
        Delete a BrainLesionsVolume entity from the database.

        Parameters
        ----------
        entity : BrainLesionsVolume
            The BrainLesionsVolume entity to delete.
        """
        self.data_gateway.delete(entity)


class DataBaseMRIExamRepository(MRIExamRepository, DataBaseRepository[MRIExam, MRIExamId]):
    """Persistence layer for MRIExam entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        super().__init__(
            data_gateway=data_gateway,
            entity_type=MRIExam,
            id_extractor=lambda mri_exam: mri_exam.id
        )

    def get_exam_for_subject(self, subject: Subject) -> MRIExam:
        # Retrieve all MRIExam entities from the database
        all_mri_exams = self.data_gateway.find_all(MRIExam)
        for mri_exam in all_mri_exams:
            if mri_exam.subject_id == subject.id:
                return mri_exam

        # If no MRIExam is found for the given subject_id, raise an exception
        raise LookupError(f"MRIExam with subject_id '{subject_id}' not found.")

    def save(self, mri_exam: MRIExam) -> None:
        """
        Save an MRIExam entity to the database, as well as all associated MRIData entities.

        Parameters
        ----------
        mri_exam : MRIExam
            The MRIExam entity to save.
        """
        self.data_gateway.save(mri_exam)
        for mri_data in mri_exam.get_all_mri_data():
            self.data_gateway.save(mri_data)


class DataBaseSubjectRepository(SubjectRepository, DataBaseRepository[Subject, SubjectId]):
    """Persistence layer for Subject entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        super().__init__(
            data_gateway=data_gateway,
            entity_type=Subject,
            id_extractor=lambda subject: subject.id
        )


class DataBaseDTINormativeValuesRepository(NormativeValueRepository):
    """Persistence layer for NormativeValue entities using a database gateway."""

    def __init__(self, data_gateway: DataBaseGateway):
        """
        Initialize the repository with a database gateway.

        Parameters
        ----------
        data_gateway : DataBaseGateway
            The database gateway used for accessing the database.
        """
        self.data_gateway = data_gateway

    def save(self, normative_value: NormativeValue) -> None:
        self.data_gateway.save(normative_value)

    def save_list(self, normative_values_list: list[NormativeValue]) -> None:
        self.data_gateway.save_list(normative_values_list)

    def list_all(self) -> List[NormativeValue]:
        return self.data_gateway.find_all(NormativeValue)

    def exists(self,
               center: Center,
               dti_metric: DTIMetric,
               atlas: Atlas,
               atlas_label: int,
               statistic_strategy: StatisticStrategy
               ) -> bool:
        normative_values = self.data_gateway.find_by_filters(
            NormativeValue,
            filters={
                'center': center,
                'dti_metric': dti_metric,
                'atlas': atlas,
                'atlas_label': atlas_label,
                'statistic_strategy': statistic_strategy
            }
        )
        return normative_values is not None

    def get_by_parameters(self,
                          center: Center,
                          dti_metric: DTIMetric,
                          atlas: Atlas,
                          atlas_label: int,
                          statistic_strategy: StatisticStrategy
                          ) -> NormativeValue:
        normative_value = self.data_gateway.find_by_filters(
            NormativeValue,
            filters={
                'center': center,
                'dti_metric': dti_metric,
                'atlas': atlas,
                'atlas_label': atlas_label,
                'statistic_strategy': statistic_strategy
            }
        )
        if normative_value is None:
            raise EntityNotFoundException(message=f"NormativeValue with parameters "
                                                  f"center = {center}; "
                                                  f"DTI metric = {dti_metric}; "
                                                  f"atlas = {atlas}; "
                                                  f"atlas label = {atlas_label}; "
                                                  f"statistic strategy = {statistic_strategy} not found"
                                                  f"in repository {self.__class__.__name__}.",
                                          repository=self)
        return normative_value

    def find_by_id(self, entity_id: int) -> Optional[NormativeValue]:
        raise NotImplementedError("find_by_id is not implemented in this Repository")  # pragma: no cover

    def list_all(self) -> List[NormativeValue]:
        return self.data_gateway.find_all(NormativeValue)

    def delete(self, entity: NormativeValue) -> None:
        self.data_gateway.delete(entity)


class DataBaseRepositoriesRegistry(RepositoriesRegistry):
    def __init__(self, persistence_gateway: DataBaseGateway):
        self._repositories = {
            Center: DataBaseCenterRepository(persistence_gateway),
            Subject: DataBaseSubjectRepository(persistence_gateway),
            MRIExam: DataBaseMRIExamRepository(persistence_gateway),
            Atlas: DataBaseAtlasRepository(persistence_gateway),
            NormativeValue: DataBaseDTINormativeValuesRepository(persistence_gateway),
            RegionOfInterest: DataBaseRegionOfInterestRepository(persistence_gateway),
            BrainLesionsVolume: DataBaseBrainLesionsVolumeRepository(persistence_gateway),
        }

    def get_repository(self, entity_type: Type[Entity]) -> "Repository[Entity, Any]":
        repository = self._repositories.get(entity_type)
        if repository is None:
            raise ValueError(f"No repository registered for entity type: {entity_type}")
        return repository

    def list_all_repositories(self) -> List[Repository[Entity, Any]]:
        return list(self._repositories.values())
