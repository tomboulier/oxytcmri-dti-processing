"""NIfTI adapter implementations."""

from typing import TypeVar, Generic, List, Tuple
from pathlib import Path

from oxytcmri.domain.entities.mri import VoxelData

T = TypeVar('T')

class NiftiVoxelData(VoxelData[T]):
    """Implementation of VoxelData for NIfTI files."""
    
    def __init__(self, nifti_path: Path):
        self.nifti_path = nifti_path
    
    def get_value_at(self, x: int, y: int, z: int) -> T:
        return 0  # TODO
    
    def get_dimensions(self) -> Tuple[int, int, int]:
        return (10, 10, 10)  # TODO
    
    def get_voxel_volume(self) -> float:
        return 0.008  # TODO