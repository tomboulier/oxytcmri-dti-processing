"""
Unit tests for the STAPLE segmentation merger.
"""
import numpy
import unittest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from oxytcmri.domain.entities.mri import DTIMap, DTIMetric, MRIExamId
from oxytcmri.domain.use_cases.segment_dti_abnormal_values import DTIAbnormalValues, AbnormalValueType, AbnormalVoxelData
from oxytcmri.interface.mri.staple_segmenter import C3DSTAPLESegmentationMerger
from oxytcmri.interface.mri.voxel_data_adapters import InMemoryNumpyVoxelData, NiftiVoxelData
from oxytcmri.interface.mri.staple_segmenter import TemporaryNiftiIntegerVoxelData
from oxytcmri.tests.fixtures import path_to_test_data_folder


class TestC3DSTAPLESegmentationMerger:
    """Test suite for C3DSTAPLESegmentationMerger."""

    def test_merge(self):
        """Test that merge() correctly merges the segmentations."""
        dti_voxel_data = InMemoryNumpyVoxelData(
            data=numpy.ones((3, 3, 3), dtype=numpy.float32),
            voxel_volume=8.0,
        )
        dti_map = DTIMap(dti_metric=DTIMetric.from_acronym("FA"),
                         mri_exam_id=MRIExamId("02-01-t-mr-16022013"),
                         voxel_data=dti_voxel_data)

        # create first segmentation
        segmentation_1 = DTIAbnormalValues.from_dti_map(dti_map=dti_map)
        segmentation_1.voxel_data.set_value_at(0, 0, 0, AbnormalValueType.LOW)
        segmentation_1.voxel_data.set_value_at(0, 1, 0, AbnormalValueType.HIGH)

        # create second segmentation
        segmentation_2 = DTIAbnormalValues.from_dti_map(dti_map=dti_map)
        segmentation_2.voxel_data.set_value_at(0, 0, 1, AbnormalValueType.HIGH)
        segmentation_2.voxel_data.set_value_at(1, 0, 0, AbnormalValueType.LOW)

        list_of_segmentations = [segmentation_1, segmentation_2]

        # create the merger
        merger = C3DSTAPLESegmentationMerger()
        # merge the segmentations
        merged_segmentation = merger.merge(list_of_segmentations)

        # check the merged segmentation
        assert isinstance(merged_segmentation, DTIAbnormalValues)


class TestTemporaryNiftiIntegerVoxelData:
    """Unit tests for TemporaryNiftiIntegerVoxelData."""

    @pytest.fixture
    def md_map_file_path(self) -> Path:
        """Returns the path to the MD map NIfTI file."""
        file_path = path_to_test_data_folder() / "dti-data/Healthy/C01/01_01v_mr_170913/MD_map.nii.gz"
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'")
        return file_path

    @pytest.fixture
    def abnormal_voxel_data(self, md_map_file_path: Path) -> AbnormalVoxelData:
        """Fixture to create a mock AbnormalVoxelData object."""
        nifti_voxel_data = NiftiVoxelData(md_map_file_path)  # type: ignore
        result = AbnormalVoxelData.from_voxel_data(nifti_voxel_data)
        
        # Add some test values to the AbnormalVoxelData
        result.set_value_at(0, 0, 0, AbnormalValueType.LOW)
        result.set_value_at(1, 1, 1, AbnormalValueType.HIGH)
        result.set_value_at(2, 2, 2, AbnormalValueType.HIGH)

        return result

    def test_conversion_from_abnormal_to_temporary(self, abnormal_voxel_data):
        """
        Test converting AbnormalVoxelData to TemporaryNiftiIntegerVoxelData.
        """
        temp_nifti = TemporaryNiftiIntegerVoxelData.from_abnormal_voxel_data(abnormal_voxel_data)
        
        # assert that the dimensions and voxel volume are set correctly
        assert temp_nifti.get_dimensions() == abnormal_voxel_data.get_dimensions()
        assert temp_nifti.get_voxel_volume_in_ml() == abnormal_voxel_data.get_voxel_volume_in_ml()

        # assert that the data is set correctly
        assert temp_nifti.get_value_at(0, 0, 0) == 1
        assert temp_nifti.get_value_at(1, 1, 1) == 2
        assert temp_nifti.get_value_at(2, 2, 2) == 2
        assert temp_nifti.get_value_at(0, 1, 1) == 0
