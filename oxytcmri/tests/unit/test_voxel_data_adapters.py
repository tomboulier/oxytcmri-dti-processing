"""Tests for the NIfTI adapter implementations."""

from pathlib import Path

from oxytcmri.domain.entities.mri import VoxelData
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData


class TestNiftiVoxelData:
    """Tests for the NiftiVoxelData adapter."""
    
    def test_create_nifti_voxel_data(self):
        """Test that we can create a NiftiVoxelData instance."""
        test_file = Path(__file__).parent.parent/"test-data/dti-data/Healthy/C01/01_01v_mr_170913/MD_map.nii.gz"

        # Check file exists
        assert test_file.exists()
        
        # Create NiftiVoxelData instance
        voxel_data = NiftiVoxelData[float](test_file)
        
        # Check instance type
        assert isinstance(voxel_data, VoxelData)