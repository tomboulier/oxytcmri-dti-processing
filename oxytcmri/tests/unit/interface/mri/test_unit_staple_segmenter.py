"""
Unit tests for the STAPLE segmentation merger.
"""
from typing import List

import numpy
import unittest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from oxytcmri.domain.entities.mri import DTIMap, DTIMetric, MRIExamId
from oxytcmri.domain.use_cases.segment_dti_abnormal_values import DTIAbnormalValues, AbnormalValueType, \
    AbnormalVoxelData
from oxytcmri.interface.mri.staple_segmenter import C3DSTAPLESegmentationMerger
from oxytcmri.interface.mri.voxel_data_adapters import InMemoryNumpyVoxelData, NiftiVoxelData
from oxytcmri.interface.mri.staple_segmenter import AbnormalToIntegerVoxelDataAdapter
from oxytcmri.tests.fixtures import path_to_test_data_folder


def get_md_map_nifti_voxel_data_from_mri_exam_id(mri_exam_id: MRIExamId) -> NiftiVoxelData:
    """Returns the path to the MD map NIfTI file."""
    file_path = path_to_test_data_folder() / f"NiftiFoldersMRIExamRepository/{str(mri_exam_id)}/MD_map.nii.gz"
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: '{file_path}'")
    return NiftiVoxelData(file_path)


class TestC3DSTAPLESegmentationMerger:
    """Test suite for C3DSTAPLESegmentationMerger."""

    @pytest.fixture
    def segmentations(self) -> List[DTIAbnormalValues]:
        """Fixture to create mock segmentations for testing."""
        mri_exam_id = MRIExamId("01_02t_mr_150328")
        nifti_voxel_data = get_md_map_nifti_voxel_data_from_mri_exam_id(mri_exam_id)
        dti_map = DTIMap(dti_metric=DTIMetric.from_acronym("MD"),
                         mri_exam_id=mri_exam_id,
                         voxel_data=nifti_voxel_data)

        # create first segmentation
        segmentation_1 = DTIAbnormalValues.from_dti_map(dti_map=dti_map,
                                                        name=f"{dti_map.mri_exam_id}_MD_segmentation_1")
        segmentation_1.voxel_data.set_value_at(0, 0, 0, AbnormalValueType.LOW)
        segmentation_1.voxel_data.set_value_at(0, 1, 0, AbnormalValueType.HIGH)

        # create second segmentation
        segmentation_2 = DTIAbnormalValues.from_dti_map(dti_map=dti_map,
                                                        name=f"{dti_map.mri_exam_id}_MD_segmentation_2")
        segmentation_2.voxel_data.set_value_at(0, 0, 1, AbnormalValueType.HIGH)
        segmentation_2.voxel_data.set_value_at(1, 0, 0, AbnormalValueType.LOW)

        return [segmentation_1, segmentation_2]

    def test_merge(self, segmentations: List[DTIAbnormalValues]) -> None:
        """Test that merge() correctly merges the segmentations."""
        # create the merger
        merger = C3DSTAPLESegmentationMerger()
        # merge the segmentations
        merged_segmentation = merger.merge(segmentations)

        # check the merged segmentation
        assert isinstance(merged_segmentation, DTIAbnormalValues)


class TestTemporaryNiftiIntegerVoxelData:
    """Unit tests for AbnormalToIntegerVoxelDataAdapter."""

    @pytest.fixture
    def abnormal_voxel_data(self) -> AbnormalVoxelData:
        """Fixture to create a mock AbnormalVoxelData object."""
        mri_exam_id = MRIExamId("01_02t_mr_150328")
        nifti_voxel_data = get_md_map_nifti_voxel_data_from_mri_exam_id(mri_exam_id)
        result = AbnormalVoxelData.from_source_voxel_data(nifti_voxel_data)

        # Add some test values to the AbnormalVoxelData
        result.set_value_at(0, 0, 0, AbnormalValueType.LOW)
        result.set_value_at(1, 1, 1, AbnormalValueType.HIGH)
        result.set_value_at(2, 2, 2, AbnormalValueType.HIGH)

        return result

    def test_conversion_from_abnormal_to_temporary(self, abnormal_voxel_data):
        """
        Test converting AbnormalVoxelData to AbnormalToIntegerVoxelDataAdapter.
        """
        temp_nifti = AbnormalToIntegerVoxelDataAdapter.from_abnormal_voxel_data(abnormal_voxel_data)

        # assert that the dimensions and voxel volume are set correctly
        assert temp_nifti.get_dimensions() == abnormal_voxel_data.get_dimensions()
        assert temp_nifti.get_voxel_volume_in_ml() == abnormal_voxel_data.get_voxel_volume_in_ml()

        # assert that the data is set correctly
        assert temp_nifti.get_value_at(0, 0, 0) == 1
        assert temp_nifti.get_value_at(1, 1, 1) == 2
        assert temp_nifti.get_value_at(2, 2, 2) == 2
        assert temp_nifti.get_value_at(0, 1, 1) == 0
