"""Tests for the NIfTI adapter implementations."""

from pathlib import Path
from pytest import fixture

from oxytcmri.domain.entities.mri import VoxelData
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData


class TestNiftiVoxelData:
    """Tests for the NiftiVoxelData adapter."""
    
    @fixture
    def md_map_file_path(self) -> Path:
        file_path = Path(__file__).parent.parent / "test-data/dti-data/Healthy/C01/01_01v_mr_170913/MD_map.nii.gz"
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'")
        return file_path

    @fixture
    def nifti_voxel_data(self, md_map_file_path) -> NiftiVoxelData[float]:
        return NiftiVoxelData[float](md_map_file_path)
    
    def test_create_nifti_voxel_data(self, nifti_voxel_data):
        """Test that we can create a NiftiVoxelData instance."""        
        # Check instance type
        assert isinstance(nifti_voxel_data, VoxelData)

    def test_get_dimensions(self, nifti_voxel_data):
        """Test that we can get the dimensions of the voxel data."""
        dimensions = nifti_voxel_data.get_dimensions()
        assert dimensions == (63, 86, 64)