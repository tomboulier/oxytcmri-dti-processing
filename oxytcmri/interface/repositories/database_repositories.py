from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Type, Any, List
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas, MRIExam, DTIMetric
from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.ports.repositories import CenterRepository, AtlasRepository, MRIExamRepository, SubjectRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue, \
    StatisticStrategy

T = TypeVar('T')


class DataBaseGateway(Generic[T], ABC):
    """Abstract base class for database access to repositories."""

    @abstractmethod
    def find_by_id(self, entity_type: Type[T], id_value: Any) -> Optional[T]:
        """Find an entity by its ID."""

    @abstractmethod
    def find_by_filters(self, entity_type: Type[T], filters: dict[str, Any]) -> Optional[T]:
        """Find an entity by filters. Those filters are the attributes of the entity,
        and are modeled as a dictionary."""

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

    def get_center_by_id(self, center_id: int) -> Center:
        return self.data_gateway.find_by_id(Center, center_id)


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
        # Retrieve all MRIExam entities from the database
        all_mri_exams = self.data_gateway.find_all(MRIExam)
        for mri_exam in all_mri_exams:
            if mri_exam.subject_id == subject_id:
                return mri_exam

        # If no MRIExam is found for the given subject_id, raise an exception
        raise LookupError(f"MRIExam with subject_id '{subject_id}' not found.")

    def save(self, mri_exam: MRIExam) -> None:
        self.data_gateway.save(mri_exam)
        for mri_data in mri_exam.get_all_mri_data():
            self.data_gateway.save(mri_data)


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

    def batch_save(self, normative_values_list: list[NormativeValue]) -> None:
        self.data_gateway.save_list(normative_values_list)

    def get_all(self) -> List[NormativeValue]:
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
