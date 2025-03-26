"""Tests for the NIfTI adapter implementations."""

from pathlib import Path
from pytest import fixture, approx, raises

from oxytcmri.domain.entities.mri import VoxelData
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData


class TestNiftiVoxelData:
    """Tests for the NiftiVoxelData adapter."""

    @fixture
    def md_map_file_path(self) -> Path:
        """Returns the path to the MD map NIfTI file."""
        test_data_folder = Path(__file__).resolve().parents[3]
        file_path = test_data_folder / "test-data/dti-data/Healthy/C01/01_01v_mr_170913/MD_map.nii.gz"
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
        assert nifti_voxel_data.get_value_at(0, 0, 0) == 0.0, (
            "Value at (0, 0, 0) should be 0."
        )
        assert nifti_voxel_data.get_value_at(32, 32, 32) == 131.0, (
            "Value at (32, 32, 32) should be 131."
        )

    def test_out_of_bounds(self, nifti_voxel_data):
        """Test that we get an error when coordinates are out of bounds."""
        with raises(ValueError):
            nifti_voxel_data.get_value_at(63, 86, 64)

    def test_get_voxel_volume_in_ml(self, nifti_voxel_data):
        """Test that we can get the volume of a voxel in milliliters."""
        assert nifti_voxel_data.get_voxel_volume_in_ml() == approx(0.0006815, abs=1e-6)

    def test_filter_values(self, nifti_voxel_data):
        """Test that we can filter values based on a condition."""
        filtered_values = nifti_voxel_data.filter_values(lambda x: x < 0)
        dimensions = filtered_values.get_dimensions()
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                for z in range(dimensions[2]):
                    assert not filtered_values.get_value_at(x, y, z), (
                        f"Filtered value at ({x}, {y}, {z}) should be False."
                    )
