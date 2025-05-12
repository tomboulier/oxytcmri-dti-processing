"""
Concrete implementation of SegmentationMerger using c3d command line tool with STAPLE algorithm.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, cast

import numpy

from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentationMerger, DTIAbnormalValues, \
    AbnormalVoxelData, AbnormalValueType
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData

logger = logging.getLogger(__name__)


class AbnormalToIntegerVoxelDataAdapter(NiftiVoxelData[int]):
    """
    Adapter class to convert AbnormalVoxelData to NiftiVoxelData with integer values.
    """

    def __init__(self, nifti_path: Path, source_voxel_data: NiftiVoxelData):
        """
        Initialize the AbnormalToIntegerVoxelDataAdapter object.

        Parameters
        ----------
        nifti_path : Path
            Path to the NIfTI file.
        source_voxel_data : NiftiVoxelData
            Source NIfTI voxel data.
        """
        super().__init__(nifti_path=nifti_path)
        self.source_voxel_data = source_voxel_data

    @classmethod
    def from_abnormal_voxel_data(cls,
                                 abnormal_voxel_data: AbnormalVoxelData,
                                 nifti_path: Path) -> AbnormalToIntegerVoxelDataAdapter:
        """
        Initialize the AbnormalToIntegerVoxelDataAdapter object.

        Parameters
        ----------
        abnormal_voxel_data : AbnormalVoxelData
            AbnormalVoxelData object containing the voxel data.
        nifti_path : Path
            Path to the NIfTI file.
        """
        # Convert the AbnormalVoxelData to a numpy array of integers
        integer_data = cls._convert_to_integer_numpy_array(abnormal_voxel_data)

        source_voxel_data = abnormal_voxel_data.get_source_voxel_data()
        if not isinstance(source_voxel_data, NiftiVoxelData):
            raise ValueError("Source voxel data must be of type NiftiVoxelData")

        # Create a NiftiVoxelData object with the integer data
        temp_nifti = NiftiVoxelData.create_with_same_metadata(
            source_nifti=cast(NiftiVoxelData, source_voxel_data),
            output_path=nifti_path,
            data=integer_data,
        )

        return cls(nifti_path=temp_nifti.nifti_path, source_voxel_data=source_voxel_data)

    @staticmethod
    def _convert_to_integer_numpy_array(voxel_data: AbnormalVoxelData) -> numpy.ndarray:
        """
        Convert the AbnormalVoxelData to a numpy array of integers.

        Parameters
        ----------
        voxel_data : AbnormalVoxelData
            AbnormalVoxelData object containing the voxel data.

        Returns
        -------
        numpy.ndarray
            Numpy array of integers representing the voxel data.
        """
        data_dimensions = voxel_data.get_dimensions()

        # Create a numpy array of the same shape as the original data
        data = numpy.zeros(data_dimensions, dtype=numpy.int32)

        # Set the values based on the AbnormalValueType
        for x in range(data_dimensions[0]):
            for y in range(data_dimensions[1]):
                for z in range(data_dimensions[2]):
                    value = voxel_data.get_value_at(x, y, z)
                    if value == AbnormalValueType.LOW:
                        data[x, y, z] = 1
                    elif value == AbnormalValueType.HIGH:
                        data[x, y, z] = 2
                    elif value is None:
                        data[x, y, z] = 0
                    else:
                        raise ValueError(f"Invalid value in voxel data {voxel_data} "
                                         f"at (x,y,z) = ({x}, {y}, {z}): {value}")

        return data

    def to_abnormal_voxel_data(self) -> AbnormalVoxelData:
        """
        Convert the AbnormalToIntegerVoxelDataAdapter to AbnormalVoxelData.

        Returns
        -------
        AbnormalVoxelData
            AbnormalVoxelData object containing the voxel data.
        """
        # Create a new AbnormalVoxelData object with the same dimensions and voxel volume
        abnormal_voxel_data = AbnormalVoxelData.from_source_voxel_data(self.source_voxel_data)

        # Set the values based on the numpy array
        dimensions = self.get_dimensions()
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                for z in range(dimensions[2]):
                    value = self.get_value_at(x, y, z)
                    rounded_value = numpy.round(value)
                    if abs(rounded_value - value) > 0.1:
                        raise ValueError(f"Value in voxel data {self} "
                                         f"at (x,y,z) = ({x}, {y}, {z}) is not an integer: {value}")
                    if rounded_value == 1:
                        abnormal_voxel_data.set_value_at(x, y, z, AbnormalValueType.LOW)
                    elif rounded_value == 2:
                        abnormal_voxel_data.set_value_at(x, y, z, AbnormalValueType.HIGH)
                    elif rounded_value != 0:
                        raise ValueError(f"Invalid value in voxel data {self} "
                                         f"at (x,y,z) = ({x}, {y}, {z}): {value}")
        return abnormal_voxel_data


class TemporaryFilesHandler:
    """
    Handler for temporary NIfTI files used during segmentation merging.

    This class provides utilities for creating temporary files and ensuring
    they are properly cleaned up when no longer needed.
    """

    def __init__(self):
        """
        Initialize an empty list to track temporary files.
        """
        self.temp_files: List[Path] = []

    def create_temp_nifti_file(self) -> Path:
        """
        Create a temporary NIfTI file for storing segmentation data.

        The file path is tracked for later cleanup.

        Returns
        -------
        Path
            Path to the temporary NIfTI file.
        """
        with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as tmp_file:
            path = Path(tmp_file.name)
            self.temp_files.append(path)
            return path

    def clean_up_temporary_files(self) -> None:
        """
        Remove all temporary files created by this handler.

        This method should be called when the temporary files are no longer needed,
        typically after the segmentation merging process is complete.
        """
        for file_path in self.temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError as e:
                # Log the error but continue with other files
                logger.error(f"Error removing temporary file {file_path}: {e}")

        # Clear the list of temporary files
        self.temp_files.clear()


class C3DSTAPLESegmentationMerger(SegmentationMerger):
    """
    Implementation of SegmentationMerger using c3d-tools STAPLE algorithm.

    STAPLE (Simultaneous Truth and Performance Level Estimation) is an algorithm
    for merging multiple segmentations into a consensus segmentation.
    """
    
    def __init__(self):
        """
        Initialize the merger with a temporary files handler.
        """
        self.temp_files_handler = TemporaryFilesHandler()

    def merge(self, segmentations: List[DTIAbnormalValues]) -> DTIAbnormalValues:
        """
        Merge multiple segmentations using `c3d` command line tool with STAPLE algorithm.

        Here is the process:
        List of `AbnormalVoxelData` (semantic values LOW/HIGH)
        ↓ (convert to)
        List `TemporaryNiftiIntegerVoxelData` (integer values 0/1/2 in NIfTI files)
        ↓ (process by `c3d`)
        `TemporaryNiftiIntegerVoxelData` (merged segmentation)
        ↓ (convert to)
        `AbnormalVoxelData` (back to semantic values LOW/HIGH)

        Sources
        -------
        - c3d documentation: https://www.itksnap.org/pmwiki/pmwiki.php?n=Convert3D.Convert3D
        - STAPLE algorithm: https://ieeexplore.ieee.org/document/1309714

        Parameters
        ----------
        segmentations : List[DTIAbnormalValues]
            List of segmentations to merge

        Returns
        -------
        DTIAbnormalValues
            Merged segmentation

        Raises
        ------
        ValueError
            If the segmentations list is empty
        RuntimeError
            If the c3d command fails
        """
        if not segmentations:
            raise ValueError("Cannot merge empty list of segmentations")

        try:
            # get MRIExamId from the first segmentation (after checking they are all the same)
            # and extract list of AbnormalToIntegerVoxelDataAdapter objects
            temporary_nifti_files = []
            mri_exam_id = segmentations[0].mri_exam_id
            source_dti_map = segmentations[0].source_dti_map
            for segmentation in segmentations:
                if segmentation.mri_exam_id != mri_exam_id:
                    raise ValueError("All segmentations must have the same MRIExamId")
                temp_nifti = AbnormalToIntegerVoxelDataAdapter.from_abnormal_voxel_data(
                    abnormal_voxel_data=segmentation.voxel_data,
                    nifti_path=self.temp_files_handler.create_temp_nifti_file(),
                )
                temporary_nifti_files.append(temp_nifti)

            nifti_merged_segmentation = self._merge_with_c3d(temporary_nifti_files)

            # create a new DTIAbnormalValues object with the merged segmentation
            merged_segmentation = nifti_merged_segmentation.to_abnormal_voxel_data()

            result = DTIAbnormalValues(
                mri_exam_id=mri_exam_id,
                source_dti_map=source_dti_map,
                voxel_data=merged_segmentation,
            )

            return result
        finally:
            # Clean up temporary files whether the operation succeeded or failed
            self.temp_files_handler.clean_up_temporary_files()

    @staticmethod
    def _merge_with_c3d(voxel_data_list: List[AbnormalToIntegerVoxelDataAdapter]) -> AbnormalToIntegerVoxelDataAdapter:
        """
        Merge multiple NIfTI files using c3d STAPLE algorithm.
        
        Parameters
        ----------
        voxel_data_list : List[AbnormalToIntegerVoxelDataAdapter]
            List of temporary NIfTI files to merge
        
        Returns
        -------
        AbnormalToIntegerVoxelDataAdapter
            Merged segmentation
        
        Raises
        ------
        RuntimeError
            If the c3d command fails
        """
        # Check if there are files to merge
        if not voxel_data_list:
            raise ValueError("No files to merge")

        # get source voxel data from the first file
        source_voxel_data = voxel_data_list[0].source_voxel_data

        # Create file for the output, in the same directory as the source
        source_dti_metric = source_voxel_data.get_filename_without_extension().removesuffix("_map")
        output_path = source_voxel_data.get_parent_directory() / (f"{source_dti_metric}"
                                                                  f"_segmentation"
                                                                  f".nii.gz")

        # Build the c3d command
        cmd = ["c3d"]
        for temp_file in voxel_data_list:
            cmd.append(str(temp_file.nifti_path))

        # Add STAPLE parameters (1 is the confidence level)
        cmd.extend(["-staple", "1", "-o", str(output_path)])

        try:
            # Execute the command
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"c3d command failed: {e.stderr}")

        # Create a new AbnormalToIntegerVoxelDataAdapter with the output file
        return AbnormalToIntegerVoxelDataAdapter(
            nifti_path=output_path,
            source_voxel_data=source_voxel_data
        )

    @staticmethod
    def _create_temp_nifti_file() -> Path:
        """
        Create a temporary NIfTI file for storing the segmentation.

        Returns
        -------
        Path
            Path to the temporary NIfTI file.
        """
        with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as tmp_file:
            return Path(tmp_file.name)
