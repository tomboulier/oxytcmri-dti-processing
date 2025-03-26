from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import (
    DTIMetric,
    Atlas,
    MRIExam,
    VoxelData, AtlasSegmentation, DTIMap, T,
)
from oxytcmri.domain.ports.repositories import SubjectRepository, MRIExamRepository, CenterRepository, AtlasRepository
import pytest
from typing import List, Optional, Tuple, Callable

from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue


@pytest.fixture
def test_center():
    return Center(id=1, name="Test Center")

class MockCenterRepository(CenterRepository):
    def save_centers(self, centers: List[Center]) -> None:
        pass

    def get_all_centers(self) -> List[Center]:
        return [
            Center(id=1, name="Brest"),
            Center(id=2, name="New-York"),
            Center(id=3, name="Katmandou"),
        ]


class MockAtlasRepository(AtlasRepository):
    def __init__(self):
        # Mock atlas data
        self.atlases = {
            2: Atlas(id=2, labels=[1, 2, 3], name="Neuromorphometrics atlas + GM parcels size ≤5cm3"),
            4: Atlas(id=4, labels=[29, 33, 59, 60, 62], name="Neuromorphometrics atlas + GM parcels size >5cm3"),
        }

    def get_all_atlases(self) -> List[Atlas]:
        return list(self.atlases.values())

    def get_atlas_by_id(self, atlas_id: int) -> Atlas:
        # Mock implementation
        try:
            return self.atlases[atlas_id]
        except KeyError:
            raise LookupError(f"Atlas with ID {atlas_id} not found.")


class MockInMemorySubjectRepository(SubjectRepository):
    def __init__(self, test_center: Center):
        # Subjects from the center
        self.subject1 = Subject(
            id="S1",
            subject_type=SubjectType.HEALTHY_VOLUNTEER,
            center_id=test_center.id,
        )
        self.subject2 = Subject(
            id="S2", subject_type=SubjectType.PATIENT, center_id=test_center.id
        )

        # Subject from a different center
        self.subject3 = Subject(
            id="S3", subject_type=SubjectType.HEALTHY_VOLUNTEER, center_id=2
        )

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
        pass


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


class MockInMemoryMRIRepository(MRIExamRepository):
    def __init__(self, atlases: List[Atlas]):
        # Create segmentation atlas data
        self.atlas_data = []
        for atlas in atlases:
            atlas_segmentation = AtlasSegmentation(
                id=f"atlas_segmentation_{atlas.id}",
                name=f"Segmentation Atlas {atlas.id}",
                voxel_data=MockVoxelData(),
                atlas=atlas,
            )
            self.atlas_data.append(atlas_segmentation)

        # Create DTI map data
        self.dti_md_data = []
        for dti_metric in DTIMetric:
            dti_map = DTIMap(
                id=f"dti_map_{dti_metric.name}",
                name=f"DTI Map {dti_metric.name}",
                voxel_data=MockVoxelData(),
                dti_metric=dti_metric,
            )
            self.dti_md_data.append(dti_map)

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        """Obtenir un examen IRM pour un sujet donné."""
        return MRIExam(
            id=f"exam_{subject_id}",
            subject_id=subject_id,
            data=self.dti_md_data + self.atlas_data,
        )

class MockInMemoryNormativeValuesRepository(NormativeValueRepository):
    def __init__(self):
        # Mock normative values data
        self.normative_values = []

    def save(self, normative_value: NormativeValue) -> None:
        self.normative_values.append(normative_value)

    def get_all(self):
        return self.normative_values
