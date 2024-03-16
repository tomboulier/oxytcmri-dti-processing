import contextlib
import os
from pathlib import Path

import docker
from docker.errors import ContainerError
from abc import ABC, abstractmethod, abstractproperty

from oxytcmri.models import MRIVolume


class NeuroImagingTool(ABC):
    """
    Abstract class for neuroimaging tools
    """

    @abstractmethod
    def extract_brain(self, input_path: Path, output_path: Path):
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

    @property
    def command(self) -> str:
        raise NotImplementedError("The command property must be implemented in the subclass.")


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

    @property
    def command(self) -> str:
        return (f"bet /home/input/{self.input_filename} "
                f"/home/output/{self.output_filename}"
                f" -f {self.fractionnal_intensity_threshold}"
                f" -g {self.vertical_gradient}")


class FSLDockerInterface(NeuroImagingTool):
    def __init__(self, image_name='fsl'):
        self.client = docker.from_env()
        self.image_name = image_name

    @contextlib.contextmanager
    def container_context(self, volumes=None):

        container = self.client.containers.create(self.image_name,
                                                  command=None,
                                                  detach=True,
                                                  volumes=volumes,
                                                  # see https://stackoverflow.com/questions/75128726/dockers-python-sdk-container-start-exit-immediately
                                                  stdin_open=True,
                                                  tty=True)
        container.start()
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

        volumes = {
            str(fsl_command.input_directory_path.absolute()):
                {'bind': f'/home/input', 'mode': 'rw'},
            str(fsl_command.output_directory_path.absolute()):
                {'bind': f'/home/output', 'mode': 'rw'},
        }
        with self.container_context(volumes) as container:
            try:
                # run the command
                full_command = f"bash -c '. /usr/local/fsl/etc/fslconf/fsl.sh && {fsl_command.command}'"
                execution_result = container.exec_run(full_command)

                # If the command failed, raise an exception
                if execution_result.exit_code != 0:
                    raise FSLCommandError(execution_result.output.decode('utf-8'))

            # If the container fails to start, raise an exception
            except ContainerError as error:
                raise FSLDockerInterfaceError(f"Error occurred in container {container}: {error}")

    def extract_brain(self, input_filepath: Path, output_filepath: Path):
        self.run_fsl_command(BET(input_filepath, output_filepath))


class MRIProcessor:
    """
    Process MRI data using a specified neuroimaging software.
    """

    def __init__(self, neuro_imaging_tool: NeuroImagingTool = FSLDockerInterface()):
        self.neuro_imaging_tool = neuro_imaging_tool

    def extract_brain(self, mri_volume: MRIVolume, output_filepath: Path):
        """
        Extract the brain from the MRI volume.

        Parameters
        ----------
        mri_volume : MRIVolume
            The MRI volume to process.

        output_filepath : Path
            The path to save the output.

        Returns
        -------
        None
        """
        self.neuro_imaging_tool.extract_brain(Path(mri_volume.filepath), output_filepath)
