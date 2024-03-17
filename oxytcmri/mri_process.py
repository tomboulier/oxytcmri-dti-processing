import contextlib
import os
from pathlib import Path

import docker
from docker.errors import ContainerError
from abc import ABC, abstractmethod, abstractproperty

from oxytcmri.controllers import DatabaseController
from oxytcmri.models import MRIVolume
from oxytcmri.settings import Settings
from oxytcmri.utils import create_tree_structure, get_subject_folder_path


class NeuroImagingTool(ABC):
    """
    Abstract class for neuroimaging tools
    """

    @abstractmethod
    def extract_brain(self, input_filepath: Path, output_filepath: Path):
        pass

    @abstractmethod
    def reorient_to_std(self, input_filepath: Path, output_filepath: Path):
        pass

    @abstractmethod
    def affine_registration_to_reference(self, input_filepath: Path, output_filepath: Path,
                                         output_matrix_filename: str):
        pass

    def segment_left_hemisphere(self, input_filepath: Path, output_filepath: Path):
        pass

    def invert_transform_matrix(self, input_matrix_filepath: Path, output_matrix_filepath: Path):
        pass

    def apply_transform_matrix(self, input_filepath: Path, output_filepath: Path, input_matrix_filepath: Path, reference_filepath: Path):
        pass


class FSLCommandError(Exception):
    """
    Exception raised when an FSL command fails.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FSLDockerInterfaceError(Exception):
    """
    Exception raised when an FSL command fails.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FSLCommand(ABC):
    """
    Abstract class for FSL commands
    """

    def __init__(self, input_directory_path: Path, output_directory_path: Path):
        """
        Parameters
        ----------
        input_directory_path : Path
            Path where the input files are located.
        output_directory_path : Path
            Path where the output files will be saved.
        """
        self.input_directory_path = input_directory_path
        self.output_directory_path = output_directory_path
        if input_directory_path == output_directory_path:
            self.container_base_input_directory = "/home"
            self.container_base_output_directory = "/home"
        else:
            self.container_base_input_directory = "/home/input"
            self.container_base_output_directory = "/home/output"

    def __repr__(self) -> str:
        raise NotImplementedError("The command property must be implemented in the subclass.")

    @property
    def volumes(self):
        """
        Volumes to mount in the container.
        Note that if the input and output directories are the same, the container will mount the same directory.

        Returns
        -------
        dict
            A dictionary with the volumes to mount in the container.
        """
        return {
            str(self.input_directory_path.absolute()):
                {'bind': self.container_base_input_directory, 'mode': 'rw'},
            str(self.output_directory_path.absolute()):
                {'bind': self.container_base_output_directory, 'mode': 'rw'},
        }


class ConvertXFM(FSLCommand):
    def __init__(self, input_matrix_filepath: Path, output_matrix_filepath: Path):
        super().__init__(input_matrix_filepath.parent, output_matrix_filepath.parent)
        self.input_filename = input_matrix_filepath.name
        self.output_filename = output_matrix_filepath.name

    def __repr__(self) -> str:
        return (f"convert_xfm -omat {self.container_base_output_directory}/{self.output_filename} "
                f"-inverse {self.container_base_input_directory}/{self.input_filename}")


class FSLMaths(FSLCommand):
    def __init__(self, input_filepath: Path, output_filepath: Path):
        super().__init__(input_filepath.parent, output_filepath.parent)
        self.input_filename = input_filepath.name
        self.output_filename = output_filepath.name

    def __repr__(self) -> str:
        return (f"fslmaths {self.container_base_input_directory}/{self.input_filename} "
                f"-roi 0 N/2 0 -1 0 -1 0 -1 "
                f"-bin {self.container_base_output_directory}/{self.output_filename}")


class BET(FSLCommand):
    def __init__(self, input_filepath: Path,
                 output_filepath: Path,
                 fractionnal_intensity_threshold: float = 0.5,
                 vertical_gradient: float = 0.0):
        super().__init__(input_filepath.parent, output_filepath.parent)
        self.input_filename = input_filepath.name
        self.output_filename = output_filepath.name
        self.fractionnal_intensity_threshold = fractionnal_intensity_threshold
        self.vertical_gradient = vertical_gradient

    def __repr__(self) -> str:
        return (f"bet {self.container_base_input_directory}/{self.input_filename} "
                f"{self.container_base_output_directory}/{self.output_filename}"
                f" -f {self.fractionnal_intensity_threshold}"
                f" -g {self.vertical_gradient}")


class FLIRT(FSLCommand):
    """
    Class for the FSL tool `flirt`.
    FLIRT stands for FMRIB's Linear Image Registration Tool. It is used to register a 3D volume to a reference image.

    Parameters
    ----------
    input_filepath : Path
        Path to the input file.
    output_filepath : Path
        Path where the output file will be saved.
    output_matrix_filename : Path
        Path where the output transformation matrix file will be saved.
    reference_name : str, optional
        Name of the reference image to which the input image will be aligned.
        Default is "MNI152_T1_2mm_brain".

    Attributes
    ----------
    input_filename : str
        Name of the input file.
    output_filename : str
        Name of the output file.
    output_matrix_filepath : str
        Name of the output transformation matrix file.
    reference_name : str
        Name of the reference image.
    cost_function : str
        Cost function used for the registration. Default is "mutualinfo".
    search_roll_x : tuple
        Range of search for optimization of registration in roll direction (rotation around x-axis).
        Values are in degrees. Default is (-180, 180).
    search_pitch_y : tuple
        Range of search for optimization of registration in pitch direction (rotation around y-axis).
        Values are in degrees. Default is (-180, 180).
    search_yaw_z : tuple
        Range of search for optimization of registration in yaw direction (rotation around z-axis).
        Values are in degrees. Default is (-180, 180).
    degrees_of_freedom : int
        Number of degrees of freedom for the registration, determining the type of transformation that can be applied.
        Default is 12, which corresponds to an affine transformation including translations, rotations, zooms and shears.
    """

    def __init__(self,
                 input_filepath: Path,
                 output_filepath: Path,
                 output_matrix_filename: str,
                 reference_name: str = "MNI152_T1_2mm_brain",
                 cost_function: str = "mutualinfo",
                 search_roll_x: tuple = (-180, 180),
                 search_pitch_y: tuple = (-180, 180),
                 search_yaw_z: tuple = (-180, 180),
                 degrees_of_freedom: int = 12):
        super().__init__(input_filepath.parent, output_filepath.parent)
        self.input_filename = input_filepath.name
        self.output_filename = output_filepath.name
        self.output_matrix_filename = output_matrix_filename
        self.reference_name = reference_name
        self.cost_function = cost_function
        self.search_roll_x = search_roll_x
        self.search_pitch_y = search_pitch_y
        self.search_yaw_z = search_yaw_z
        self.degrees_of_freedom = degrees_of_freedom

    def __repr__(self) -> str:
        return (f"flirt "
                f"-in {self.container_base_input_directory}/{self.input_filename} "
                f"-ref $FSLDIR/data/standard/{self.reference_name}.nii.gz "
                f"-out {self.container_base_output_directory}/{self.output_filename} "
                f"-omat {self.container_base_output_directory}/{self.output_matrix_filename} "
                f"-cost {self.cost_function} "
                f"-searchrx {self.search_roll_x[0]} {self.search_roll_x[1]} "
                f"-searchry {self.search_pitch_y[0]} {self.search_pitch_y[1]} "
                f"-searchrz {self.search_yaw_z[0]} {self.search_yaw_z[1]} "
                f"-dof {self.degrees_of_freedom}")


class ApplyXFM(FSLCommand):
    def __init__(self, input_filepath: Path,
                 output_filepath: Path,
                 input_matrix_filepath: Path,
                 reference_filepath: Path):
        super().__init__(input_filepath.parent, output_filepath.parent)
        self.input_filename = input_filepath.name
        self.output_filename = output_filepath.name
        self.input_matrix_filepath = input_matrix_filepath
        self.input_matrix_filename = input_matrix_filepath.name
        self.reference_filepath = reference_filepath
        self.reference_filename = reference_filepath.name
        self.container_base_matrix_directory = None
        self.container_base_reference_directory = None

    @property
    def volumes(self):
        """
        Volumes to mount in the container.
        Here, since there are 3 different directories, we need to mount them all,
        and bind them to the same directory ("/home/") in the container.
        """
        volumes = super().volumes

        # If the input matrix file is not already mounted, add it to the volumes
        matrix_directorypath_str = str(self.input_matrix_filepath.parent.absolute())
        if matrix_directorypath_str not in volumes:
            self.container_base_matrix_directory = "/home/matrix"
            volumes[matrix_directorypath_str] = {'bind': self.container_base_matrix_directory, 'mode': 'rw'}
        else:
            self.container_base_matrix_directory = volumes[matrix_directorypath_str]['bind']

        # If the reference file is not already mounted, add it to the volumes
        reference_directorypath_str = str(self.reference_filepath.parent.absolute())
        if reference_directorypath_str not in volumes:
            self.container_base_reference_directory = "/home/reference"
            volumes[reference_directorypath_str] = {'bind': self.container_base_reference_directory, 'mode': 'rw'}
        else:
            self.container_base_reference_directory = volumes[reference_directorypath_str]['bind']

        return volumes

    def __repr__(self) -> str:
        return (f"flirt "
                f"-in {self.container_base_input_directory}/{self.input_filename} "
                f"-ref {self.container_base_reference_directory}/{self.reference_filename} "
                f"-out {self.container_base_output_directory}/{self.output_filename} "
                f"-applyxfm -init {self.container_base_matrix_directory}/{self.input_matrix_filename}")


class FSLReorientToStd(FSLCommand):
    """
    Reorient an MRI volume to standard orientation using the FSL tool `fslreorient2std`.
    See https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Orientation%20Explained for more information.

    Parameters
    ----------
    input_filepath : Path
        Path to the input file.
    output_filepath : Path
        Path where the output file will be saved.
    """

    def __init__(self, input_filepath: Path, output_filepath: Path):
        super().__init__(input_filepath.parent, output_filepath.parent)
        self.input_filename = input_filepath.name
        self.output_filename = output_filepath.name

    def __repr__(self) -> str:
        return (f"fslreorient2std "
                f"{self.container_base_input_directory}/{self.input_filename} "
                f"{self.container_base_output_directory}/{self.output_filename}")


class FSLDockerInterface(NeuroImagingTool):

    def __init__(self, image_name='fsl'):
        self.client = docker.from_env()
        self.image_name = image_name

    @contextlib.contextmanager
    def container_context(self, volumes=None):
        user_id = os.getuid()
        group_id = os.getgid()

        try:
            container = self.client.containers.create(self.image_name,
                                                      command=None,
                                                      detach=True,
                                                      volumes=volumes,
                                                      # see https://stackoverflow.com/questions/75128726/dockers-python-sdk-container-start-exit-immediately
                                                      stdin_open=True,
                                                      tty=True,
                                                      user=f"{user_id}:{group_id}",  # to avoid permission issues
                                                      )
            container.start()
        except docker.errors.APIError as error:
            raise FSLDockerInterfaceError(f"Error occurred while creating the container: {error}")
        try:
            yield container
        finally:
            container.kill()
            container.remove()

    @staticmethod
    def check_file_exists_in_container(container, file_path_in_container: str) -> None:
        check_file_command = f"bash -c 'if [ -f {file_path_in_container} ]; then echo exists; else echo not found; fi'"
        check_file_result = container.exec_run(check_file_command)
        if 'exists' not in check_file_result.output.decode('utf-8'):
            raise FSLDockerInterfaceError(f"File {file_path_in_container} not found in container")

    def run_simple_command(self, command: str):
        with self.container_context() as container:
            exec_result = container.exec_run(command)

            if exec_result.exit_code != 0:
                raise FSLDockerInterfaceError(
                    f"Error occurred in container {container}: {exec_result.output.decode('utf-8')}")

            return exec_result.output.decode('utf-8')

    def run_fsl_command(self, fsl_command: FSLCommand):
        with self.container_context(fsl_command.volumes) as container:
            try:
                # run the command
                full_command = f"bash -c '. /usr/local/fsl/etc/fslconf/fsl.sh && {fsl_command}'"
                execution_result = container.exec_run(full_command)

                # If the command failed, raise an exception
                if execution_result.exit_code != 0:
                    raise FSLCommandError(execution_result.output.decode('utf-8'))

            # If the container fails to start, raise an exception
            except ContainerError as error:
                raise FSLDockerInterfaceError(f"Error occurred in container {container}: {error}")

    def extract_brain(self, input_filepath: Path, output_filepath: Path):
        self.run_fsl_command(BET(input_filepath, output_filepath))

    def reorient_to_std(self, input_filepath: Path, output_filepath: Path):
        self.run_fsl_command(FSLReorientToStd(input_filepath, output_filepath))

    def affine_registration_to_reference(self, input_filepath: Path, output_filepath: Path,
                                         output_matrix_filename: str):
        self.run_fsl_command(FLIRT(input_filepath, output_filepath, output_matrix_filename))

    def segment_left_hemisphere(self, input_filepath: Path, output_filepath: Path):
        self.run_fsl_command(FSLMaths(input_filepath, output_filepath))

    def invert_transform_matrix(self, input_matrix_filepath: Path, output_matrix_filepath: Path):
        self.run_fsl_command(ConvertXFM(input_matrix_filepath, output_matrix_filepath))

    def apply_transform_matrix(self, input_filepath: Path, output_filepath: Path, input_matrix_filepath: Path, reference_filepath: Path):
        self.run_fsl_command(ApplyXFM(input_filepath, output_filepath, input_matrix_filepath, reference_filepath))


class MRIProcessor:
    """
    Process MRI data using a specified neuroimaging software.
    """

    def __init__(self,
                 settings: Settings,
                 neuro_imaging_tool: NeuroImagingTool = FSLDockerInterface()
                 ):
        self.neuro_imaging_tool = neuro_imaging_tool
        self.root_directory_path = Path(settings.paths.ProcessedMRIFolder)
        self.db_controller = DatabaseController(settings)
        create_tree_structure(self.root_directory_path, self.db_controller)

    def process_pipeline_on_single_mri_volume(self, mri_volume: MRIVolume):
        """
        Register the MRI volume to "standard" space (MNI152 template), with the following steps:
        1. Reorient the MRI volume to standard orientation using the FSL tool `fslreorient2std`.
        2. Extract the brain using the FSL tool `bet`.
        3. Register the MRI volume to the MNI152 template using the FSL tool `flirt`.

        Left hemisphere segmentation in the MNI152 space
        - The left hemisphere segmentation is performed using the FSL tool `fslmaths`.

        Register back to the original space, using the following steps:
        1. compute the inverse transformation matrix
        2. apply the inverse transformation matrix to the left hemisphere segmentation
        """
        # all the outputs will be saved in the subject's directory
        subject = mri_volume.exam.subject
        subject_folder_path = get_subject_folder_path(data_path=self.root_directory_path, subject=subject)

        # Reorient the MRI volume to standard orientation using the FSL tool `fslreorient2std`
        mri_volume_reoriented_name = f"{mri_volume.name}_reoriented"
        mri_volume_reoriented_filepath = subject_folder_path / f"{mri_volume_reoriented_name}.nii.gz"
        self.neuro_imaging_tool.reorient_to_std(input_filepath=Path(mri_volume.filepath),
                                                output_filepath=mri_volume_reoriented_filepath)
        mri_volume_reoriented = MRIVolume(name=mri_volume_reoriented_name,
                                          filepath=str(mri_volume_reoriented_filepath),
                                          exam_id=mri_volume.exam_id)
        self.db_controller.add_object(mri_volume_reoriented)

        # Extract the brain using the FSL tool `bet`
        mri_volume_brain_name = f"{mri_volume.name}_brain"
        mri_volume_brain_filepath = subject_folder_path / f"{mri_volume_brain_name}.nii.gz"
        self.neuro_imaging_tool.extract_brain(input_filepath=mri_volume_reoriented_filepath,
                                              output_filepath=mri_volume_brain_filepath)
        mri_volume_brain = MRIVolume(name=mri_volume_brain_name,
                                     filepath=str(mri_volume_brain_filepath),
                                     exam_id=mri_volume.exam_id)
        self.db_controller.add_object(mri_volume_brain)

        # Register the MRI volume to the MNI152 template using the FSL tool `flirt`
        mri_volume_registered_name = f"{mri_volume.name}_to_MNI152"
        mri_volume_registered_filepath = subject_folder_path / f"{mri_volume_registered_name}.nii.gz"
        mri_volume_registered_matrix_filepath = subject_folder_path / f"{mri_volume_registered_name}_matrix.mat"
        self.neuro_imaging_tool.affine_registration_to_reference(input_filepath=mri_volume_brain_filepath,
                                                                 output_filepath=mri_volume_registered_filepath,
                                                                 output_matrix_filename=mri_volume_registered_matrix_filepath.name)
        mri_volume_registered = MRIVolume(name=mri_volume_registered_name,
                                          filepath=str(mri_volume_registered_filepath),
                                          exam_id=mri_volume.exam_id)
        self.db_controller.add_object(mri_volume_registered)
        registration_matrix = MRIVolume(name=f"{mri_volume_registered_name}_matrix",
                                        filepath=str(mri_volume_registered_matrix_filepath),
                                        exam_id=mri_volume.exam_id)
        self.db_controller.add_object(registration_matrix)

        # Left hemisphere segmentation in the MNI152 space
        mri_volume_left_hemisphere_name = f"{mri_volume_registered_name}_left_hemisphere_mask"
        mri_volume_left_hemisphere_filepath = subject_folder_path / f"{mri_volume_left_hemisphere_name}.nii.gz"
        self.neuro_imaging_tool.segment_left_hemisphere(input_filepath=mri_volume_registered_filepath,
                                                        output_filepath=mri_volume_left_hemisphere_filepath)
        mri_volume_left_hemisphere = MRIVolume(name=mri_volume_left_hemisphere_name,
                                               filepath=str(mri_volume_left_hemisphere_filepath),
                                               exam_id=mri_volume.exam_id)
        self.db_controller.add_object(mri_volume_left_hemisphere)

        # Compute the inverse transformation matrix
        inverse_matrix_filename = f"MNI152_to_{mri_volume.name}_matrix"
        inverse_matrix_filepath = subject_folder_path / f"{inverse_matrix_filename}.mat"
        self.neuro_imaging_tool.invert_transform_matrix(input_matrix_filepath=mri_volume_registered_matrix_filepath,
                                                        output_matrix_filepath=inverse_matrix_filepath)
        inverse_matrix = MRIVolume(name=inverse_matrix_filename,
                                   filepath=str(inverse_matrix_filepath),
                                   exam_id=mri_volume.exam_id)
        self.db_controller.add_object(inverse_matrix)

        # Apply the inverse transformation matrix to the left hemisphere segmentation
        # command is: flirt -in t1_left_hemisphere_mask.nii.gz -ref t1_image.nii.gz -out t1_left_hemisphere_mask_in_t1_space.nii.gz -init mni_to_t1.mat -applyxfm
        mri_volume_left_hemisphere_in_original_space_name = f"{mri_volume.name}_left_hemisphere_mask"
        mri_volume_left_hemisphere_in_original_space_filepath = subject_folder_path / f"{mri_volume_left_hemisphere_in_original_space_name}.nii.gz"
        self.neuro_imaging_tool.apply_transform_matrix(input_filepath=mri_volume_left_hemisphere_filepath,
                                                       output_filepath=mri_volume_left_hemisphere_in_original_space_filepath,
                                                       input_matrix_filepath=inverse_matrix_filepath,
                                                       reference_filepath=Path(mri_volume.filepath))
        mri_volume_left_hemisphere_in_original_space = MRIVolume(name=mri_volume_left_hemisphere_in_original_space_name,
                                                                 filepath=str(mri_volume_left_hemisphere_in_original_space_filepath),
                                                                 exam_id=mri_volume.exam_id)
        self.db_controller.add_object(mri_volume_left_hemisphere_in_original_space)