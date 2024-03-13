# tests.py
import functools
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pandas
import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from oxytcmri.settings import Settings
from oxytcmri.logger import get_logger
from oxytcmri.controllers import DatabaseController
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume, Base, get_center_id_from_subject_id
from oxytcmri.utils import get_subject_folder_path

# The following lines are meant to import the CLI script from the parent directory.
# See https://www.geeksforgeeks.org/python-import-from-parent-directory/ for more details.
# 1. Getting the name of the directory where the CLI script is present.
current = os.path.dirname(os.path.realpath(__file__))
# 2. Getting the parent directory name where the current directory is present.
parent = os.path.dirname(current)
# 3. Adding the parent directory to the sys.path.
sys.path.append(parent)
# 4. now we can import the module in the parent directory.
from oxytcmricli import app  # noqa: E402


def skip_if_ci_and_local_data(test_func):
    """
    Decorator to skip a test if it is run in a CI environment and local data is used.
    """

    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        local_data = kwargs.get('local_data', False)
        if local_data and os.getenv('CI', 'false') == 'true':
            pytest.skip("Skipping this test in CI environment with local data")
        else:
            return test_func(*args, **kwargs)

    return wrapper


@pytest.fixture(scope="session")
def test_settings_in_memory(tmp_path_factory):
    """
    Fixture to generate test settings.
    """
    # Creates settings file
    tmp_dir = tmp_path_factory.mktemp("settings")
    settings_file = tmp_dir / "test_settings.toml"
    logs_dir = tmp_dir / "logs"
    settings_content = \
        f"""[database]
        url = "sqlite:///:memory:"
        [logs]
        LogsDirectoryPath = "{logs_dir}"
        LogsFilename = "oxytcmri.log"
        """
    settings_file.write_text(settings_content)

    # Loading settings file
    settings = Settings(str(settings_file))
    return settings


@pytest.fixture
def db_controller_in_memory(test_settings_in_memory):
    """
    Fixture to create a DatabaseController instance with test settings.
    """
    return DatabaseController(settings=test_settings_in_memory)


@pytest.fixture
def database_session(tmp_path_factory):
    """
        Fixture providing a database session for testing.

        Returns:
        - session: A SQLAlchemy session for database interactions.
    """
    tmp_dir = tmp_path_factory.mktemp("database")
    tmp_database = tmp_dir / "test.db"
    engine = create_engine(f"sqlite:///{tmp_database}", echo=False)
    #engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def test_csv_file(tmpdir):
    # Fixture to create a test CSV file
    csv_content = "subjectId,center,subjectType\n01-subject_1,center_1,Healthy Control\n01_subject_2,center_1,Patient\n02-subject_3,center_2,Patient Test\n"
    csv_file_path = tmpdir.join("test_data.csv")
    csv_file_path.write(csv_content)
    return str(csv_file_path)


class TestSettings:
    """
    A class containing unit tests for the settings module.
    """
    @pytest.fixture(scope="function")
    def settings(self, tmp_path):
        # Create a temporary settings file
        settings_file = tmp_path / "settings.toml"
        settings_file.write_text(f'foo = "bar"\n'
                                      f'[database]\n'
                                      f'url = "sqlite:///test.db"\n'
                                      f'[logs]\n'
                                      f'LogsDirectoryPath = "logs"\n'
                                      f'LogsFilename = "oxytcmri.log"\n')
        return Settings(str(settings_file))

    def test_load_settings(self, settings, tmp_path):
        """
        Test if the settings are correctly loaded from a file.
        """
        assert settings.filepath == tmp_path / "settings.toml"

    def test_settings_attributes(self, settings):
        """
        Test if the settings attributes are correctly loaded.
        """
        assert settings.foo == "bar"
        assert settings.database.url == "sqlite:///test.db"
        assert settings.logs.LogsDirectoryPath == "logs"
        assert settings.logs.LogsFilename == "oxytcmri.log"

    def test_settings_errors(self, settings):
        """
        Test if the settings module raises the correct errors.
        """
        with pytest.raises(FileNotFoundError, match=f"Settings file not found: '{Path('invalid_settings.toml').absolute()}'"):
            Settings("invalid_settings.toml")
        with pytest.raises(AttributeError, match="No module 'invalid_module' in settings file"):
            settings.invalid_module
        with pytest.raises(AttributeError, match="No attribute 'invalid_attribute' for module 'logs'"):
            settings.logs.invalid_attribute

    def test_to_toml(self, settings, tmp_path):
        """
        Test if the settings are correctly written to a TOML file.
        """
        toml_file = tmp_path / "test_settings.toml"
        settings.to_toml(toml_file)

        settings_exported = Settings(str(toml_file))

        assert settings_exported.foo == settings.foo
        assert settings_exported.database.url == settings.database.url
        assert settings_exported.logs.LogsDirectoryPath == settings.logs.LogsDirectoryPath
        assert settings_exported.logs.LogsFilename == settings.logs.LogsFilename



class TestLogging:
    """
    A class containing unit tests for the logging module.
    """

    def test_config_logging(self, tmp_path):
        """
        Test if the logging is correctly configured.
        """
        # Create a temporary settings file
        settings_file = tmp_path / "settings.toml"

        # Create temporary log directory
        log_path = tmp_path / "logs"
        settings_file.write_text(f'[logs]\n'
                                 f'LogsDirectoryPath = "{log_path}"\n'
                                 f'LogsFilename = "oxytcmri.log"\n'
                                 f'LogLevel = "debug"\n')

        # Load settings
        settings = Settings(str(settings_file))

        # Configure logging
        logger = get_logger(settings)

        # Check if the logger is correctly configured
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1

        # Check if the log file is correctly created
        log_file = Path(log_path / settings.logs.LogsFilename)
        assert log_file.exists()

        # Check if SQLAlchemy log level is correctly set
        assert logging.getLogger('sqlalchemy.engine').level == logging.WARNING


@pytest.mark.parametrize("subject_type,center_id,subject_id,expected_path", [
    ("Healthy Control", 5, "05_01V_MR_170615", "/data/Healthy/C05/05_01v_mr_170615"),
    ("Patient", 12, "12_02P_MR_171015", "/data/Patient/C12/12_02p_mr_171015"),
    ("Patient Test", 23, "23-12T-MR-171217", "/data/Patient/C23/23-12t-mr-171217"),
])
def test_get_subject_folder_path(subject_type, center_id, subject_id, expected_path):
    # Setup
    data_path = "/data"
    subject = Subject(id=subject_id, subject_type=subject_type, center=Center(id=center_id))

    # Mock the Path.exists and Path.iterdir methods to return True and a non-empty list, respectively.
    with patch("pathlib.Path.exists", return_value=True), \
            patch("pathlib.Path.iterdir", return_value=[1]):  # iterdir needs to return an iterable for 'any' to work
        # Act
        result_path = get_subject_folder_path(data_path, subject)

        # Assert
        assert str(result_path) == expected_path


def test_get_center_id_from_subject_id():
    # Test the get_center_id_from_subject_id function
    subject_id = "08-xyz001"
    center_id = get_center_id_from_subject_id(subject_id)
    assert center_id == 8

    # Test the get_center_id_from_subject_id function with an invalid subject id
    with pytest.raises(ValueError,
                       match="Invalid center id in subject id: 'su_001'. The subject id should start with the center id."):
        get_center_id_from_subject_id("su_001")


class TestModels:
    """
        A class containing unit tests for the Oxy-TC MRI models.

        Attributes:
        - database_session: A fixture providing a database session for testing.

        Methods:
        - test_create_subject: Test the creation of a Subject model.
        - test_create_center: Test the creation of a Center model.
        - test_create_mri_exam: Test the creation of an MRIExam model.
        - test_create_mri_volume: Test the creation of an MRIVolume model.

        Note: Ensure to use the provided database session for testing (i.e. the fixture).
        """

    def test_create_subject(self, database_session):
        # Test creating a Subject
        grenoble = Center(id=1, name="Grenoble")
        subject1 = Subject(id="subject_id_1", subject_type="Healthy Control", center=grenoble)
        database_session.add_all([grenoble, subject1])
        database_session.commit()

        db_subject = database_session.execute(select(Subject)).scalar_one()
        assert db_subject is not None
        assert db_subject.id == "subject_id_1"
        assert db_subject.subject_type == "Healthy Control"
        assert db_subject.center.id == 1

    def test_create_center(self, database_session):
        # Test creating a Center
        center = Center(id=1, name="Grenoble")
        database_session.add(center)
        database_session.commit()

        db_center = database_session.execute(select(Center)).scalar_one()
        assert db_center is not None
        assert db_center.id == 1
        assert db_center.name == "Grenoble"

    def test_create_mri_exam(self, database_session):
        # Test creating an MRIExam
        subject = Subject(id="subject_id_2", subject_type="patient", center_id=2)
        database_session.add(subject)

        mri_exam = MRIExam(subject=subject)
        database_session.add(mri_exam)
        database_session.commit()

        db_mri_exam = database_session.execute(select(MRIExam)).scalar_one()
        db_subject = database_session.execute(select(Subject)).scalar_one()
        assert db_mri_exam is not None
        assert db_mri_exam.id == 1
        assert db_mri_exam.subject.id == "subject_id_2"
        assert db_subject.mri_exam == db_mri_exam

    def test_create_mri_volume(self, database_session):
        # Test creating an MRIVolume
        paris = Center(id=3, name="Paris")
        subject3 = Subject(id="subject_id_3", subject_type="test_patient", center=paris)
        database_session.add(subject3)

        mri_exam = MRIExam(subject=subject3)
        database_session.add(mri_exam)

        mri_volume = MRIVolume(name="T1", filepath="/path/to/t1.nii.gz", exam=mri_exam)
        database_session.add(mri_volume)

        database_session.commit()

        db_mri_volume = database_session.execute(select(MRIVolume)).scalar_one()
        db_mri_exam = database_session.execute(select(MRIExam)).scalar_one()
        assert db_mri_volume is not None
        assert db_mri_volume.name == "T1"
        assert db_mri_volume.filepath == "/path/to/t1.nii.gz"
        assert db_mri_volume.exam.subject.center == paris
        assert db_mri_exam.volumes == [db_mri_volume]


class TestDatabaseController:
    """Tests suit for DatabaseController"""

    def test_object_add_and_exists(self, db_controller_in_memory):
        """
        Test if `object_exists` correctly identifies an existing object in the database.
        This allows us to test in the same time the method `add_object`
        """
        # adding a subject
        existing_subject = Subject(id='existing_subject', subject_type='Patient', center_id=1)
        db_controller_in_memory.add_object(existing_subject)

        # checks if this subject exists
        assert db_controller_in_memory.object_exists(Subject, id='existing_subject')

        # this center is not supposed to exist
        assert not db_controller_in_memory.object_exists(Center, name="Pétaouchnok")

    def test_add_list_of_objects(self, db_controller_in_memory):
        """
        Adds a list of objects, and test if they exist
        """
        test_center = Center(name="Test")
        subject1 = Subject(id="subject_id_1", subject_type="Healthy Control", center=test_center)
        subject2 = Subject(id="subject_id_2", subject_type="Healthy Control", center=test_center)
        subject3 = Subject(id="subject_id_3", subject_type="Healthy Control", center=test_center)

        db_controller_in_memory.add_objects_list([subject1, subject2, subject3])

        for id_number in [1, 2, 3]:
            assert db_controller_in_memory.object_exists(Subject, id=f'subject_id_{id_number}')

    def test_get_mri_exam_and_volumes(self, db_controller_in_memory):
        """
        Test if `get_mri_exam` and `get_mri_volume` give the correct answer
        """
        babeloued_center = Center(name="Bab El Oued")
        subject = Subject(id=74865, subject_type="test_patient", center=babeloued_center)
        mri_exam = MRIExam(subject=subject)
        mri_volume = MRIVolume(name="T1", filepath="/path/to/t1.nii.gz", exam=mri_exam)
        for obj in [subject, mri_exam, mri_volume]:
            db_controller_in_memory.add_object(obj)

        assert db_controller_in_memory.get_mri_exam(subject=subject).subject.id == subject.id
        assert db_controller_in_memory.get_mri_volume(subject_id=subject.id, volume_name="T1").name == "T1"


class TestCLI:
    """unit tests suit for verifying the behavior of the CLI script"""

    runner = CliRunner()

    def _run_command_with_exception_handling(self, command, *args, **kwargs):
        """
        Executes a TyperCLI command with exception handling.

        Parameters
        ----------
        command: str
            The command to execute and its arguments as a list.
        *args:
            Additional positional arguments for the TyperCLI command.
        **kwargs:
            Additional named arguments for the TyperCLI command, used to specify command options.

        Returns
        -------
        Result
            The result of executing the TyperCLI command.

        Raises
        ------
        Exception
            If the command execution results in an exception.
        """
        # Constructing the complete command with args and kwargs
        # This combines the command list with any additional positional arguments
        # and constructs command options from kwargs.
        command_args = [command] + list(args) + [f"--{k} {v}" for k, v in kwargs.items()]

        # Invoking the command
        result = self.runner.invoke(app, command_args)

        # Handling exceptions
        if result.exception:
            print(f"Exception during command execution: {result.exception}")
            raise result.exception

        return result

    def test_unit_help(self):
        """Test the help command"""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "export-data-to-csv" in result.stdout
        assert "import-data" in result.stdout

    def test_unit_help_import_data(self):
        """Test the import-data command"""
        result = self.runner.invoke(app, ["import-data", "--help"])
        assert result.exit_code == 0
        assert "--settings" in result.stdout
        assert "--database-url" in result.stdout

    def test_unit_help_export_md_lesions_to_csv(self):
        """Test the export-md-lesions-to-csv command"""
        result = self.runner.invoke(app, ["export-data-to-csv", "--help"])
        assert result.exit_code == 0
        assert "--settings" in result.stdout
        assert "--csv-filepath" in result.stdout

    @pytest.mark.parametrize(
        "settings_filepath, expected_number_of_subjects, expected_number_of_centers, expected_number_of_volumes, local_data",
        [("../settings.toml", 200, 19, 4670, True),  # local data
         ("test-data/test_settings.toml", 23, 3, 74, False),  # non-local data
         ])
    @skip_if_ci_and_local_data
    def test_integration_import_data(self,
                                     database_session,
                                     settings_filepath,
                                     expected_number_of_subjects,
                                     expected_number_of_centers,
                                     expected_number_of_volumes,
                                     local_data):
        """Test if importing data works properly.

        On local repository, real data will be used.
        On remote repository (CI/CD context), fake data will be used.
        """
        self._run_command_with_exception_handling("import-data",
                                                  "--settings", settings_filepath,
                                                  "--database-url", database_session.bind.url)

        # retrieve DatabaseController instance
        settings = Settings(settings_filepath)
        settings.database.url = str(database_session.bind.url)
        db_controller = DatabaseController(settings)

        # Verify the count of Subjects
        all_subjects = db_controller.get_all_subjects()
        assert len(all_subjects) == expected_number_of_subjects
        # Verify the count of Centers
        all_centers = db_controller.get_all_objects(Center)
        assert len(all_centers) == expected_number_of_centers
        # Verify that the count of MRIExams is the same as number of Subjects
        all_exams = db_controller.get_all_objects(MRIExam)
        assert len(all_exams) == len(all_subjects)
        # Verify the count of MRIVolumes
        all_volumes = db_controller.get_all_objects(MRIVolume)
        assert len(all_volumes) == expected_number_of_volumes

    @skip_if_ci_and_local_data
    @pytest.mark.parametrize(
        "settings_filepath, csv_filepath, expected_number_of_patients, expected_mean_of_low_MD_lesions_in_mL_7_94, local_data",
        [("../settings.toml", "../output.csv", 85, 9.46354745197296, True),  # local data
         ("test-data/test_settings.toml", "test-data/output.csv", 11, 0.8204922921657561, False),  # non-local data
         ])
    def test_integration_export_data(self,
                                     database_session,
                                     settings_filepath,
                                     csv_filepath,
                                     expected_number_of_patients,
                                     expected_mean_of_low_MD_lesions_in_mL_7_94,
                                     local_data):
        """Test if exporting data works properly.

        On local repository, real data will be used.
        On remote repository (CI/CD context), fake data will be used.
        """
        self._run_command_with_exception_handling("export-data-to-csv",
                                                  "--settings", settings_filepath,
                                                  "--csv-filepath", csv_filepath,
                                                  )

        # Verify the exported CSV file
        results_data_frame = pandas.read_csv(csv_filepath)
        # ensure the CSV file is not empty
        assert not results_data_frame.empty
        # ensure the CSV file has the expected number of columns
        assert len(results_data_frame.columns) == 16
        # ensure the CSV file has the same number of rows as the number of patients
        assert len(results_data_frame) == expected_number_of_patients
        # ensure the CSV file has the expected mean volume of low MD lesions in mL (quantiles 7-94)
        assert results_data_frame["low_MD_lesions_in_mL_7_94"].mean() == expected_mean_of_low_MD_lesions_in_mL_7_94

        # delete CSV file after testing
        os.remove(csv_filepath)
