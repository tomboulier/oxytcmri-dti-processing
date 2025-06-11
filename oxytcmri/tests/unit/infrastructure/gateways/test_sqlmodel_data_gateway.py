from unittest.mock import MagicMock

import pytest
import os
import tempfile

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMap, DTIMetric, MRIExamId, DTIAbnormalValues, AbnormalVoxelData
from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData, NiftiAbnormalVoxelData
from oxytcmri.tests.fixtures import path_to_test_data_folder


class TestSQLModelSQLiteDataGateway:

    @pytest.fixture
    def temp_db_path(self):
        """Creates a temporary database file for testing."""
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)  # Close the file descriptor

        yield path

        # Clean up after the test
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def gateway(self, temp_db_path):
        """Creates a gateway instance with a temporary database."""
        gateway = SQLModelSQLiteDataGateway(temp_db_path)
        return gateway

    def test_find_all_empty(self, gateway):
        """Tests that find_all returns an empty list when the database is empty."""
        # Act
        centers = gateway.find_all(Center)

        # Assert
        assert isinstance(centers, list)
        assert len(centers) == 0

    def test_save_and_find_by_id(self, gateway):
        """Tests saving an entity and retrieving it by ID."""
        # Arrange
        center = Center(id=1, name="Test Center")

        # Act
        gateway.save(center)
        found_center = gateway.find_by_id(Center, 1)

        # Assert
        assert found_center is not None
        assert found_center.id == 1
        assert found_center.name == "Test Center"

    def test_save_and_find_all(self, gateway):
        """Tests saving multiple entities and retrieving them all."""
        # Arrange
        centers = [
            Center(id=1, name="Center 1"),
            Center(id=2, name="Center 2"),
            Center(id=3, name="Center 3")
        ]

        # Act
        for center in centers:
            gateway.save(center)

        found_centers = gateway.find_all(Center)

        # Assert
        assert len(found_centers) == 3

        # Check that all centers were saved correctly
        center_ids = [c.id for c in found_centers]
        assert 1 in center_ids
        assert 2 in center_ids
        assert 3 in center_ids

        # Check the names as well
        for center in found_centers:
            if center.id == 1:
                assert center.name == "Center 1"
            elif center.id == 2:
                assert center.name == "Center 2"
            elif center.id == 3:
                assert center.name == "Center 3"

    def test_find_by_filters(self, gateway):
        """Tests finding an entity by filters."""
        # Arrange
        center1 = Center(id=1, name="Center A")
        center2 = Center(id=2, name="Center B")
        gateway.save(center1)
        gateway.save(center2)

        # Act
        found_center = gateway.find_by_filters(Center, {"name": "Center A"})

        # Assert
        assert found_center is not None
        assert found_center.id == 1
        assert found_center.name == "Center A"

    def test_update_entity(self, gateway):
        """Tests updating an existing entity."""
        # Arrange
        center = Center(id=1, name="Original Name")
        gateway.save(center)

        # Act
        updated_center = Center(id=1, name="Updated Name")
        gateway.save(updated_center)

        # Assert
        found_center = gateway.find_by_id(Center, 1)
        assert found_center is not None
        assert found_center.name == "Updated Name"

    def test_delete_entity(self, gateway):
        """Tests deleting an entity."""
        # Arrange
        center = Center(id=1, name="Test Center")
        gateway.save(center)

        # Act
        gateway.delete(center)

        # Assert
        found_center = gateway.find_by_id(Center, 1)
        assert found_center is None

    def test_entity_not_found(self, gateway):
        """Tests that find_by_id returns None when the entity doesn't exist."""
        # Act
        found_center = gateway.find_by_id(Center, 999)

        # Assert
        assert found_center is None
    
    def test_save_with_abnormal_voxel_data(self, gateway):
        """Test saving DTIAbnormalValues with AbnormalVoxelData."""
        # Arrange
        source_voxel_data = NiftiVoxelData(nifti_path=path_to_test_data_folder() / "AbnormalVoxelData/MD_map.nii.gz")
        source_dti_map = DTIMap(
            mri_exam_id=MRIExamId("01_02t_mr_150328"),
            voxel_data=source_voxel_data,
            dti_metric=DTIMetric.MD)

        abnormal_voxel_data = NiftiAbnormalVoxelData(
            nifti_path=path_to_test_data_folder() / "AbnormalVoxelData/MD_segmentation.nii.gz",
            source_voxel_data=source_voxel_data,
        )

        dti_abnormal_values = DTIAbnormalValues(
            mri_exam_id=MRIExamId("01_02t_mr_150328"),
            name="MD_abnormal",
            voxel_data=abnormal_voxel_data,
            source_dti_map=source_dti_map
        )
        # Act
        gateway.save(dti_abnormal_values)
