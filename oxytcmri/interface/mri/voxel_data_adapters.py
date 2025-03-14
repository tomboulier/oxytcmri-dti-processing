"""NIfTI adapter implementations."""

from typing import TypeVar, Tuple
from pathlib import Path

import nibabel as nib

from oxytcmri.domain.entities.mri import VoxelData

T = TypeVar('T')

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
            raise ValueError(f"Coordinates ({x}, {y}, {z}) are out of bounds. Shape is {dimensions}")
    
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
        return (shape[0], shape[1], shape[2])
    
    def get_voxel_volume(self) -> float:
        """Get the volume of a single voxel in cubic millimeters.
        
        Returns
        -------
        float
            Volume of a single voxel in cubic millimeters.
        """
        return 0.008  # TODO