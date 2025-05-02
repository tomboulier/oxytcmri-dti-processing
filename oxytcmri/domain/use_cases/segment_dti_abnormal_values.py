"""
This module segments the abnormal values in DTI images using the normative values computed in each center from healthy subjects.
"""
import warnings
from enum import Enum
from typing import Optional, List, Callable, Tuple

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas, DTIMetric, DTIMap, MRIData, VoxelData
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.monitoring import EventDispatcher
from oxytcmri.domain.ports.repositories import (
    SubjectRepository, MRIExamRepository, AtlasRepository, CenterRepository, RepositoriesRegistry)
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue


class AbnormalValueType(Enum):
    """
    Enum for the type of abnormal values.
    """
    HIGH = "high"
    LOW = "low"


class AbnormalVoxelData(VoxelData[AbnormalValueType]):
    """
    Implementation of VoxelData for abnormal DTI values.

    This class stores abnormal voxels in a dictionary, where only abnormal voxels
    are stored. Voxels not present in the dictionary are considered normal.

    Parameters
    ----------
    source_dti_map : DTIMap
        The source DTI map used to get dimensions and voxel volume
    """

    def __init__(self, source_dti_map: DTIMap):
        """
        Initialize with dimensions from the source DTI map.

        Parameters
        ----------
        source_dti_map : DTIMap
            The source DTI map used to get dimensions and voxel volume
        """
        self.source_dti_map = source_dti_map

        # Dictionary to store abnormal voxels
        # Key: tuple (x, y, z), Value: AbnormalValueType (HIGH or LOW)
        self.abnormal_voxels: dict[tuple[int, int, int], AbnormalValueType] = {}

    def set_value_at(self, x: int, y: int, z: int, value: AbnormalValueType) -> None:
        """
        Set an abnormal value at the specified coordinates.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate
        value : AbnormalValueType
            The type of abnormality (HIGH or LOW)

        Raises
        ------
        ValueError
            If coordinates are out of bounds
        """
        if not self._is_in_bounds(x, y, z):
            raise ValueError(f"Coordinates ({x}, {y}, {z}) out of bounds. Dimensions: {self.dimensions}")

        # Add to dictionary
        self.abnormal_voxels[(x, y, z)] = value

    def get_value_at(self, x: int, y: int, z: int) -> AbnormalValueType:
        """
        Get the abnormal value at the specified coordinates.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate

        Returns
        -------
        AbnormalValueType
            The abnormal value type (HIGH or LOW)

        Raises
        ------
        ValueError
            If coordinates are out of bounds or if voxel is not abnormal
        """
        if not self._is_in_bounds(x, y, z):
            raise ValueError(f"Coordinates ({x}, {y}, {z}) out of bounds. Dimensions: {self.dimensions}")

        coords = (x, y, z)
        if coords not in self.abnormal_voxels:
            raise ValueError(f"No abnormal value at coordinates ({x}, {y}, {z})")

        return self.abnormal_voxels[coords]

    def is_abnormal(self, x: int, y: int, z: int) -> bool:
        """
        Check if a voxel is marked as abnormal.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate

        Returns
        -------
        bool
            True if voxel is abnormal, False otherwise
        """
        return (x, y, z) in self.abnormal_voxels

    def _is_in_bounds(self, x: int, y: int, z: int) -> bool:
        """
        Check if coordinates are within dimensions bounds.

        Parameters
        ----------
        x : int
            X coordinate
        y : int
            Y coordinate
        z : int
            Z coordinate

        Returns
        -------
        bool
            True if coordinates are valid, False otherwise
        """
        return (0 <= x < self.dimensions[0] and
                0 <= y < self.dimensions[1] and
                0 <= z < self.dimensions[2])

    def get_dimensions(self) -> Tuple[int, int, int]:
        """
        Get the dimensions of the voxel data.

        Returns
        -------
        Tuple[int, int, int]
            Dimensions as (x, y, z)
        """
        return self.source_dti_map.voxel_data.get_dimensions()

    def get_voxel_volume_in_ml(self) -> float:
        """
        Get the volume of a voxel in milliliters.

        Returns
        -------
        float
            Volume in milliliters
        """
        return self.source_dti_map.voxel_data.get_voxel_volume_in_ml()

    def filter_values(self, condition: Callable[[AbnormalValueType], bool]) -> VoxelData[bool]:
        """
        Filter abnormal values based on a condition.

        Parameters
        ----------
        condition : Callable[[AbnormalValueType], bool]
            Function that tests if a voxel should be included

        Returns
        -------
        VoxelData[bool]
            Boolean mask of matching voxels
        """
        raise NotImplementedError("AbnormalVoxelData.filter_values")


class DTIAbnormalValues(MRIData[AbnormalValueType]):
    """
    Class to store the abnormal values in DTI images.
    """

    def __init__(self, dti_map: DTIMap, name: Optional[str] = None):
        """
        Initializes the DTIAbnormalValues class.
        """
        super().__init__(mri_exam_id=dti_map.mri_exam_id,
                         name=name or f"abnormal_values_{dti_map.name}",
                         voxel_data=AbnormalVoxelData(dti_map))


class SegmentDTIAbnormalValues:
    """
    Segment abnormal values in DTI images compared to normative values (computed in each center from healthy subjects).
    """

    def __init__(self,
                 repositories_registry: RepositoriesRegistry,
                 dispatcher: Optional[EventDispatcher] = None):
        """
        Initializes the SegmentDtiAbnormalValues use-case.
        """
        self.subjects_repository: SubjectRepository = repositories_registry.get_repository(Subject)
        self.mri_repository: MRIExamRepository = repositories_registry.get_repository(MRIExam)
        self.atlas_repository: AtlasRepository = repositories_registry.get_repository(Atlas)
        self.centers_repository: CenterRepository = repositories_registry.get_repository(Center)
        self.normative_values_repository: NormativeValueRepository = (
            repositories_registry.get_repository(NormativeValue))

    def __call__(self,
                 dti_metrics: Optional[List[DTIMetric]] = None) -> None:
        """
        Runs the use-case.

        Segments the DTI images of all patients in the SubjectRepository, for DTI metrics provided.

        Parameters
        ----------
        dti_metrics : List[DTIMetric], optional
            The DTI metrics to segment. If None, all the DTI metrics will be segmented.
        """
        self.segment_all_mri_exams_of_patients(dti_metrics)

    def segment_all_mri_exams_of_patients(self,
                                          dti_metrics: Optional[List[DTIMetric]] = None):
        """
        Segments all the MRI exams of all patients.

        It will look for all the patients in the SubjectRepository and for each patient, it will segment the DTI images.
        This segmentation process will have access to the normative values stored in the NormativeValuesRepository.
        """
        dti_metrics = dti_metrics or list(DTIMetric)
        # Get all the patients
        patients = self.subjects_repository.list_all_patients()
        for patient in patients:
            # Get the MRI exam for the patient
            mri_exam = self.mri_repository.get_exam_for_subject(patient)
            for dti_metric in dti_metrics:
                # Get the DTI map associated with the DTI metric
                try:
                    dti_image = mri_exam.get_dti_map(dti_metric)
                    self.segment_dti_map(dti_image)
                except LookupError:
                    # If the DTI image is not found, skip this metric
                    continue

    def segment_dti_map(self, dti_image: DTIMap) -> MRIData:
        """
        Segments the DTI map, i.e. build a map with values indicating the abnormal values in the input DTI map.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map to segment.
        """
        segmentations = []
        for atlas in self.atlas_repository.list_all():
            segmentations.append(self.segment_dti_map_for_atlas(dti_image, atlas))
        return self.merge_segmentations(segmentations)

    def segment_dti_map_for_atlas(self, dti_image: DTIMap, atlas: Atlas) -> MRIData:
        """
        Segments the DTI map for a given atlas, using the normative values.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map to segment.
        atlas : Atlas
            The atlas to use for segmentation.

        Returns
        -------
        MRIData
            The list of segmentations for the DTI map.
        """
        result = DTIAbnormalValues(dti_image,
                                   name=f"abnormal_{dti_image.dti_metric}_values_{atlas.name}")
        for atlas_label in atlas.labels:
            thresholds = self.compute_thresholds(dti_image, atlas, atlas_label)
            self.mark_abnormal_voxels(dti_image, atlas, atlas_label, thresholds, result)
        return result

    def merge_segmentations(self, segmentations: List[MRIData]) -> MRIData:
        """
        Merges the segmentations into a single MRIData object.

        Parameters
        ----------
        segmentations : List[MRIData]
            The list of segmentations to merge.

        Returns
        -------
        MRIData
            The merged segmentation.

        Warnings
        --------
        UserWarning
            Warns that this is a temporary dummy implementation.
        """
        if not segmentations:
            raise ValueError("Cannot merge empty list of segmentations")

        warnings.warn(
            "Using dummy implementation of merge_segmentations that returns only the first segmentation. "
            "This should be properly implemented in the future.",
            UserWarning,
            stacklevel=2
        )

        # Just return the first segmentation for now
        return segmentations[0]

    def compute_thresholds(self, dti_image, atlas, atlas_label):
        return None

    def mark_abnormal_voxels(self, dti_image, atlas, atlas_label, thresholds, result):
        pass
