"""
Concrete implementation of SegmentationMerger using c3d command line tool with STAPLE algorithm.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import List, cast, Optional

import numpy

from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentationMerger, DTIAbnormalValues, \
    AbnormalVoxelData, AbnormalValueType
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData


class TemporaryNiftiIntegerVoxelData(NiftiVoxelData[int]):
    """
    Temporary NiftiVoxelData class for storing integer voxel data.
    This class is used to create a temporary NIfTI file for the c3d command line tool.
    """
    def __init__(self, nifti_path: Path, source_voxel_data: NiftiVoxelData):
        """
        Initialize the TemporaryNiftiIntegerVoxelData object.

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
    def from_abnormal_voxel_data(cls, abnormal_voxel_data: AbnormalVoxelData) -> TemporaryNiftiIntegerVoxelData:
        """
        Initialize the TemporaryNiftiIntegerVoxelData object.

        Parameters
        ----------
        abnormal_voxel_data : AbnormalVoxelData
            AbnormalVoxelData object containing the voxel data.
        """
        # Convert the AbnormalVoxelData to a numpy array of integers
        integer_data = cls._convert_to_integer_numpy_array(abnormal_voxel_data)

        source_voxel_data = abnormal_voxel_data.get_source_voxel_data()
        if not isinstance(source_voxel_data, NiftiVoxelData):
            raise ValueError("Source voxel data must be of type NiftiVoxelData")

        # Create a NiftiVoxelData object with the integer data
        temp_nifti = NiftiVoxelData.create_with_same_metadata(
            source_nifti=cast(NiftiVoxelData, source_voxel_data),
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
        Convert the TemporaryNiftiIntegerVoxelData to AbnormalVoxelData.

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


class C3DSTAPLESegmentationMerger(SegmentationMerger):
    """
    Implementation of SegmentationMerger using c3d-tools STAPLE algorithm.

    STAPLE (Simultaneous Truth and Performance Level Estimation) is an algorithm
    for merging multiple segmentations into a consensus segmentation.
    """

    def merge(self, segmentations: List[DTIAbnormalValues]) -> DTIAbnormalValues:
        """
        Merge multiple segmentations using `c3d` command line tool with STAPLE algorithm.

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

        # get MRIExamId from the first segmentation (after checking they are all the same)
        # and extract list of TemporaryNiftiIntegerVoxelData objects
        temporary_nifti_files = []
        mri_exam_id = segmentations[0].mri_exam_id
        source_dti_map = segmentations[0].source_dti_map
        for segmentation in segmentations:
            if segmentation.mri_exam_id != mri_exam_id:
                raise ValueError("All segmentations must have the same MRIExamId")
            temp_nifti = TemporaryNiftiIntegerVoxelData.from_abnormal_voxel_data(segmentation.voxel_data)
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

    def _merge_with_c3d(self, temporary_nifti_files: List[TemporaryNiftiIntegerVoxelData]) -> TemporaryNiftiIntegerVoxelData:
        """
        Merge multiple NIfTI files using c3d STAPLE algorithm.
        
        Parameters
        ----------
        temporary_nifti_files : List[TemporaryNiftiIntegerVoxelData]
            List of temporary NIfTI files to merge
        
        Returns
        -------
        TemporaryNiftiIntegerVoxelData
            Merged segmentation
        
        Raises
        ------
        RuntimeError
            If the c3d command fails
        """
        # Check if there are files to merge
        if not temporary_nifti_files:
            raise ValueError("No files to merge")

        # get source voxel data from the first file
        source_voxel_data = temporary_nifti_files[0].source_voxel_data
        
        # Create a temporary file for the output
        with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as tmp_file:
            output_path = Path(tmp_file.name)
        
        # Build the c3d command
        cmd = ["c3d"]
        for temp_file in temporary_nifti_files:
            cmd.append(str(temp_file.nifti_path))
        
        # Add STAPLE parameters (1 is the confidence level)
        cmd.extend(["-staple", "1", "-o", str(output_path)])
        
        try:
            # Execute the command
            process = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"c3d command failed: {e.stderr}")
        
        # Create a new TemporaryNiftiIntegerVoxelData with the output file
        return TemporaryNiftiIntegerVoxelData(
            nifti_path=output_path,
            source_voxel_data=source_voxel_data
        )
