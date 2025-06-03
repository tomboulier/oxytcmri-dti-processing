"""
Unit tests for the STAPLE segmentation merger.
"""
import tempfile
from typing import List

import numpy
import unittest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from oxytcmri.domain.entities.mri import DTIMap, DTIMetric, MRIExamId
from oxytcmri.domain.entities.dti_lesions import DTIAbnormalValues, AbnormalVoxelData, AbnormalValueType
from oxytcmri.interface.mri.staple_segmenter import C3DSTAPLESegmentationMerger
from oxytcmri.interface.mri.voxel_data_adapters import InMemoryNumpyVoxelData, NiftiVoxelData
from oxytcmri.interface.mri.staple_segmenter import AbnormalToIntegerVoxelDataAdapter
from oxytcmri.tests.fixtures import path_to_test_data_folder


def path_to_mri_exam_folder(mri_exam_id: MRIExamId) -> Path:
    """Returns the path to the MRI exam folder."""
    return path_to_test_data_folder() / f"NiftiFoldersMRIExamRepository/{str(mri_exam_id)}"


def get_nifti_voxel_data(
        mri_exam_id: MRIExamId,
        nifti_filename: str,
) -> NiftiVoxelData:
    """
    Helper function to get the NiftiVoxelData object for a given MRI exam ID.

    Parameters
    ----------
    mri_exam_id : MRIExamId
        The MRI exam ID.
    nifti_filename : str
        The name of the NIfTI file to load.
    """
    file_path = path_to_mri_exam_folder(mri_exam_id) / nifti_filename
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: '{file_path}'")
    return NiftiVoxelData(file_path)


class TestC3DSTAPLESegmentationMerger:
    """Test suite for C3DSTAPLESegmentationMerger."""

    @pytest.fixture
    def segmentations(self) -> List[DTIAbnormalValues]:
        """Fixture to create mock segmentations for testing."""
        mri_exam_id = MRIExamId("01_02t_mr_150328")
        nifti_voxel_data = get_nifti_voxel_data(mri_exam_id, "MD_map.nii.gz")
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

        # mock the subprocess call to avoid actual execution
        merger._merge_with_c3d = lambda voxel_data_list: voxel_data_list[0]
        # merge the segmentations
        merger.merge(segmentations)

    def test_merge_with_c3d(self):
        """Test that _merge_with_c3d correctly merges the segmentations."""
        # create a mock merger
        merger = C3DSTAPLESegmentationMerger()

        # create mock voxel data
        mri_exam_id = MRIExamId("01_02t_mr_150328")
        source_voxel_data = get_nifti_voxel_data(mri_exam_id, "MD_map.nii.gz")
        voxel_data_1 = AbnormalToIntegerVoxelDataAdapter(
            nifti_path=path_to_mri_exam_folder(mri_exam_id) / "Pixyl_Staple_7_94.nii.gz",
            source_voxel_data=source_voxel_data,
        )
        voxel_data_2 = AbnormalToIntegerVoxelDataAdapter(
            nifti_path=path_to_mri_exam_folder(mri_exam_id) / "Pixyl_Staple_10_95.nii.gz",
            source_voxel_data=source_voxel_data,
        )
        voxel_data_list = [voxel_data_1, voxel_data_2]

        merged_voxel_data = merger._merge_with_c3d(voxel_data_list)

        assert merged_voxel_data is not None

        # delete the output file created by the merger
        merged_voxel_data.nifti_path.unlink()


class TestTemporaryNiftiIntegerVoxelData:
    """Unit tests for AbnormalToIntegerVoxelDataAdapter."""

    @pytest.fixture
    def abnormal_voxel_data(self) -> AbnormalVoxelData:
        """Fixture to create a mock AbnormalVoxelData object."""
        mri_exam_id = MRIExamId("01_02t_mr_150328")
        nifti_voxel_data = get_nifti_voxel_data(mri_exam_id, "MD_map.nii.gz")
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
        # create a temporary NIfTI file
        with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as tmp_file:
            temp_nifti_path = Path(tmp_file.name)
        temp_nifti = AbnormalToIntegerVoxelDataAdapter.from_abnormal_voxel_data(
            abnormal_voxel_data=abnormal_voxel_data,
            nifti_path=temp_nifti_path,
        )

        # assert that the dimensions and voxel volume are set correctly
        assert temp_nifti.get_dimensions() == abnormal_voxel_data.get_dimensions()
        assert temp_nifti.get_voxel_volume_in_ml() == abnormal_voxel_data.get_voxel_volume_in_ml()

        # assert that the data is set correctly
        assert temp_nifti.get_value_at(0, 0, 0) == AbnormalValueType.to_integer(AbnormalValueType.LOW)
        assert temp_nifti.get_value_at(1, 1, 1) == AbnormalValueType.to_integer(AbnormalValueType.HIGH)
        assert temp_nifti.get_value_at(2, 2, 2) == AbnormalValueType.to_integer(AbnormalValueType.HIGH)
        assert temp_nifti.get_value_at(0, 1, 1) == 0

        # clean up the temporary file
        temp_nifti.nifti_path.unlink()
