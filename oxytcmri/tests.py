# tests.py
import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from oxytcmri import settings
from oxytcmri.controllers import get_center_id_from_subject_id
from oxytcmri.models import Subject, Center, MRIExam, MRIVolume, Base
import pytest


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


class TestSettings:
    """Test suite for verifying the behavior of the settings module"""

    def test_read_test_variable(self):
        """Verify that the "test_variable" in the [test] section
        of the  settings file "settings.toml" is read correctly"""
        assert settings.test.test_variable == "test_value"

    def test_read_test_secret(self):
        """Verify that the "test_secret" in the [test] section
        of the secret settings file ".secrets.toml" is read correctly"""
        assert settings.test.test_secret == "test_secret_value"
