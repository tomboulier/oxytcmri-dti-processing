"""
Concrete implementation of SegmentationMerger using picsl-c3d with STAPLE.
"""
from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import List

import picsl_c3d

from oxytcmri.domain.use_cases.segment_dti_abnormal_values import SegmentationMerger
from oxytcmri.domain.entities.mri import AbnormalValueType, DTIAbnormalValues, AbnormalVoxelData
from oxytcmri.interface.mri.voxel_data_adapters import NiftiAbnormalVoxelData

logger = logging.getLogger(__name__)


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
    Implementation of SegmentationMerger using picsl-c3d STAPLE.

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
        Merge multiple segmentations using picsl-c3d with STAPLE algorithm.

        Process flow:
        1. Convert AbnormalVoxelData (semantic values LOW/HIGH) to temporary NIfTI files (integers 0/1/2)
        2. Process these files with c3d STAPLE algorithm
        3. Convert the result back to AbnormalVoxelData (semantic values LOW/HIGH)

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
            If the picsl-c3d fails
        """
        logger.info(f"Merging {len(segmentations)} segmentations with picsl-c3d STAPLE algorithm")
        if not segmentations:
            raise ValueError("Cannot merge empty list of segmentations")

        try:
            # Extract information from segmentations and create temporary NIfTI files
            temporary_nifti_files = []
            mri_exam_id = segmentations[0].mri_exam_id
            source_dti_map = segmentations[0].source_dti_map

            for segmentation in segmentations:
                if segmentation.mri_exam_id != mri_exam_id:
                    raise ValueError("All segmentations must have the same MRIExamId")

                abnormal_data = segmentation.voxel_data
                if not isinstance(abnormal_data, AbnormalVoxelData):
                    raise TypeError("Segmentation voxel data must be of type AbnormalVoxelData")

                # Create a temporary NIfTI file
                temp_path = self.temp_files_handler.create_temp_nifti_file()

                # Convert directly to NiftiAbnormalVoxelData
                temp_nifti = NiftiAbnormalVoxelData.from_abnormal_voxel_data(
                    abnormal_voxel_data=abnormal_data,
                    nifti_path=temp_path,
                )

                logger.debug(f"Temporary NIfTI file created at {temp_nifti.nifti_path} "
                             f"for segmentation {segmentation.mri_exam_id}")
                temporary_nifti_files.append(temp_nifti)

            # Merge segmentations with picsl-c3d
            nifti_merged_segmentation = self._merge_with_c3d(temporary_nifti_files)

            # Create and return the result
            result = DTIAbnormalValues(
                mri_exam_id=mri_exam_id,
                source_dti_map=source_dti_map,
                voxel_data=nifti_merged_segmentation,
            )

            return result

        finally:
            # Clean up temporary files
            self.temp_files_handler.clean_up_temporary_files()

    def _merge_with_c3d(self,
                        voxel_data_list: List[NiftiAbnormalVoxelData]
                        ) -> NiftiAbnormalVoxelData:
        """
        Merge multiple NIfTI files using picsl-c3d STAPLE algorithm.

        Parameters
        ----------
        voxel_data_list : List[NiftiAbnormalVoxelData]
            List of temporary NIfTI files to merge

        Returns
        -------
        NiftiAbnormalVoxelData
            Merged segmentation

        Raises
        ------
        RuntimeError
            If picsl-c3d execution fails.
        """
        # Check if there are files to merge
        if not voxel_data_list:
            raise ValueError("No files to merge")

        # Get source voxel data from the first file
        source_voxel_data = voxel_data_list[0].get_source_voxel_data()

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

        # TODO: round the values to 0, 1, 2

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
        Run picsl-c3d.

        Parameters
        ----------
        input_paths_list : List[Path]
            List of input file paths to merge
        output_path : Path
            Path to save the output NIfTI file
        options : List[str]
            Options for picsl-c3d (e.g., "-staple 1")
        """
        # Check if the option is not empty
        if not options:
            raise ValueError("No option provided for picsl-c3d")

        # Check if the input paths list is empty
        if not input_paths_list:
            raise ValueError("No input paths provided for picsl-c3d")

        # Check if the output path already exists
        if output_path.exists():
            logger.warning(f"Output path {output_path} already exists. It will be overwritten.")

        # Check if the input paths are valid files
        for path in input_paths_list:
            if not path.is_file():
                raise FileNotFoundError(f"Input path {path} does not exist or is not a file")

        cmd = " ".join(
            [*(f'"{path}"' for path in input_paths_list), *options, "-o", f'"{output_path}"']
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            logger.info(f"Running picsl-c3d: {cmd}")
            picsl_c3d.Convert3D().execute(cmd, out=stdout, err=stderr)
            logger.info(f"picsl-c3d completed successfully, output saved to {output_path}")
        except RuntimeError as e:
            error_details = stderr.getvalue().strip() or stdout.getvalue().strip() or str(e)
            raise RuntimeError(f"picsl-c3d failed: {error_details}") from e
