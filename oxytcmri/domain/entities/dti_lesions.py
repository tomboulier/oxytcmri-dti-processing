from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple, Callable

from oxytcmri.domain.entities.mri import MRIData, MRIExamId, DTIMap, VoxelData


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
