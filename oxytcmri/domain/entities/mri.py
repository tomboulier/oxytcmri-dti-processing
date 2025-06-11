"""
This module contains all the classes related to MRI data.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Generic, TypeVar, Callable, Collection, Optional, Tuple

from oxytcmri.domain.entities.subject import SubjectId

T = TypeVar("T")


class DTIMetric(Enum):
    """Different metrics derived from diffusion tensor imaging."""

    MD = "Mean Diffusivity"
    FA = "Fractional Anisotropy"
    AD = "Axial Diffusivity"
    RD = "Radial Diffusivity"

    @classmethod
    def from_acronym(cls, acronym: str):
        """
        Get a DTIMetric enum value from its acronym.

        Parameters
        ----------
        acronym : str
            The acronym (e.g., 'MD', 'FA')

        Returns
        -------
        DTIMetric
            The corresponding enum value

        Raises
        ------
        ValueError
            If no enum value matches the given acronym
        """
        for metric in cls:
            if metric.name == acronym:
                return metric
        raise ValueError(f"No DTIMetric found for acronym: {acronym}")

    def __str__(self):
        return self.name


@dataclass
class Atlas:
    """
    An atlas is a set of labels that can be used to segment the brain.

    Parameters
    ----------
    id : int
        Unique identifier for the atlas
    labels : List[int]
        List of labels within the atlas
    name : str, optional
        Name of the atlas (e.g. "Atlas1", "Atlas2")
    """
    id: int
    labels: List[int]
    name: Optional[str] = None

    def __post_init__(self):
        """
        Validate the atlas ID.

        Raises
        ------
        ValueError
            If the atlas ID is not an integer
        """
        if not isinstance(self.id, int):
            raise ValueError("Atlas ID must be an integer.")

    def __repr__(self) -> str:  # pragma: no cover
        """
        String representation of the Atlas object.

        Returns
        -------
        str
            String representation of the Atlas object
        """
        if self.name:
            return f"Atlas(id={self.id}, name={self.name})"
        return f"Atlas(id={self.id})"


@dataclass
class RegionOfInterest:
    """
    Represents a Region of Interest (ROI) in medical imaging.

    Parameters
    ----------
    atlas : Atlas
        The atlas used to define the region
    labels : List[int]
        The list of labels within the atlas defining the region
    """

    atlas: Atlas
    labels: List[int]


class VoxelData(ABC, Generic[T]):
    """
    Protocol defining the interface for voxel data access.

    This interface abstracts the underlying data representation (numpy arrays, etc.)
    to keep the domain layer independent from technical implementations.
    """

    @abstractmethod
    def get_value_at(self, x: int, y: int, z: int) -> T:
        """
        Get the value of a voxel at a specific position.

        Parameters
        ----------
        x : int
            x-coordinate of the voxel
        y : int
            y-coordinate of the voxel
        z : int
            z-coordinate of the voxel

        Returns
        -------
        T
            Value of the voxel
        """

    @abstractmethod
    def set_value_at(self, x: int, y: int, z: int, value: T) -> None:
        """
        Set the value of a voxel at a specific position.

        Parameters
        ----------
        x : int
            x-coordinate of the voxel
        y : int
            y-coordinate of the voxel
        z : int
            z-coordinate of the voxel
        value : T
            Value to set for the voxel

        Returns
        -------
        None
        """

    @abstractmethod
    def get_dimensions(self) -> tuple[int, int, int]:
        """
        Get the dimensions of the voxel data.

        Returns
        -------
        tuple[int, int, int]
            Dimensions of the voxel data
        """

    @abstractmethod
    def get_voxel_volume_in_ml(self) -> float:
        """
        Get the volume of a voxel in milliliters (mL).

        Returns
        -------
        float
            Volume of a voxel, in mL.
        """

    @abstractmethod
    def filter_values(self, condition: Callable[[T], bool]) -> VoxelData[bool]:
        """
        Create a boolean representation of voxel data based on a filtering condition.

        Parameters
        ----------
        condition : Callable[[T], bool]
            Function that takes a voxel value and returns True if the voxel
            should be included in the filter

        Returns
        -------
        VoxelData[bool]
            A boolean representation where voxels are True if they match the condition
        """

    def filter_by_values(self, values_to_include: Collection[T]) -> VoxelData[bool]:
        """
        Create a boolean representation where voxels with values in the provided
        collection are True.

        Parameters
        ----------
        values_to_include : Collection[T]
            Collection of values to include in the filter

        Returns
        -------
        VoxelData[bool]
            A boolean representation where voxels are True if their value
            is in values_to_include
        """
        return self.filter_values(lambda x: x in values_to_include)


@dataclass(frozen=True)
class MRIExamId:
    """
    Value Object representing an MRI examination identifier.

    The ID can have different formats in the database:
    - "06-08P-MR-170918"
    - "10_03V_MR301015"
    - "13-03P-190717"
    """

    id: str

    def __str__(self) -> str:
        return self.id

    def to_subject_id(self) -> SubjectId:
        """
        Convert the MRIExamId to a subject ID.

        For example:
        - "06-08P-MR-170918" -> "06-08-P"
        - "10_03V_MR301015" -> "10-03-V"
        - "13-03P-190717" -> "13-03-P"

        Returns
        -------
        SubjectId
            The subject ID derived from the MRIExamId
        """
        cleaned = re.sub(r"[-_]", "", self.id.upper())

        if len(cleaned) < 5:
            raise ValueError(f"Invalid MRIExamId format (too short): {self.id}")

        center = cleaned[0:2]
        subject = cleaned[2:4]
        subject_type = cleaned[4]

        if not center.isdigit() or not subject.isdigit():
            raise ValueError(f"Invalid center or subject number in ID: {self.id}")
        if subject_type not in {"P", "V", "T"}:
            raise ValueError(f"Invalid subject type (expected P, V or T) in ID: {self.id}")

        return SubjectId(f"{center}-{subject}-{subject_type}")


@dataclass(kw_only=True)
class MRIData(Generic[T]):
    """
    Represents a 3D MRI data volume.

    This can be:
    - An anatomical sequence (T1, T2, FLAIR)
    - A DTI-derived map (MD, FA)
    - An atlas or segmentation mask

    Attributes
    ----------
    voxel_data : VoxelData[T]
        Provider for voxel data
    mri_exam_id : MRIExamId
        Unique identifier of the MRI exam which this data belongs to
    name : Optional[str]
        Optional name of the MRI data
    """
    voxel_data: VoxelData[T]
    mri_exam_id: MRIExamId
    name: Optional[str] = None

    def get_voxel_data(self) -> VoxelData[T]:
        """
        Get the voxel data of this MRI volume.

        Returns
        -------
        VoxelData[T]
            Interface to access the underlying voxel data
        """
        return self.voxel_data


@dataclass(kw_only=True)
class DTIMap(MRIData[float]):
    """
    Represents a map of DTI metric (FA, MD, RA, RD).

    Parameters
    ----------
    voxel_data : VoxelData[float]
        Provider for voxel data
    mri_exam_id : MRIExamId
        Identifier of the MRI exam
    dti_metric : DTIMetric
        The type of DTI metric (MD, FA, etc.)
    name : Optional[str]
        Optional name of the DTI map, defaults to "{dti_metric}_map" if not provided
    """
    dti_metric: DTIMetric

    def __post_init__(self):
        """
        Set default name if not provided.
        """
        if self.name is None:
            self.name = f"{self.dti_metric}_map"

    def __repr__(self) -> str:  # pragma: no cover
        """
        String representation of the DTIMap object.

        Returns
        -------
        str
            String representation of the DTIMap object
        """
        return f"DTIMap(mri_exam_id={self.mri_exam_id}, metric={self.dti_metric})"


class Mask(MRIData[bool]):
    """
    Represents a binary mask for a specific region of interest.

    Parameters
    ----------
    mri_exam_id : MRIExamId
        Unique identifier of the MRI exam which this data belongs to
    voxel_data : VoxelData[bool]
        Provider for voxel data
    """

    def extract_values_from(self, mri_data: MRIData[T]) -> List[T]:
        """
        Extract values from an MRI data object where this mask is True.

        Parameters
        ----------
        mri_data : MRIData[T]
            The MRI data from which to extract values

        Returns
        -------
        List[T]
            List of values from voxels where this mask is True
        """
        # Result list to store the extracted values
        values = []

        # Get the voxel data from the mask and the source MRI data
        mask_voxel_data = self.get_voxel_data()
        source_voxel_data = mri_data.get_voxel_data()

        # Check if the dimensions of the mask and source data match
        mask_dimensions = mask_voxel_data.get_dimensions()
        source_dimensions = source_voxel_data.get_dimensions()
        if mask_dimensions != source_dimensions:
            raise ValueError(
                f"Dimensions mismatch: mask {mask_dimensions} vs source {source_dimensions}"
            )

        # Iterate through the mask dimensions
        for x in range(mask_dimensions[0]):
            for y in range(mask_dimensions[1]):
                for z in range(mask_dimensions[2]):
                    # If the mask is True, get the corresponding value from the source data
                    if mask_voxel_data.get_value_at(x, y, z):
                        values.append(source_voxel_data.get_value_at(x, y, z))

        return values

    def get_true_voxel_coordinates(self) -> List[Tuple[int, int, int]]:
        """
        Get the coordinates of all voxels where this mask is True.
        
        This method iterates through all voxels in the mask and returns
        the coordinates (x, y, z) where the value is True.
        
        Returns
        -------
        List[Tuple[int, int, int]]
            List of (x, y, z) coordinates where the mask has True values
        """
        # List to store coordinates
        coordinates = []

        # Get the mask's voxel data
        mask_voxel_data = self.get_voxel_data()

        # Get dimensions
        dimensions = mask_voxel_data.get_dimensions()

        # Iterate through all dimensions of the mask
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                for z in range(dimensions[2]):
                    # If the mask is True at this position, add the coordinates
                    if mask_voxel_data.get_value_at(x, y, z):
                        coordinates.append((x, y, z))

        return coordinates


class AtlasSegmentation(MRIData[int]):
    """
    Represents a segmentation of an atlas.

    Parameters
    ----------
    mri_exam_id : MRIExamId
        Unique identifier of the MRI exam which this data belongs to
    voxel_data : VoxelData[int]
        Provider for voxel data
    atlas : Atlas
        The atlas used for segmentation
    """

    def __init__(self,
                 voxel_data: VoxelData[int],
                 mri_exam_id: MRIExamId,
                 atlas: Atlas) -> None:
        super().__init__(voxel_data=voxel_data,
                         mri_exam_id=mri_exam_id,
                         name=f"{atlas.name}_segmentation")
        self.atlas = atlas

    def create_mask(self, labels: List[int]) -> "Mask":
        """
        Create a mask for the specified labels.

        Parameters
        ----------
        labels : List[int]
            The labels to include in the mask

        Returns
        -------
        Mask
            A mask representing the specified labels
        """
        mask_voxel_data = self.get_voxel_data().filter_by_values(labels)
        return Mask(mri_exam_id=self.mri_exam_id,
                    voxel_data=mask_voxel_data)


@dataclass
class MRIExam:
    """
    A complete MRI examination.

    Contains all the MRI data (sequences, maps, masks) associated with a subject's exam.

    Parameters
    ----------
    id : MRIExamId
        Unique identifier of the exam
    subject_id : SubjectId
        Identifier of the subject who underwent the exam
    data : List[MRIData]
        List of all MRI data associated with this exam
    """

    id: MRIExamId
    subject_id: SubjectId
    data: List[MRIData] = field(default_factory=list)

    def __repr__(self) -> str:  # pragma: no cover
        """
        String representation of the MRIExam object.

        Returns
        -------
        str
            String representation of the MRIExam object
        """
        return f"MRIExam(id={self.id})"

    @classmethod
    def from_string_exam_id(cls, exam_id: str, data: Optional[List[MRIData]] = None) -> MRIExam:
        """
        Factory method that creates an MRIExam from a string exam id.

        Parameters
        ----------
        exam_id : str
            Unique identifier of the exam
        data : Optional[List[MRIData]]
            List of all MRI data associated with this exam
        """
        mri_exam_id = MRIExamId(exam_id)
        subject_id = mri_exam_id.to_subject_id()
        return cls(mri_exam_id, subject_id, data or [])

    def get_all_mri_data(self) -> list[MRIData]:
        """
        Get all MRI data associated with this exam.

        Returns
        -------
        Optional[MRIData]
            The requested data if found, None otherwise
        """
        return self.data

    def get_dti_map(self, metric: DTIMetric) -> DTIMap:
        """
        Retrieve the DTI map for a specific metric.

        Parameters
        ----------
        metric : DTIMetric
            The type of DTI metric to retrieve

        Returns
        -------
        MRIData
            The DTI map for the specified metric
        """
        for mri_data in self.data:
            if isinstance(mri_data, DTIMap) and mri_data.dti_metric == metric:
                return mri_data

        raise LookupError(f"DTI map not found for metric '{metric}' in MRI exam '{self.id}'")

    def get_segmented_dti_abnormal_values(self, dti_metric: DTIMetric) -> DTIAbnormalValues:
        """
        Retrieve the segmented DTI abnormal values for a specific metric.

        Parameters
        ----------
        dti_metric : DTIMetric
            The type of DTI metric to retrieve abnormal values for

        Returns
        -------
        DTIAbnormalValues
            The segmented DTI abnormal values for the specified metric
        """
        for mri_data in self.data:
            if isinstance(mri_data, DTIAbnormalValues) and mri_data.source_dti_map.dti_metric == dti_metric:
                return mri_data

        raise LookupError(f"Segmented DTI abnormal values not found for metric '{dti_metric}' in MRI exam '{self.id}'")

    def get_atlas_segmentation(self, atlas: Atlas) -> AtlasSegmentation:
        """
        Retrieve the segmentation for a specific atlas.

        Parameters
        ----------
        atlas : Atlas

        Returns
        -------
        AtlasSegmentation
            The atlas segmentation data
        """
        # look for atlas by atlas id
        for mri_data in self.data:
            if isinstance(mri_data, AtlasSegmentation) and mri_data.atlas.id == atlas.id:
                return mri_data

        raise LookupError(f"Atlas segmentation not found for atlas '{atlas.id}' in MRI exam '{self.id}'")

    def get_mask(self, roi: RegionOfInterest) -> Mask:
        """
        Create a mask for a given region of interest.

        Parameters
        ----------
        roi : RegionOfInterest
            The region of interest to create a mask for

        Returns
        -------
        Mask
            A mask representing the specified region of interest
        """
        # Get the atlas segmentation data for the ROI's atlas
        atlas_segmentation = self.get_atlas_segmentation(roi.atlas)
        if atlas_segmentation is None:
            raise LookupError(f"Atlas segmentation not found for atlas "
                              f"'{roi.atlas.id}' in MRI exam '{self.id}'")

        # Create a mask that includes all specified labels
        mask = atlas_segmentation.create_mask(roi.labels)

        return mask

    def extract_dti_values_for_region(
            self, dti_metric: DTIMetric, roi: RegionOfInterest
    ) -> List[float]:
        """
        Extract DTI metric values for a specific region of interest.

        Parameters
        ----------
        dti_metric : DTIMetric
            The type of DTI metric to extract (MD, FA, etc.)
        roi : RegionOfInterest
            The region of interest to extract values from

        Returns
        -------
        List[float]
            DTI values corresponding to the specified ROI
        """
        # Get the DTI metric data for the specified metric
        dti_map = self.get_dti_map(dti_metric)

        # Create a mask for the ROI
        mask = self.get_mask(roi)

        # Extract values using the mask
        dti_values = mask.extract_values_from(dti_map)

        return dti_values

    def add_mri_data(self, mri_data: MRIData) -> None:
        """
        Add MRI data to the MRI exam

        Parameters
        ----------
        mri_data : MRIData
            The MRI data to add to the exam

        Returns
        -------
        None
        """
        self.data.append(mri_data)


class AbnormalValueType(Enum):
    """
    Enum for the type of abnormal values.
    """
    HIGH = "high"
    LOW = "low"

    @classmethod
    def from_integer(cls, value: int) -> Optional['AbnormalValueType']:
        """
        Convert an integer value to AbnormalValueType.

        Parameters
        ----------
        value : int
            Integer value to convert (0, 1, or 2)

        Returns
        -------
        Optional[AbnormalValueType]
            Corresponding AbnormalValueType or None if value is 0

        Raises
        ------
        ValueError
            If the value is not 0, 1, or 2
        """
        if value == 0:
            return None
        elif value == 1:
            return cls.HIGH
        elif value == 2:
            return cls.LOW
        else:
            raise ValueError(f"Invalid integer value for conversion to AbnormalValueType: {value}")

    def to_integer(self) -> int:
        """
        Convert AbnormalValueType to integer.

        Returns
        -------
        int
            1 for LOW, 2 for HIGH
        """
        if self == self.HIGH:
            return 1
        elif self == self.LOW:
            return 2
        else:
            # This should never happen as we only have LOW and HIGH
            raise ValueError(f"Unknown AbnormalValueType: {self}")


class DTIAbnormalValues(MRIData[AbnormalValueType]):
    """
    Class to store the abnormal values in DTI images.
    """

    def __init__(self,
                 mri_exam_id: MRIExamId,
                 voxel_data: AbnormalVoxelData,
                 source_dti_map: DTIMap,
                 name: Optional[str] = None,
                 ) -> None:
        self.mri_exam_id = mri_exam_id
        self.voxel_data = voxel_data
        self.source_dti_map = source_dti_map
        self.name = name or f"abnormal_values_{source_dti_map.name}"

    @classmethod
    def from_dti_map(cls, dti_map: DTIMap, name: Optional[str] = None) -> DTIAbnormalValues:
        """
        Create a DTIAbnormalValues object from a DTIMap.
        """
        return cls(mri_exam_id=dti_map.mri_exam_id,
                   voxel_data=AbnormalVoxelData.from_source_voxel_data(dti_map.voxel_data),
                   source_dti_map=dti_map,
                   name=name or f"abnormal_values_{dti_map.name}",
                   )


class AbnormalVoxelData(VoxelData[AbnormalValueType]):
    """
    Implementation of VoxelData for abnormal DTI values.

    This class stores abnormal voxels in a dictionary, where only abnormal voxels
    are stored. Voxels not present in the dictionary are considered normal.

    Attributes
    ----------
    source_voxel_data : VoxelData[float]
        The source voxel data from which the abnormal values are derived.
    """

    def __init__(self,
                 source_voxel_data: VoxelData[float]
                 ) -> None:
        """
        Initialize with dimensions from the source voxel data.

        Parameters
        ----------
        source_voxel_data : VoxelData[float]
            The source voxel data from which the abnormal values are derived.
        """
        self.source_voxel_data = source_voxel_data

        # Dictionary to store abnormal voxels
        # Key: tuple (x, y, z), Value: AbnormalValueType (HIGH or LOW)
        self.abnormal_voxels: dict[tuple[int, int, int], AbnormalValueType] = {}

    @classmethod
    def from_source_voxel_data(cls, source_voxel_data: VoxelData[float]) -> AbnormalVoxelData:
        """
        Create an AbnormalVoxelData object from source VoxelData.

        Parameters
        ----------
        source_voxel_data: VoxelData[float]
            The source voxel data from which the abnormal values are derived.

        Returns
        -------
        AbnormalVoxelData
            The created AbnormalVoxelData object
        """
        return cls(source_voxel_data=source_voxel_data)

    def get_source_voxel_data(self) -> VoxelData[float]:
        """
        Get the source voxel data.

        Returns
        -------
        VoxelData[float]
            The source voxel data
        """
        return self.source_voxel_data

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
            raise ValueError(f"Coordinates ({x}, {y}, {z}) out of bounds. Dimensions: {self.get_dimensions()}")

        # Add to dictionary
        self.abnormal_voxels[(x, y, z)] = value

    def get_value_at(self, x: int, y: int, z: int) -> Optional[AbnormalValueType]:
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
        coords = (x, y, z)
        if not self._is_in_bounds(x, y, z):
            raise ValueError(f"Coordinates ({x}, {y}, {z}) out of bounds. Dimensions: {self.get_dimensions()}")

        if coords not in self.abnormal_voxels:
            return None

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
        x_bound, y_bound, z_bound = self.get_dimensions()
        return (0 <= x < x_bound and
                0 <= y < y_bound and
                0 <= z < z_bound)

    def get_dimensions(self) -> Tuple[int, int, int]:
        """
        Get the dimensions of the voxel data.

        Returns
        -------
        Tuple[int, int, int]
            Dimensions as (x, y, z)
        """
        return self.source_voxel_data.get_dimensions()

    def get_voxel_volume_in_ml(self) -> float:
        """
        Get the volume of a voxel in milliliters.

        Returns
        -------
        float
            Volume in milliliters
        """
        return self.source_voxel_data.get_voxel_volume_in_ml()

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
