import contextlib
import os
from pathlib import Path

import docker
from docker.errors import ContainerError
from abc import ABC, abstractmethod

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
                raise FSLDockerInterfaceError(f"Error occurred in container {container}: {exec_result.output.decode('utf-8')}")

            return exec_result.output.decode('utf-8')

    def run_fsl_command(self,
                        command: str,
                        input_host_directorypath: Path,
                        output_host_directorypath: Path,
                        container_path='/home'):

        volumes = {
            str(input_host_directorypath.absolute()):
                {'bind': f'{container_path}/input', 'mode': 'rw'},
            str(output_host_directorypath.absolute()):
                {'bind': f'{container_path}/output', 'mode': 'rw'},
        }
        with self.container_context(volumes) as container:
            try:
                # run the command
                full_command = f"bash -c '. /usr/local/fsl/etc/fslconf/fsl.sh && {command}'"
                execution_result = container.exec_run(full_command)

                # If the command failed, raise an exception
                if execution_result.exit_code != 0:
                    logs = container.logs().decode('utf-8')  # decode the logs to string
                    raise FSLCommandError(logs)

            # If the container fails to start, raise an exception
            except ContainerError as error:
                raise FSLDockerInterfaceError(f"Error occurred in container {container}: {error}")

    def extract_brain(self, input_filepath: Path, output_filepath: Path):
        input_host_directorypath = input_filepath.parent
        output_host_directorypath = output_filepath.parent

        input_filename = input_filepath.name
        output_filename = output_filepath.name

        command = f"bet /home/input/{input_filename} /home/output/{output_filename}"

        self.run_fsl_command(command, input_host_directorypath, output_host_directorypath)


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
