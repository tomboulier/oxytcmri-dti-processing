from __future__ import annotations

from typing import List, Optional, Tuple, Callable, Dict, Generic, Type, Any

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import (
    DTIMetric,
    Atlas,
    MRIExam,
    VoxelData, AtlasSegmentation, DTIMap, T, MRIExamId, MRIData, Mask,
)
from oxytcmri.domain.entities.subject import Subject, SubjectType, SubjectId
from oxytcmri.domain.ports.repositories import (
    SubjectRepository,
    MRIExamRepository,
    CenterRepository,
    AtlasRepository,
    Repository,
    Entity,
    EntityIdentifier,
    RepositoriesRegistry, EntityNotFoundException,
)
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue, \
    StatisticStrategy
from oxytcmri.interface.repositories.database_repositories import DataBaseGateway


class InMemoryRepository(Repository[Entity, EntityIdentifier], Generic[Entity, EntityIdentifier]):
    """
    Generic in-memory implementation of the Repository interface.
    """

    def __init__(self, id_extractor: Callable[[Entity], EntityIdentifier]):
        """
        Initialize the in-memory repository.

        Parameters
        ----------
        id_extractor : Callable[[Entity], EntityIdentifier]
            A function to extract the ID from an entity.
        """
        self._store: Dict[EntityIdentifier, Entity] = {}
        self._get_id = id_extractor

    def find_by_id(self, entity_id: EntityIdentifier) -> Optional[Entity]:
        return self._store.get(entity_id)

    def list_all(self) -> List[Entity]:
        return list(self._store.values())

    def save(self, entity: Entity) -> None:
        self._store[self._get_id(entity)] = entity

    def delete(self, entity: Entity) -> None:
        key = self._get_id(entity)
        if key in self._store:
            del self._store[key]


class MockCenterRepository(InMemoryRepository[Center, int], CenterRepository):
    """
    Mock implementation of the CenterRepository interface, with in-memory storage.
    """

    def __init__(self, centers: Optional[List[Center]] = None):
        """
        Initialize the in-memory repository with a list of centers.

        By default, this list contains 3 centers, named "Brest", "New-York", "Katmandou".
        """
        super().__init__(id_extractor=lambda center: center.id)
        if centers is None:
            self.save_list([
                Center(id=1, name="Brest"),
                Center(id=2, name="New-York"),
                Center(id=3, name="Katmandou"),
            ])


# atlases
class MockAtlasRepository(InMemoryRepository[Atlas, int], AtlasRepository):
    """
    Mock implementation of the AtlasRepository using in-memory storage.
    """

    def __init__(self, atlases: Optional[List[Atlas]] = None):
        super().__init__(id_extractor=lambda atlas: atlas.id)
        if atlases is None:
            atlases = [
                Atlas(id=2, labels=[29, 33, 62], name="Atlas 2"),
                Atlas(id=4, labels=[29, 33, 59, 60, 62], name="Atlas 4"),
            ]
        for atlas in atlases:
            self.save(atlas)


class MockInMemorySubjectRepository(InMemoryRepository[Subject, str], SubjectRepository):
    """
    Mock implementation of the SubjectRepository interface, based on in-memory storage.
    """

    def __init__(self, subject_ids: Optional[List[str]] = None):
        super().__init__(id_extractor=lambda subj: str(subj.id))

        if subject_ids is None:
            subject_ids = ["01-01-P", "01-02-V", "02-01-V"]

        subjects = self.build_subjects_from_strings(subject_ids)
        for subject in subjects:
            self.save(subject)

    @staticmethod
    def build_subjects_from_strings(subject_ids: List[str]) -> List[Subject]:
        """
        Build a list of Subject objects from their string IDs.
        """
        return [Subject.from_string_id(id_str) for id_str in subject_ids]

    def find_subjects_by_center(
            self, center: Center, subject_type: Optional[SubjectType] = None
    ) -> List[Subject]:
        return [
            subject for subject in self.list_all()
            if subject.center_id == center.id and (subject_type is None or subject.subject_type == subject_type)
        ]


class MockMaskData(Mask):
    """Mock for boolean masks."""

    def __init__(self, boolean_value: bool = True):
        self.boolean_value = boolean_value

    def get_value_at(self, x: int, y: int, z: int) -> bool:
        return self.boolean_value

    @staticmethod
    def get_dimensions() -> Tuple[int, int, int]:
        return 10, 10, 10

    @staticmethod
    def get_voxel_volume_in_ml() -> float:
        return 8.0

    def filter_values(self, condition: Callable[[T], bool]) -> VoxelData[bool]:
        raise NotImplementedError("filter_values is not implemented in MockMaskData")


class MockVoxelData(VoxelData[float]):
    """Mock for voxel data."""

    def __init__(self):
        self.value = 0.5
        # Test values for apply_mask
        self.test_values = [0.1, 0.2, 0.3]

    def get_value_at(self, x: int, y: int, z: int) -> float:
        return self.value

    def set_value_at(self, x: int, y: int, z: int, value: float) -> None:
        """Set the value of a voxel at a specific position."""
        self.value = value

    def get_dimensions(self) -> Tuple[int, int, int]:
        return 10, 10, 10

    def get_voxel_volume_in_ml(self) -> float:
        return 8.0

    def apply_mask(self, mask: "MockMaskData") -> List[float]:
        """Apply a mask to filter voxel data."""
        return self.test_values

    def filter_values(self, condition: Callable[[float], bool]) -> VoxelData[bool]:
        return MockMaskData(condition(self.value))


class MockSegmentationData(VoxelData[int]):
    """Mock for VoxelData[int]."""

    def __init__(self):
        self.value = 3
        # Test values for apply_mask
        self.test_values = [0.1, 0.2, 0.3]

    def get_value_at(self, x: int, y: int, z: int) -> int:
        return self.value

    def set_value_at(self, x: int, y: int, z: int, value: int) -> None:
        raise NotImplementedError("set_value_at is not implemented in MockSegmentationData")

    def get_dimensions(self) -> tuple[int, int, int]:
        return 10, 10, 10

    def get_voxel_volume_in_ml(self) -> float:
        return 8.0

    def filter_values(self, condition: Callable[[int], bool]) -> VoxelData[bool]:
        return MockMaskData(condition(self.value))


class MockSyntheticMRIExamRepository(MRIExamRepository):
    """
    Generates synthetic MRIExam objects on-the-fly for any subject_id.
    """

    def __init__(self, atlases: List[Atlas]):
        self.atlases = atlases

    def get_exam_for_subject(self, subject: Subject) -> MRIExam:
        synthetic_mri_exam_id = MRIExamId(str(subject.id))
        return self._build_synthetic_mri_exam_from_id(synthetic_mri_exam_id)

    def _build_synthetic_mri_exam_from_id(self, mri_exam_id: MRIExamId) -> MRIExam:
        """
        Build a synthetic MRIExam object from its ID.
        """
        return MRIExam(
            id=mri_exam_id,
            subject_id=SubjectId("01-01-P"),
            data=self._build_synthetic_data_from_subject_id(mri_exam_id)
        )

    def _build_synthetic_data_from_subject_id(self, synthetic_mri_exam_id: MRIExamId) -> list[MRIData]:
        atlas_data = [
            AtlasSegmentation(
                mri_exam_id=synthetic_mri_exam_id,
                voxel_data=MockSegmentationData(),
                atlas=atlas,
            )
            for atlas in self.atlases
        ]
        dti_md_data = [
            DTIMap(
                mri_exam_id=synthetic_mri_exam_id,
                voxel_data=MockVoxelData(),
                dti_metric=metric,
            )
            for metric in DTIMetric
        ]
        return atlas_data + dti_md_data

    def save(self, mri_exam: MRIExam) -> None:
        """
        Save a synthetic MRI exam.
        This method is not implemented as this repository generates synthetic data.
        """
        pass

    def find_by_id(self, entity_id: MRIExamId) -> Optional[MRIExam]:
        return self._build_synthetic_mri_exam_from_id(entity_id)

    def list_all(self) -> List[Entity]:
        raise NotImplementedError("list_all is not implemented in MockSyntheticMRIExamRepository")

    def delete(self, entity: Entity) -> None:
        raise NotImplementedError("delete is not implemented in MockSyntheticMRIExamRepository")


class MockInMemoryMRIExamRepository(InMemoryRepository[MRIExam, MRIExamId], MRIExamRepository):
    """
    In-memory repository for MRIExam objects.
    """

    def __init__(self, mri_exams: Optional[List[MRIExam]] = None):
        super().__init__(id_extractor=lambda exam: exam.id)
        mri_exams = mri_exams or []

    def get_exam_for_subject(self, subject_id: SubjectId) -> MRIExam:
        for exam in self.list_all():
            if exam.subject_id == subject_id:
                return exam
        raise LookupError(f"MRI exam for subj {subject_id} not found.")

    def save_exam(self, mri_exam: MRIExam) -> None:
        self.save(mri_exam)


class MockInMemoryNormativeValuesRepository(InMemoryRepository[NormativeValue, str], NormativeValueRepository):
    """
    In-memory repository for NormativeValue objects.
    """

    def __init__(self):
        # Key = synthetic ID based on center/metric/atlas/label/statistic_strategy
        super().__init__(id_extractor=self._build_id)

    @staticmethod
    def _build_id(normative_value: NormativeValue) -> str:
        return (f"{normative_value.center.id}"
                f"-{normative_value.dti_metric.name}"
                f"-{normative_value.atlas.id}"
                f"-{normative_value.atlas_label}"
                f"-{normative_value.statistic_strategy.name}")

    def save(self, normative_value: NormativeValue) -> None:
        super().save(normative_value)

    def save_list(self, normative_values_list: List[NormativeValue]) -> None:
        for nv in normative_values_list:
            self.save(nv)

    def exists(self, center: Center, dti_metric: DTIMetric, atlas: Atlas, atlas_label: int,
               statistic_strategy: StatisticStrategy) -> bool:
        synthetic_id = f"{center.id}-{dti_metric.name}-{atlas.id}-{atlas_label}-{statistic_strategy.name}"
        return self.find_by_id(synthetic_id) is not None

    def get_by_parameters(self, center: Center, dti_metric: DTIMetric, atlas: Atlas, atlas_label: int,
                          statistic_strategy: StatisticStrategy) -> NormativeValue:
        synthetic_id = f"{center.id}-{dti_metric.name}-{atlas.id}-{atlas_label}-{statistic_strategy.name}"
        normative_value = self.find_by_id(synthetic_id)
        if normative_value is None:
            raise EntityNotFoundException(message=f"NormativeValue with parameters {center}, "
                                                  f"{dti_metric}, {atlas}, {atlas_label}, "
                                                  f"{statistic_strategy} not found "
                                                  f"in repository {self}",
                                          repository=self)
        return normative_value


class MockInMemoryRepositoriesRegistry(RepositoriesRegistry):
    """
    Mock implementation of the RepositoriesRegistry interface.
    """

    def __init__(self) -> None:
        atlas_repository = MockAtlasRepository()
        self._dict_of_repositories: Dict[Type[Entity], Repository] = {
            Subject: MockInMemorySubjectRepository(),
            MRIExam: MockSyntheticMRIExamRepository(atlases=atlas_repository.list_all()),
            Center: MockCenterRepository(),
            Atlas: atlas_repository,
            NormativeValue: MockInMemoryNormativeValuesRepository(),
        }

    def get_repository(self, entity_type: Type[Entity]) -> Repository[Entity, EntityIdentifier]:
        return self._dict_of_repositories[entity_type]

    def list_all_repositories(self) -> List[Repository[Entity, EntityIdentifier]]:
        return list(self._dict_of_repositories.values())

    def register_repository(self, entity_type: Type[Entity], repository: Repository[Entity, EntityIdentifier]) -> None:
        self._dict_of_repositories[entity_type] = repository


class MockInMemoryDataGateway(DataBaseGateway):
    """
    Mock implementation of DataBaseGateway for testing.
    Stores entities in memory using dictionaries.
    """

    def __init__(self):
        """
        Initialize the in-memory data gateway.
        """
        self.entity_storage = {
            Center: {},
            Subject: {},
            Atlas: {},
            MRIExam: {},
            MRIData: {},
            NormativeValue: {}
        }

    @staticmethod
    def get_id(entity):
        """Extract ID from entity based on its type."""
        id_extractors = {
            Center: lambda x: x.id,
            Subject: lambda x: str(x.id),
            Atlas: lambda x: x.id,
            MRIExam: lambda x: str(x.id),
            MRIData: lambda x: f"{x.mri_exam_id}_{x.name}",
            NormativeValue: lambda x: id(x)  # Use object ID as fallback
        }
        entity_type = type(entity)
        if entity_type in id_extractors:
            return id_extractors[entity_type](entity)
        return id(entity)  # Fallback to Python's object ID

    @staticmethod
    def convert_id(entity_type: Type[Entity], id_value: EntityIdentifier) -> Any:
        """Convert ID to the appropriate type based on entity type."""
        if entity_type == Subject and type(id_value) == SubjectId:
            return str(id_value)
        elif entity_type == MRIExam and type(id_value) == MRIExamId:
            return str(id_value)
        elif entity_type == Atlas and type(id_value) == int:
            return id_value
        elif entity_type == Center and type(id_value) == int:
            return id_value
        return id_value

    def find_by_id(self, entity_type: Type[Entity], id_value: Any) -> Optional[Entity]:
        """Find entity by ID and type."""
        # Handle the case where entity_type is a TypeVar or generic
        if entity_type not in self.entity_storage:
            return None

        converted_id = self.convert_id(entity_type, id_value)

        return self.entity_storage[entity_type].get(converted_id)

    def find_by_filters(self, entity_type: Type[Entity], filters: dict[str, Any]) -> Optional[Entity]:
        """Find entity by filters."""
        if entity_type not in self.entity_storage:
            return None

        for entity in self.entity_storage[entity_type].values():
            if all(getattr(entity, k) == v for k, v in filters.items()):
                return entity

        return None

    def find_all(self, entity_type: Type[Entity]) -> list[Entity]:
        """Find all entities of a given type."""
        if entity_type not in self.entity_storage:
            return []

        return list(self.entity_storage[entity_type].values())

    def save(self, entity: Entity) -> None:
        """Save an entity to storage."""
        entity_type = type(entity)
        if entity_type not in self.entity_storage:
            self.entity_storage[entity_type] = {}

        entity_id = self.get_id(entity)
        self.entity_storage[entity_type][entity_id] = entity

    def save_list(self, entities: List[Entity]) -> None:
        """Save a list of entities."""
        for entity in entities:
            self.save(entity)

    def delete(self, entity: Entity) -> None:
        """Delete an entity."""
        entity_type = type(entity)
        if entity_type in self.entity_storage:
            entity_id = self.get_id(entity)
            if entity_id in self.entity_storage[entity_type]:
                del self.entity_storage[entity_type][entity_id]

    def update(self, entity: Entity) -> None:
        """Update an entity (same as save in this implementation)."""
        self.save(entity)
