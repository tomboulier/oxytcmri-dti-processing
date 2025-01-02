# tests.py
import functools
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch
import pandas
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from typer.testing import CliRunner

from oxytcmri.mri_analysis import MRIAnalysis, get_list_of_brain_localizers_from_json
from oxytcmri.settings import Settings
from oxytcmri.logger import LoggerSingleton, get_logger
from oxytcmri.controllers import DatabaseError, DatabaseController
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume, Base, get_center_id_from_subject_id, MDLesionVolume, \
    Quantiles, LesionType
from oxytcmri.utils import get_subject_folder_path, create_tree_structure
from oxytcmri.usecases.add_clinical_data import AddClinicalData, ClinicalDataRepository, AdditionalClinicalDataRepository

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

# Change the working directory to the directory of the current file
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Fixtures and helper functions
@pytest.fixture
def reset_logger():
    # Reset the singleton instance
    LoggerSingleton._instance = None

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
def test_settings_in_memory(tmp_path_factory) -> Settings:
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


@pytest.fixture()
def settings_with_test_data():
    return Settings("test-data/test_settings.toml")


@pytest.fixture
def db_controller_in_memory(test_settings_in_memory) -> DatabaseController:
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
    # engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


class TestSettings:
    """
    A class containing unit tests for the settings module.
    """

    @pytest.fixture(scope="function")
    def settings(self, tmp_path):
        # Create a temporary settings file
        settings_file = tmp_path / "settings.toml"
        settings_file.write_text('foo = "bar"\n'
                                 '[database]\n'
                                 'url = "sqlite:///test.db"\n'
                                 '[logs]\n'
                                 'LogsDirectoryPath = "logs"\n'
                                 'LogsFilename = "oxytcmri.log"\n')
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
        with pytest.raises(FileNotFoundError,
                           match=f"Settings file not found: '{Path('invalid_settings.toml').absolute()}'"):
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

    def test_list_attributes_of_module(self, settings, tmp_path):
        """
        Test if the list attributes of a module are correctly loaded.
        """
        assert settings.logs.list_attributes() == ['LogsDirectoryPath', 'LogsFilename']

    def test_settings_with_test_data(self, settings_with_test_data):
        """
        Test if the settings are correctly loaded from the test data file.
        """
        assert settings_with_test_data.database.url == "sqlite:///test-data/test.db"
        assert settings_with_test_data.logs.LogsDirectoryPath == "test-data/logs"
        assert settings_with_test_data.logs.LogsFilename == "oxytcmri-test_data.log"

    def test_repr(self, settings):
        """
        Test if the settings are correctly represented as a string.
        """
        assert repr(settings) == f"Settings(filepath='{settings.filepath}')"
        
    def test_str(self, settings):
        """
        Test if the settings are correctly represented as a string.
        """
        expected_str = (
            f"Settings(filepath='{settings.filepath}')\n"
            "------------------------------------------------------------------------\n"
            f"FOO = '{settings.foo}'\n"
            "\n[DATABASE]\n"
            f"url = '{settings.database.url}'\n"
            "\n[LOGS]\n"
            f"LogsDirectoryPath = '{settings.logs.LogsDirectoryPath}'\n"
            f"LogsFilename = '{settings.logs.LogsFilename}'\n"
        )
        assert str(settings) == expected_str

@pytest.mark.usefixtures("reset_logger")
class TestLogging:
    """
    A class containing unit tests for the logging module.
    """

    def test_config_logging(self, test_settings_in_memory, tmp_path):
        """
        Test if the logging is correctly configured.
        """
        # Create temporary log directory
        log_path = tmp_path / "logs"
        log_path.mkdir()

        # Update the settings in memory
        test_settings_in_memory.logs.LogsDirectoryPath = str(log_path)
        test_settings_in_memory.logs.LogsFilename = "oxytcmri.log"
        test_settings_in_memory.logs.LogLevel = "debug"

        # Configure logging
        logger = get_logger(test_settings_in_memory)

        # Check if the logger is correctly configured
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1

        # Check if the log file is correctly created
        log_file = Path(log_path / test_settings_in_memory.logs.LogsFilename)
        assert log_file.exists()

        # Check if SQLAlchemy log level is correctly set
        assert logging.getLogger('sqlalchemy.engine').level == logging.WARNING
        
    def test_config_logging_without_settings(self, tmp_path_factory):
        """
        Test if the logging is correctly configured without settings.
        """
        # Create settings file
        settings_file = tmp_path_factory.mktemp("settings") / "settings.toml"
        settings_file.write_text("")
        settings = Settings(str(settings_file))
        
        # Configure logging
        logger = get_logger(settings)

        # Check if the logger is correctly configured
        assert logger.level == logging.INFO
        
        # Check if SQLAlchemy log level is correctly set
        assert logging.getLogger('sqlalchemy.engine').level == logging.WARNING
        
    def test_permission_error_on_directory_creation(self, tmp_path, test_settings_in_memory):
        """
        Test if a PermissionError is raised when creating a log directory without sufficient permissions.
        """
        # Make the directory containing the log directory read-only
        read_only_dir = tmp_path / "read_only_dir"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o500)
        log_path = read_only_dir / "logs"

        # Update the settings to point to this read-only directory
        test_settings_in_memory.logs.LogsDirectoryPath = str(log_path)

        # Assert that trying to get the logger raises a PermissionError
        with pytest.raises(PermissionError, match=f"Permission denied to create log directory: '{log_path}'"):
            get_logger(test_settings_in_memory)
            
        # make the directory containing the log directory writable
        # to avoid PermissionError for the next test
        read_only_dir.chmod(0o700)
        

    def test_permission_error_on_file_handler_creation(self, tmp_path, test_settings_in_memory):
        """
        Test if a PermissionError is raised when writing to a log file in a directory without sufficient permissions.
        """
        # make the directory containing the log file read-only
        logs_directory_path = Path(test_settings_in_memory.logs.LogsDirectoryPath)
        os.makedirs(logs_directory_path, exist_ok=True)
        logs_directory_path.chmod(0o500)

        # Assert that trying to log a message raises a PermissionError
        with pytest.raises(PermissionError, match=f"Permission denied to create log file: '{test_settings_in_memory.logs.LogsFilename}' in '{logs_directory_path}'."):
            get_logger(test_settings_in_memory)


class TestUtils:
    @pytest.mark.parametrize("subject_type,center_id,subject_id,expected_path", [
        ("Healthy Control", 5, "05_01V_MR_170615", "/data/Healthy/C05/05_01v_mr_170615"),
        ("Patient", 12, "12_02P_MR_171015", "/data/Patient/C12/12_02p_mr_171015"),
        ("Patient Test", 23, "23-12T-MR-171217", "/data/Patient/C23/23-12t-mr-171217"),
    ])
    def test_get_subject_folder_path(self, subject_type, center_id, subject_id, expected_path):
        # Setup
        data_path = "/data"
        subject = Subject(id=subject_id, subject_type=subject_type, center=Center(id=center_id))

        # Mock the Path.exists and Path.iterdir methods to return True and a non-empty list, respectively.
        with patch("pathlib.Path.exists", return_value=True), \
                patch("pathlib.Path.iterdir",
                      return_value=[1]):  # iterdir needs to return an iterable for 'any' to work
            # Act
            result_path = get_subject_folder_path(data_path, subject)

            # Assert
            assert str(result_path) == expected_path

    def test_get_center_id_from_subject_id(self):
        # Test the get_center_id_from_subject_id function
        subject_id = "08-xyz001"
        center_id = get_center_id_from_subject_id(subject_id)
        assert center_id == 8

        # Test the get_center_id_from_subject_id function with an invalid subject id
        with pytest.raises(ValueError,
                           match="Invalid center id in subject id: 'su_001'. The subject id should start with the center id."):
            get_center_id_from_subject_id("su_001")

    def test_create_tree_structure(self, tmp_path, database_session):
        """
        Test if the tree structure is correctly created.
        """
        # Create the tree structure
        root_directory = tmp_path
        create_tree_structure(root_directory, DatabaseController(Settings("test-data/test_settings.toml")))

        # Verify the tree structure
        assert (root_directory / "Healthy" / "C01" / "01_01v_mr_170913").exists()
        assert (root_directory / "Patient" / "C02" / "02_01p_mr_040812").exists()
        assert (root_directory / "Patient" / "C03" / "03_01t_mr_280612").exists()


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
    def test_create_engine_exception(self, test_settings_in_memory):
        """
        Test if an exception is correctly handled when creating the database engine or tables.
        """
        # Mock the create_engine function to raise an exception
        with patch("oxytcmri.controllers.create_engine", side_effect=Exception("Mocked error")):
            with patch.object(test_settings_in_memory.logger, 'error'):
                with pytest.raises(DatabaseError, match="Error while creating the database engine or tables: Mocked error"):
                    DatabaseController(settings=test_settings_in_memory)
                                            
    def test_commit_changes_sqlalchemy_error(self, db_controller_in_memory):
        """
        Test if an SQLAlchemyError is correctly handled when committing changes.
        """
        # Mock the session to raise an SQLAlchemyError
        with patch.object(db_controller_in_memory.database_session, 'commit', side_effect=SQLAlchemyError("Mocked error")):
            with patch.object(db_controller_in_memory.database_session, 'rollback') as mock_rollback:
                with patch.object(db_controller_in_memory.logger, 'error') as mock_logger_error:
                    with pytest.raises(SQLAlchemyError, match="Mocked error"):
                        db_controller_in_memory.commit_changes()
                    mock_rollback.assert_called_once()
                    mock_logger_error.assert_called_once_with("Error while committing changes to database: Mocked error")

    def test_get_subject(self, db_controller_in_memory):
        """
        Test the method `get_subject` of the DatabaseController
        """
        # creating a subject
        subject = Subject(id='subject_id', subject_type='Patient', center_id=1)
        db_controller_in_memory.add_object(subject)

        # check if the subject is correctly retrieved
        assert db_controller_in_memory.get_subject('subject_id') == subject

        # if not found, verify the error message f"Subject not found: {subject_id}"
        with pytest.raises(ValueError, match="Subject not found: subject_id_2"):
            db_controller_in_memory.get_subject('subject_id_2')

    def test_add_md_lesions_volume(self, db_controller_in_memory):
        """
        Test the method `add_object` of the DatabaseController
        """
        # creating a MDLesionVolume object
        md_lesion_volume = MDLesionVolume(
            subject_id=1,
            quantiles=Quantiles.seven_ninetyfour,
            lesion_type=LesionType.low,
            volume_value_in_mL=1,
            localisation='whole_brain'
        )
        db_controller_in_memory.add_mean_diffusivity_lesions_volume(md_lesion_volume, overwrite_data=True)

        # check if the object is added
        assert db_controller_in_memory.get_all_objects(MDLesionVolume) == [md_lesion_volume]

        # creating a second MDLesionVolume object
        md_lesion_volume2 = MDLesionVolume(
            subject_id=1,
            quantiles=Quantiles.seven_ninetyfour,
            lesion_type=LesionType.low,
            volume_value_in_mL=2,
            localisation='whole_brain'
        )
        db_controller_in_memory.add_mean_diffusivity_lesions_volume(md_lesion_volume2, overwrite_data=False)

        # check if the MD lesion volume is not overwritten
        assert db_controller_in_memory.get_all_objects(MDLesionVolume) == [md_lesion_volume]

        db_controller_in_memory.add_mean_diffusivity_lesions_volume(md_lesion_volume2, overwrite_data=True)

        # check if the value has been updated (and not only added)
        md_lesion_volume_list = db_controller_in_memory.get_all_objects(MDLesionVolume)
        assert len(md_lesion_volume_list) == 1
        assert md_lesion_volume_list[0].volume_value_in_mL == 2

    def test_get_distinct_localizations(self, db_controller_in_memory):
        """
        Test the method `get_distinct_localizations` of the DatabaseController
        """
        # creating a list of MDLesionVolume objects
        expected_localizations = ['whole_brain', 'left_hemisphere', 'right_hemisphere', 'thalami', 'corpus_callosum']
        md_lesion_volumes_list = []
        for quantile in Quantiles:
            for lesion_type in LesionType:
                for localization in expected_localizations:
                    md_lesion_volumes_list.append(MDLesionVolume(
                        subject_id=1,
                        quantiles=quantile,
                        lesion_type=lesion_type,
                        volume_value_in_mL=0.5,
                        localisation=localization
                    ))
        db_controller_in_memory.add_objects_list(md_lesion_volumes_list)

        assert db_controller_in_memory.get_distinct_localizations() == expected_localizations

    def test_count_patients(self, db_controller_in_memory, settings_with_test_data):
        """
        Test the method `count_patients` of the DatabaseController
        """

        # adding a patient
        patient = Subject(id='patient_id', subject_type='Patient', center_id=1)
        db_controller_in_memory.add_object(patient)

        # adding a healthy control
        healthy_control = Subject(id='healthy_control_id', subject_type='Healthy Control', center_id=1)
        db_controller_in_memory.add_object(healthy_control)

        assert db_controller_in_memory.count_patients() == 1

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

    def test_get_all_subjects_operational_error(self, db_controller_in_memory):
        """
        Test if an OperationalError is correctly handled when fetching all subjects.
        """
        # Mock the method to raise an OperationalError
        with patch.object(db_controller_in_memory, 'get_all_objects', side_effect=OperationalError("Mocked statement", [], "Mocked error")):
            with pytest.raises(DatabaseError, match="An error occurred while fetching all subjects from the database"):
                db_controller_in_memory.get_all_subjects()

    def test_add_object_exception(self, db_controller_in_memory):
        """
        Test if a generic Exception is correctly handled when adding an object.
        """
        # Mock the session to raise a generic Exception
        with patch.object(db_controller_in_memory.database_session, 'add', side_effect=Exception("Mocked error")):
            with patch.object(db_controller_in_memory.logger, 'error') as mock_logger_error:
                obj = Subject(id='subject_id', subject_type='Patient', center_id=1)
                with pytest.raises(Exception, match="Mocked error"):
                    db_controller_in_memory.add_object(obj)
                mock_logger_error.assert_called_once_with(f"Error while adding object{obj}: Mocked error")


def settings_with_copied_database(tmp_dir: Path, settings_filepath: str) -> str:
    """
    Fixture providing a copy of the database for testing.
    It returns the path to the settings file containing the copied database path.
    """
    # Load settings
    settings = Settings(settings_filepath)

    # get the original database path
    original_db_path = Path(settings.database.url.replace("sqlite:///", ""))

    # create a temporary directory for the database copy
    copied_db_path = tmp_dir / "test.db"

    # copy the database
    shutil.copy2(original_db_path, copied_db_path)

    # Create a new settings file with the copied database path
    settings.database.url = f"sqlite:///{copied_db_path}"
    new_settings_filepath = str(tmp_dir / "settings.toml")
    settings.to_toml(new_settings_filepath)

    return new_settings_filepath


@pytest.fixture
def brain_localizers_list_json_file(tmp_path):
    data = {
        "left_hemisphere": {
            "atlas_number": 4,
            "labels_list_csv_filepath": "test-data/brain-regions-localizers/left_hemisphere_labels_in_Atlas4.csv",
        },
        "right_hemisphere": {
            "atlas_number": 4,
            "labels_list_csv_filepath": "test-data/brain-regions-localizers/right_hemisphere_labels_in_Atlas4.csv",
        }
    }
    json_file_path = tmp_path / "localizers.json"
    with open(json_file_path, 'w') as file:
        json.dump(data, file)
    return json_file_path


def test_unit_get_list_of_brain_localizers_from_json(brain_localizers_list_json_file):
    localizers = get_list_of_brain_localizers_from_json(brain_localizers_list_json_file)
    assert len(localizers) == 2


class TestMRIAnalysis:
    """
    A class containing unit tests for the MRIAnalysis module.
    """
    def test_get_list_of_localizers(self, settings_with_test_data):
        """
        Test if the list of localizers is correctly loaded.
        """
        db_controller = DatabaseController(settings_with_test_data)
        mri_analysis = MRIAnalysis(settings_with_test_data, db_controller)

        # first, get the number of brain localizers from the JSON file
        brain_localizers_list_json_path = settings_with_test_data.brainlocalizers.brain_localizers_list_json_path
        number_of_brain_localizers_in_json = len(get_list_of_brain_localizers_from_json(brain_localizers_list_json_path))

        # then, add the whole brain localizer
        number_of_brain_localizers = number_of_brain_localizers_in_json + 1

        assert len(mri_analysis.brain_region_localizers) == number_of_brain_localizers


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

    def test_unit_help_add_clinical_data(self):
        """Test the add-clinical-data command"""
        result = self.runner.invoke(app, ["add-clinical-data", "--help"])
        assert result.exit_code == 0
        assert "--settings" in result.stdout
        assert "--additional-clinical-data" in result.stdout

    @pytest.mark.parametrize(
        "settings_filepath, expected_number_of_subjects, expected_number_of_centers, expected_number_of_volumes, local_data",
        [
         ("test-data/test_settings.toml", 23, 3, 102, False),  # non-local data
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
        "settings_filepath, local_data",
        [
            ("test-data/test_settings.toml", False),  # non-local data
        ]
    )
    def test_integration_compute_md_lesion(self,
                                           tmp_path_factory,
                                           settings_filepath,
                                           local_data):
        """Test if computing MD lesions works properly.

        The number of MDLesionVolume objects and the mean of all MDLesionVolume values are verified.
        The former is obtained as follows:
            82 (number of subjects) * 20 (number of MDLesionVolumes per subject) = 1640
        The number of MDLesionVolumes per subject comes from:
        - 2 lesion_types (low and high),
        - 2 quantiles (7-94 and 10-95),
        - 5 brain localizations (corpus callosum, thalami, left/right hemisphere, whole brain).

        Parameters
        ----------
        tmp_path_factory: _pytest.tmpdir.TempPathFactory
            The temporary directory factory for creating temporary directories.
        settings_filepath: str
            The path to the settings file.
        expected_number_of_md_lesion_volumes: int
            The expected number of MDLesionVolume objects.
        expected_mean_of_all_values: float
            The expected mean of all MDLesionVolume values.
        local_data: bool
            A flag indicating if the test is run on local data.
        """
        # Create a temporary directory for the copied database
        tmp_dir = tmp_path_factory.mktemp("database")
        test_settings_filepath = settings_with_copied_database(tmp_dir, settings_filepath=settings_filepath)

        # retrieve the DatabaseController instance
        settings = Settings(test_settings_filepath)
        db_controller = DatabaseController(settings)

        # Get number of subjects
        number_of_patients = db_controller.count_patients()
        # Get number of MDLesionVolumes per subject
        n_lesion_types = 2  # low and high
        n_quantiles = 2  # 7-94 and 10-95
        brain_localizers_list_json_path = settings.brainlocalizers.brain_localizers_list_json_path
        number_of_brain_localizers_in_json = len(
            get_list_of_brain_localizers_from_json(brain_localizers_list_json_path))
        number_of_md_lesion_volumes_per_subject = (n_lesion_types
                                                   * n_quantiles
                                                   * (number_of_brain_localizers_in_json+1)  # +1 for the whole brain
                                                   )
        expected_number_of_md_lesion_volumes = number_of_patients * number_of_md_lesion_volumes_per_subject

        # assert len(db_controller.get_all_objects(MDLesionVolume)) == expected_number_of_md_lesion_volumes

        # erase all MDLesionVolume objects
        db_controller.delete_all_objects(MDLesionVolume)
        assert len(db_controller.get_all_objects(MDLesionVolume)) == 0

        # Run the command
        self._run_command_with_exception_handling("compute-md-lesions",
                                                  "--settings", test_settings_filepath)

        # Verify the count of MDLesionVolumes count
        all_md_lesion_volumes = db_controller.get_all_objects(MDLesionVolume)
        assert len(all_md_lesion_volumes) == expected_number_of_md_lesion_volumes

    @skip_if_ci_and_local_data
    @pytest.mark.parametrize(
        "settings_filepath, csv_filepath, expected_number_of_patients, expected_mean_of_low_MD_lesions_in_mL_7_94, local_data",
        [
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
        settings = Settings(settings_filepath)
        self._run_command_with_exception_handling("export-data-to-csv",
                                                  "--settings", settings_filepath,
                                                  "--csv-filepath", csv_filepath,
                                                  )

        # Verify the exported CSV file
        results_data_frame = pandas.read_csv(csv_filepath)
        # ensure the CSV file is not empty
        assert not results_data_frame.empty

        # ensure the CSV file has the expected number of columns
        number_of_clinical_columns = 13
        brain_localizers_list_json_path = settings.brainlocalizers.brain_localizers_list_json_path
        len(get_list_of_brain_localizers_from_json(brain_localizers_list_json_path))
        db_controller = DatabaseController(settings)
        number_of_brain_localizers = len(db_controller.get_distinct_localizations())
        # Calculate the total number of columns
        # * 2 for lesion types (high/low)
        # * 2 for different quantiles (7-94/10-95)
        total_columns = number_of_clinical_columns + (number_of_brain_localizers * 2 * 2)

        # Assertion to check if the number of columns in the DataFrame is correct
        assert len(results_data_frame.columns) == total_columns
        # ensure the CSV file has the same number of rows as the number of patients
        assert len(results_data_frame) == expected_number_of_patients
        # ensure the CSV file has the expected mean volume of low MD lesions in mL (quantiles 7-94)
        assert results_data_frame["low_MD_lesions_in_mL_7_94_whole_brain"].mean() == expected_mean_of_low_MD_lesions_in_mL_7_94

        # delete CSV file after testing
        os.remove(csv_filepath)


class TestAddClinicalData:
    """
    A class containing unit tests for the add-clinical-data command.
    """
    @pytest.fixture
    def mock_clinical_data_repository(self) -> ClinicalDataRepository:
        class MockClinicalDataRepository(ClinicalDataRepository):
            def __init__(self):
                pass

        return MockClinicalDataRepository()

    @pytest.fixture()
    def mock_additional_clinical_data_repository(self) -> AdditionalClinicalDataRepository:
        class MockAdditionalClinicalDataRepository(AdditionalClinicalDataRepository):
            def __init__(self):
                pass

            def extract_data(self) -> dict:
                return {
                    Subject(id="01-01-P"): 2,
                    Subject(id="01-02-P"): 3,
                    Subject(id="03-01-P"): 4,
                }


        return MockAdditionalClinicalDataRepository()

    def test_extract_data(self, mock_additional_clinical_data_repository):
        """
        Test if the data is correctly extracted from the repository.
        """
        data = mock_additional_clinical_data_repository.extract_data()
        expected_data = {
            Subject(id="01-01-P"): 2,
            Subject(id="01-02-P"): 3,
            Subject(id="03-01-P"): 4,
        }

        assert set(data.keys()) == set(expected_data.keys())
        for key in data.keys():
            assert data[key] == expected_data[key]

    def test_creation_of_class_additional_clinical_data(self,
                                                        mock_clinical_data_repository,
                                                        mock_additional_clinical_data_repository):
        """
        Test if the class AdditionalClinicalData is correctly created.
        """
        clinical_data_repo = mock_clinical_data_repository
        additional_clinical_data_repo = mock_additional_clinical_data_repository
        additional_clinical_data = AddClinicalData(clinical_data_repo, additional_clinical_data_repo)

        assert additional_clinical_data is not None