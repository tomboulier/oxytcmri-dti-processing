# tests.py
import sys
import os
from unittest.mock import patch

import pandas
import pytest
import csv
from typer.testing import CliRunner

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from oxytcmri.controllers import get_subject_folder_path
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume, Base, get_center_id_from_subject_id

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


@pytest.fixture
def database_session():
    """
        Fixture providing a database session for testing.

        Returns:
        - session: A SQLAlchemy session for database interactions.
    """
    engine = create_engine("sqlite:///test.db", echo=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    # Drop the tables after the tests
    Base.metadata.drop_all(engine)

    # delete the test database
    os.remove("test.db")


@pytest.fixture
def test_csv_file(tmpdir):
    # Fixture to create a test CSV file
    csv_content = "subjectId,center,subjectType\n01-subject_1,center_1,Healthy Control\n01_subject_2,center_1,Patient\n02-subject_3,center_2,Patient Test\n"
    csv_file_path = tmpdir.join("test_data.csv")
    csv_file_path.write(csv_content)
    return str(csv_file_path)


@pytest.mark.parametrize("subject_type,center_id,subject_id,expected_path", [
    ("Healthy Control", 5, "05_01V_MR_170615", "/data/Healthy/C05/05_01V_MR_170615"),
    ("Patient", 12, "12_02P_MR_171015", "/data/Patient/C12/12_02P_MR_171015"),
    ("Patient Test", 23, "23-12T-MR-171217", "/data/Patient/C23/23-12T-MR-171217"),
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
        assert "export-md-lesions-to-csv" in result.stdout
        assert "import-data" in result.stdout

    def test_unit_help_import_data(self):
        """Test the import-data command"""
        result = self.runner.invoke(app, ["import-data", "--help"])
        assert result.exit_code == 0
        assert "--settings" in result.stdout
        assert "--database-url" in result.stdout

    def test_integration_import_data(self, database_session):
        """Test if importing data works properly.

        On local repository, real data will be used.
        On remote repository (CI/CD context), fake data will be used.
        """
        if os.getenv('LOCAL_TEST') == 'TRUE':
            # Use real data for local testing
            settings_filepath = "../settings.toml"
            expected_number_of_subjects = 200
            expected_number_of_centers = 19
            expected_number_of_volumes = 4670
        else:
            # Use fake data for online testing
            settings_filepath = "test-data/test_settings.toml"
            expected_number_of_subjects = 23
            expected_number_of_centers = 3
            expected_number_of_volumes = 74

        self._run_command_with_exception_handling("import-data",
                                                  "--settings", settings_filepath,
                                                  "--database-url", database_session.bind.url)

        # Verify the count of Subjects
        all_subjects = database_session.query(Subject).all()
        assert len(all_subjects) == expected_number_of_subjects
        all_centers = database_session.query(Center).all()
        assert len(all_centers) == expected_number_of_centers
        all_exams = database_session.query(MRIExam).all()
        assert len(all_exams) == len(all_subjects)
        all_volumes = database_session.query(MRIVolume).all()
        assert len(all_volumes) == expected_number_of_volumes

    def test_integration_export_data(self, database_session):
        """Test if exporting data works properly.

        On local repository, real data will be used.
        On remote repository (CI/CD context), fake data will be used.
        """
        if os.getenv('LOCAL_TEST') == 'TRUE':
            # Use real data for local testing
            settings_filepath = "../settings.toml"
            csv_filepath = "../output.csv"
            expected_number_of_patients = 85
            expected_mean_of_low_MD_lesions_in_mL_7_94 = 9.46354745197296
        else:
            # Use fake data for online testing
            settings_filepath = "test-data/test_settings.toml"
            csv_filepath = "test-data/output.csv"
            expected_number_of_patients = 11
            expected_mean_of_low_MD_lesions_in_mL_7_94 = 0.8204922921657561

        self._run_command_with_exception_handling("export-md-lesions-to-csv",
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

    def test_unit_help_export_md_lesions_to_csv(self):
        """Test the export-md-lesions-to-csv command"""
        result = self.runner.invoke(app, ["export-md-lesions-to-csv", "--help"])
        assert result.exit_code == 0
        assert "--settings" in result.stdout
        assert "--csv-filepath" in result.stdout
