from oxytcmri.domain.entities.subject import Subject, SubjectType
from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import (
    DTIMetric,
    Atlas,
    MRIExam,
    MRIData,
    VoxelData, AtlasSegmentation, DTIMap,
)
from oxytcmri.domain.ports.repositories import SubjectRepository, MRIExamRepository
from oxytcmri.domain.use_cases.compute_dti_normative_values import (
    ComputeDTINormativeValues,
)
import pytest
from typing import List, Optional, Tuple


# Entities
class TestSubject:
    def test_create_subject(self):
        new_subject = Subject.from_string_id("01-01-P")
        assert new_subject.center_id == 1
        assert new_subject.subject_type == SubjectType.PATIENT

        healthy_volunteer = Subject.from_string_id("02-03-V")
        assert healthy_volunteer.subject_type == SubjectType.HEALTHY_VOLUNTEER
        assert healthy_volunteer.center_id == 2

    def test_subject_id_invalid(self):
        with pytest.raises(ValueError):
            Subject.from_string_id("01-01-INVALID")

        with pytest.raises(ValueError):
            Subject.from_string_id("XX-01-P")

        with pytest.raises(ValueError):
            Subject.from_string_id("01-YY-H")

    def test_subject_type(self):
        assert SubjectType.PATIENT == SubjectType.from_string("P")
        assert SubjectType.HEALTHY_VOLUNTEER == SubjectType.from_string("V")
        assert SubjectType.TEST_PATIENT == SubjectType.from_string("T")

        with pytest.raises(ValueError):
            SubjectType.from_string("INVALID")


# repositories
@pytest.fixture
def test_center():
    return Center(id=1, name="Test Center")


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


# Mocks for tests
class MockVoxelData(VoxelData[float]):
    """Mock for voxel data."""

    def __init__(self):
        # Test values for apply_mask
        self.test_values = [0.1, 0.2, 0.3]

    def get_value_at(self, x: int, y: int, z: int) -> float:
        return 0.5

    def get_dimensions(self) -> Tuple[int, int, int]:
        return (10, 10, 10)

    def get_voxel_volume_in_ml(self) -> float:
        return 8.0

    def get_values_where(self, condition) -> List[float]:
        """Get values where condition is True."""
        return self.test_values

    def apply_mask(self, mask: "MockMaskData") -> List[float]:
        """Apply a mask to filter voxel data."""
        return self.test_values


class MockMaskData(VoxelData[bool]):
    """Mock for boolean masks."""

    def get_value_at(self, x: int, y: int, z: int) -> bool:
        return True

    def get_dimensions(self) -> Tuple[int, int, int]:
        return 10, 10, 10

    def get_voxel_volume_in_ml(self) -> float:
        return 8.0


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


class TestSubjectRepository:
    def test_find_subjects_by_center(self, test_center):
        # definitions
        repository = MockInMemorySubjectRepository(test_center)

        # execution
        all_subjects = repository.find_subjects_by_center(test_center)
        healthy_volunteers = repository.find_subjects_by_center(
            test_center, subject_type=SubjectType.HEALTHY_VOLUNTEER
        )
        patients = repository.find_subjects_by_center(
            test_center, subject_type=SubjectType.PATIENT
        )

        # assertions
        assert len(all_subjects) == 3
        assert len(healthy_volunteers) == 2
        assert len(patients) == 1


# Use cases
class TestComputeDTIReferenceValues:
    def test_execute_use_case(self, test_center):
        # definitions
        dti_metric = DTIMetric.MD
        atlas = Atlas(
            id=2,
            labels=[1, 2, 3],
            name="Neuromorphometrics atlas + GM parcels size ≤5cm3",
        )

        # execution
        use_case = ComputeDTINormativeValues(
            subjects_repository=MockInMemorySubjectRepository(test_center),
            mri_repository=MockInMemoryMRIRepository(atlases=[atlas]),
        )
        result = use_case.execute(test_center, dti_metric, atlas)

        # assertions
        assert result is not None
        assert all(item.center == test_center for item in result)
        assert all(item.dti_metric == dti_metric for item in result)
        assert all(item.atlas == atlas for item in result)
        assert all(isinstance(item.value, float) for item in result)
