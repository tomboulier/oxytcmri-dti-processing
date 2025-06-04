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

from oxytcmri.domain.entities.mri import VoxelData
from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentationMerger
from oxytcmri.domain.entities.dti_lesions import DTIAbnormalValues, AbnormalVoxelData, AbnormalValueType
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
                    if value is not None:
                        try:
                            data[x, y, z] = value.to_integer()
                        except ValueError as e:
                            raise ValueError(f"Invalid value in voxel data {voxel_data} "
                                             f"at (x,y,z) = ({x}, {y}, {z}): {value}") from e

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
                    self._convert_integer_voxel_to_abnormal_value_type(abnormal_voxel_data, x, y, z)

        return abnormal_voxel_data

    def _convert_integer_voxel_to_abnormal_value_type(self,
                                                      abnormal_voxel_data: AbnormalVoxelData,
                                                      x: int, y: int, z: int) -> None:
        """
        Convert an integer voxel value to AbnormalValueType and set it in the AbnormalVoxelData.

        Parameters
        ----------
        abnormal_voxel_data : AbnormalVoxelData
            AbnormalVoxelData object to set the value in.
        x,y,z : int
            Coordinates of the voxel in the 3D space.
        """
        value = self.get_value_at(x, y, z)
        # Verify the value is close to an integer
        rounded_value = numpy.round(value)
        if abs(rounded_value - value) > 0.25:
            message = (f"Rounding value in voxel data {self} at (x,y,z) = ({x}, {y}, {z}) "
                       f"from {value} to {rounded_value} "
                       f"to convert to AbnormalValueType. "
                       "This may indicate a precision issue in the data.")
            logger.warning(message)
        # Convert the integer to AbnormalValueType
        try:
            abnormal_type = AbnormalValueType.from_integer(int(rounded_value))
            if abnormal_type is not None:
                abnormal_voxel_data.set_value_at(x, y, z, abnormal_type)
        except ValueError as e:
            raise ValueError(f"Invalid value in voxel data {self} "
                             f"at (x,y,z) = ({x}, {y}, {z}): {value}") from e


class NiftiAbnormalVoxelData(AbnormalVoxelData, NiftiVoxelData[int]):
    """
    NiftiAbnormalVoxelData extends AbnormalVoxelData with NiftiVoxelData functionalities.
    """

    def __init__(self,
                 source_voxel_data: VoxelData[float],
                 nifti_path: Path) -> None:
        """
        Initialize the NiftiAbnormalVoxelData object.

        Parameters
        ----------
        source_voxel_data : VoxelData[float]
            Source voxel data from which the abnormal values are derived.
        nifti_path : Path
            Path to the NIfTI file containing the voxel data.
        """
        # Initialize AbnormalVoxelData with the source voxel data
        AbnormalVoxelData.__init__(self, source_voxel_data)

        # Initialize NiftiVoxelData with the NIfTI file path
        NiftiVoxelData.__init__(self, nifti_path)


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
        logger.info(f"Merging {len(segmentations)} segmentations with c3d STAPLE algorithm")
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
                temporary_path = self.temp_files_handler.create_temp_nifti_file()
                temp_nifti = AbnormalToIntegerVoxelDataAdapter.from_abnormal_voxel_data(
                    abnormal_voxel_data=segmentation.voxel_data,
                    nifti_path=temporary_path,
                )
                logger.debug(f"Temporary NIfTI file created in {temp_nifti.nifti_path} "
                             f"for segmentation {segmentation.mri_exam_id}")
                temporary_nifti_files.append(temp_nifti)

            nifti_merged_segmentation = self._merge_with_c3d(temporary_nifti_files)

            result = DTIAbnormalValues(
                mri_exam_id=mri_exam_id,
                source_dti_map=source_dti_map,
                voxel_data=nifti_merged_segmentation,
            )

            return result

        finally:
            # Clean up temporary files whether the operation succeeded or failed
            self.temp_files_handler.clean_up_temporary_files()

    def _merge_with_c3d(self,
                        voxel_data_list: List[AbnormalToIntegerVoxelDataAdapter]
                        ) -> NiftiAbnormalVoxelData:
        """
        Merge multiple NIfTI files using c3d STAPLE algorithm.
        
        Parameters
        ----------
        voxel_data_list : List[AbnormalToIntegerVoxelDataAdapter]
            List of temporary NIfTI files to merge
        
        Returns
        -------
        NiftiAbnormalVoxelData
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

        # Get the list of NIfTI file paths
        nifti_path_list = [voxel_data.nifti_path for voxel_data in voxel_data_list]

        # segment high values
        output_staple_high = self.build_output_path(source_voxel_data, suffix="output_staple_high")
        self.run_c3d_command(
            input_paths_list=nifti_path_list,
            output_path=output_staple_high,
            options=["-staple", str(AbnormalValueType.to_integer(AbnormalValueType.HIGH))]
        )
        # segment low values
        output_staple_low = self.build_output_path(source_voxel_data, suffix="output_staple_low")
        self.run_c3d_command(
            input_paths_list=nifti_path_list,
            output_path=output_staple_low,
            options=["-staple", str(AbnormalValueType.to_integer(AbnormalValueType.LOW))]
        )
        # the low segmentations should have labels valued "2", so we have to add them together
        output_staple_2 = self.build_output_path(source_voxel_data, suffix="output_staple_2")
        self.run_c3d_command(
            input_paths_list=[output_staple_low, output_staple_low],
            output_path=output_staple_2,
            options=["-add"]
        )

        # finally, we merge the two segmentations
        output_path = self.build_output_path(source_voxel_data, suffix="segmentation")
        self.run_c3d_command(
            input_paths_list=[output_staple_2, output_staple_high],
            output_path=output_path,
            options=["-add"]
        )

        # Clean up temporary files
        for temporary_path in [output_staple_high, output_staple_low, output_staple_2]:
            temporary_path.unlink()

        # Create a new AbnormalToIntegerVoxelDataAdapter with the output file
        return NiftiAbnormalVoxelData(
            nifti_path=output_path,
            source_voxel_data=source_voxel_data
        )

    @staticmethod
    def build_output_path(source_voxel_data, suffix: str) -> Path:
        # Create file for the output, in the same directory as the source
        source_dti_metric = source_voxel_data.get_filename_without_extension().removesuffix("_map")
        output_path = source_voxel_data.get_parent_directory() / (f"{source_dti_metric}"
                                                                  f"_{suffix}"
                                                                  f".nii.gz")
        return output_path

    @staticmethod
    def run_c3d_command(input_paths_list: List[Path],
                        output_path: Path,
                        options: List[str]) -> None:
        """
        Run the c3d command line tool.

        Parameters
        ----------
        input_paths_list : List[Path]
            List of input file paths to merge
        output_path : Path
            Path to save the output NIfTI file
        options : List[str]
            Options for the c3d command (e.g., "-staple 1")
        """
        # Check if the option is not empty
        if not options:
            raise ValueError("No option provided for c3d command")

        # Check if the input paths list is empty
        if not input_paths_list:
            raise ValueError("No input paths provided for c3d command")

        # Check if the output path already exists
        if output_path.exists():
            raise FileExistsError(f"Output path {output_path} already exists.")

        # Check if the input paths are valid files
        for path in input_paths_list:
            if not path.is_file():
                raise FileNotFoundError(f"Input path {path} does not exist or is not a file")

        # Build the c3d command
        cmd = ["c3d"]
        for nifti_path in input_paths_list:
            cmd.append(str(nifti_path))

        # Add options
        cmd.extend(options)

        # Add output path
        cmd.extend(["-o", str(output_path)])
        try:
            # Execute the command
            logger.info(f"Running c3d command: {' '.join(cmd)}")
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"c3d command completed successfully, output saved to {output_path}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"c3d command failed: {e.stderr}")
