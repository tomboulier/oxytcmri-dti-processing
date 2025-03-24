"""NIfTI adapter implementations."""

from typing import TypeVar, Tuple, Callable
from pathlib import Path

import nibabel as nib
import numpy as np

from oxytcmri.domain.entities.mri import VoxelData

T = TypeVar("T")


class InMemoryNumpyVoxelData(VoxelData[T]):
    """Voxel data stored in memory as a numpy array."""
    def __init__(self, data: np.ndarray = None, voxel_volume: float = None):
        """Initialize the InMemoryNumpyVoxelData object.

        Parameters
        ----------
        data : np.ndarray, optional
            Numpy array containing voxel data.
        """
        self._data = data
        self._voxel_volume = voxel_volume

    def get_value_at(self, x: int, y: int, z: int) -> T:
        """Get the value at the specified coordinates.

        Parameters
        ----------
        x : int
            X coordinate.
        y : int
            Y coordinate.
        z : int
            Z coordinate.

        Returns
        -------
        T
            Value at the specified coordinates.
        """
        return self._data[x, y, z]

    def get_dimensions(self) -> Tuple[int, int, int]:
        """Get the dimensions of the voxel data.

        Returns
        -------
        Tuple[int, int, int]
            Dimensions of the voxel data (x, y, z).
        """
        return self._data.shape

    def get_voxel_volume_in_ml(self) -> float:
        """Get the volume of a voxel in milliliters.

        Returns
        -------
        float
            Volume of a voxel in milliliters.
        """
        return self._voxel_volume

    def filter_values(self, condition: Callable[[T], bool]) -> VoxelData[bool]:
        """Create a boolean representation of voxel data based on a filtering condition.

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
        return InMemoryNumpyVoxelData(self._data[condition(self._data)], self._voxel_volume)


class NiftiVoxelData(VoxelData[T]):
    """Implementation of VoxelData for NIfTI files.

    Parameters
    ----------
    nifti_path : Path
        Path to the NIfTI file.
    """

    def __init__(self, nifti_path: Path):
        """Initialize the NiftiVoxelData object.

        Parameters
        ----------
        nifti_path : Path
            Path to the NIfTI file.
        """
        self.nifti_path = nifti_path
        self._img = nib.load(str(nifti_path))
        self._data = self._img.get_fdata()

    def get_value_at(self, x: int, y: int, z: int) -> T:
        """Get the value at the specified coordinates.

        Parameters
        ----------
        x : int
            X coordinate.
        y : int
            Y coordinate.
        z : int
            Z coordinate.

        Returns
        -------
        T
            Value at the specified coordinates.
        """
        # Check if the coordinates are within bounds
        dimensions = self.get_dimensions()
        if 0 <= x < dimensions[0] and 0 <= y < dimensions[1] and 0 <= z < dimensions[2]:
            return float(self._data[x, y, z])
        else:
            raise ValueError(
                f"Coordinates ({x}, {y}, {z}) are out of bounds. Shape is {dimensions}"
            )

    def get_dimensions(self) -> Tuple[int, int, int]:
        """Get the dimensions of the voxel data.

        Returns
        -------
        Tuple[int, int, int]
            Dimensions of the voxel data (x, y, z).
        """
        # Get the shape of the data array
        shape = self._data.shape

        # Return the first three dimensions (x, y, z)
        # Some NIfTI files might have a 4th dimension (time), which we ignore here
        return shape[0], shape[1], shape[2]

    def get_voxel_volume_in_ml(self) -> float:
        """Get the volume of a single voxel in milliliters (mL).

        1 mL = 1000 mm³

        Returns
        -------
        float
            Volume of a single voxel in milliliters (mL).
        """
        # Get the spatial dimensions of each voxel in mm
        # nibabel stores this information in the NIfTI file header
        # The header contains "zooms" which are the physical dimensions of voxels
        zooms = self._img.header.get_zooms()

        # Calculate the volume by multiplying the 3 dimensions
        # We only consider the first 3 dimensions (x, y, z)
        # because some files might have a 4th dimension (time)
        # Convert from mm³ to mL (division by 1000)
        volume = (zooms[0] * zooms[1] * zooms[2]) / 1000

        return float(volume)

    def filter_values(self, condition: Callable[[T], bool]) -> VoxelData[bool]:
        """
        Filter the voxel data based on a condition.

        Parameters
        ----------
        condition : Callable[[T], bool]
            A function that takes a voxel value and returns True if the voxel
            should be included in the filter.

        Returns
        -------
        VoxelData[bool]
            A boolean representation where voxels are True if they match the condition
        """
        # Create a boolean mask based on the condition
        mask = self._data.copy()
        mask[~condition(mask)] = False
        mask[condition(mask)] = True

        # Return a new InMemoryNumpyVoxelData object with the filtered data
        return InMemoryNumpyVoxelData(mask, self.get_voxel_volume_in_ml())
