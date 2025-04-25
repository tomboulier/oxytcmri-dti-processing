from typing import List, Optional, Tuple, Callable, Dict, Generic

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import (
    DTIMetric,
    Atlas,
    MRIExam,
    VoxelData, AtlasSegmentation, DTIMap, T, MRIExamId,
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
)
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue, \
    StatisticStrategy


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
            self.save_centers([
                Center(id=1, name="Brest"),
                Center(id=2, name="New-York"),
                Center(id=3, name="Katmandou"),
            ])

    def get_center_by_id(self, center_id: int) -> Center:
        center = self.find_by_id(center_id)
        if center is None:
            raise LookupError(f"Center with ID {center_id} not found.")
        return center

    def get_all_centers(self) -> List[Center]:
        return self.list_all()

    def save_centers(self, centers: List[Center]) -> None:
        for center in centers:
            self.save(center)


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

    def get_all_atlases(self) -> List[Atlas]:
        return self.list_all()

    def get_atlas_by_id(self, atlas_id: int) -> Atlas:
        atlas = self.find_by_id(atlas_id)
        if atlas is None:
            raise LookupError(f"Atlas with ID {atlas_id} not found.")
        return atlas

    def save_atlas(self, atlas: Atlas) -> None:
        self.save(atlas)


class MockInMemorySubjectRepository(InMemoryRepository[Subject, SubjectId], SubjectRepository):
    """
    Mock implementation of the SubjectRepository interface.
    """
    def __init__(self):
        # Initialize the in-memory repository with a function to extract the ID
        super().__init__(id_extractor=lambda subject: subject.id)
        # Subjects from the center
        self.subject1 = Subject.from_string_id(id_str="01-01-P")
        self.subject2 = Subject.from_string_id(id_str="01-02-V")
        # Subject from a different center
        self.subject3 = Subject.from_string_id(id_str="02-03-V")

        # All subjects
        self.all_subjects = [self.subject1, self.subject2, self.subject3]

    def find_subjects_by_center(
            self, center: Center, subject_type: Optional[SubjectType] = None
    ) -> List[Subject]:
        if subject_type is None:
            return self.all_subjects

        return [
            subject
            for subject in self.all_subjects
            if subject.subject_type == subject_type
        ]


class MockInMemoryEmptySubjectRepository(SubjectRepository):
    def __init__(self):
        self.all_subjects = []

    def save(self, subject: Subject) -> None:
        self.all_subjects.append(subject)

    def find_by_id(self, subject_id: str) -> Optional[Subject]:
        id_to_check = SubjectId(subject_id)
        for subject in self.all_subjects:
            if subject.id == id_to_check:
                return subject

        return None

    def find_subjects_by_center(
            self, center: Center, subject_type: Optional[SubjectType] = None
    ) -> List[Subject]:
        result = []
        for subject in self.all_subjects:
            if subject.center_id == center.id:
                if subject_type is None or subject.subject_type == subject_type:
                    result.append(subject)
        return result


class MockMaskData(VoxelData[bool]):
    """Mock for boolean masks."""

    def __init__(self, boolean_value: bool = True):
        self.boolean_value = boolean_value

    def get_value_at(self, x: int, y: int, z: int) -> bool:
        return self.boolean_value

    def get_dimensions(self) -> Tuple[int, int, int]:
        return 10, 10, 10

    def get_voxel_volume_in_ml(self) -> float:
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

    def get_dimensions(self) -> Tuple[int, int, int]:
        return (10, 10, 10)

    def get_voxel_volume_in_ml(self) -> float:
        return 8.0

    def apply_mask(self, mask: "MockMaskData") -> List[float]:
        """Apply a mask to filter voxel data."""
        return self.test_values

    def filter_values(self, condition: Callable[[T], bool]) -> VoxelData[bool]:
        return MockMaskData(condition(self.value))


class MockSyntheticMRIExamRepository(MRIExamRepository):
    """
    Generates synthetic MRIExam objects on-the-fly for any subject_id.
    """

    def __init__(self, atlases: List[Atlas]):
        self.atlas_data = [
            AtlasSegmentation(
                id=f"atlas_segmentation_{atlas.id}",
                name=f"Segmentation Atlas {atlas.id}",
                voxel_data=MockVoxelData(),
                atlas=atlas,
            )
            for atlas in atlases
        ]

        self.dti_md_data = [
            DTIMap(
                id=f"dti_map_{metric.name}",
                name=f"DTI Map {metric.name}",
                voxel_data=MockVoxelData(),
                dti_metric=metric,
            )
            for metric in DTIMetric
        ]

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        return MRIExam(
            id=f"exam_{subject_id}",
            subject_id=subject_id,
            data=self.dti_md_data + self.atlas_data,
        )

    def save(self, mri_exam: MRIExam) -> None:
        raise NotImplementedError("save is not implemented in MockSyntheticMRIExamRepository")

    def find_by_id(self, entity_id: EntityIdentifier) -> Optional[Entity]:
        raise NotImplementedError("find_by_id is not implemented in MockSyntheticMRIExamRepository")

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

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        for exam in self.list_all():
            if exam.subject_id == subject_id:
                return exam
        raise LookupError(f"MRI exam for subject {subject_id} not found.")

    def save_exam(self, mri_exam: MRIExam) -> None:
        self.save(mri_exam)


class MockInMemoryNormativeValuesRepository(NormativeValueRepository):
    def __init__(self):
        # Mock normative values data
        self.normative_values = []

    def save(self, normative_value: NormativeValue) -> None:
        self.normative_values.append(normative_value)

    def batch_save(self, normative_values_list: list[NormativeValue]) -> None:
        self.normative_values += normative_values_list

    def get_all(self):
        return self.normative_values

    def exists(self, center: Center, dti_metric: DTIMetric, atlas: Atlas, atlas_label: int,
               statistic_strategy: StatisticStrategy) -> bool:
        return any(
            normative_value.center_id == center.id and
            normative_value.dti_metric == dti_metric and
            normative_value.atlas_id == atlas.id and
            normative_value.atlas_label == atlas_label and
            normative_value.statistic_strategy == statistic_strategy
            for normative_value in self.normative_values)
