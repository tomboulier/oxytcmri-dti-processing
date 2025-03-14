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
        
    def test_get_value_at(self, nifti_voxel_data):
        """Test that we can get the value at specific coordinates."""
        assert nifti_voxel_data.get_value_at(0, 0, 0) == 0., "Value at (0, 0, 0) should be 0."
        assert nifti_voxel_data.get_value_at(32, 32, 32) == 131., "Value at (32, 32, 32) should be 131."
        
    def test_get_voxel_volume(self, nifti_voxel_data):
        """Test que nous pouvons obtenir le volume d'un voxel."""
        volume = nifti_voxel_data.get_voxel_volume()
        assert isinstance(volume, float), "Le volume devrait être un nombre à virgule flottante"
        assert volume > 0, "Le volume devrait être positif"
        # Les fichiers DTI ont généralement des voxels d'environ 2mm de côté
        # donc un volume d'environ 8mm³
        assert 1 < volume < 20, "Le volume devrait être dans une plage raisonnable pour l'IRM cérébrale"