# oxytcmri/tests/integration/test_workflow_import_center.py
import pytest
import tempfile
import os
import csv
import sqlite3

from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.interface.repositories.database_repositories import DataBaseCenterRepository, DataBaseAtlasRepository, \
    DataBaseMRIExamRepository, DataBaseSubjectRepository
from oxytcmri.interface.importers import CSVAtlasImporter, NiftiFoldersImporter
from oxytcmri.infrastructure.importers.csv import CSVCenterImporter
from oxytcmri.tests.fixtures import path_to_test_data_folder


@pytest.fixture(scope="module")
def temp_db_path():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    yield path

    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="module")
def centers_list_csv_path():
    """Create a temporary CSV file with sample center data."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
        writer = csv.writer(temp_file)
        writer.writerow(['id', 'name'])  # Header
        writer.writerow(['1', 'Center A'])
        writer.writerow(['2', 'Center B'])
        writer.writerow(['3', 'Center C'])
        csv_path = temp_file.name

    yield csv_path

    # Cleanup
    if os.path.exists(csv_path):
        os.unlink(csv_path)


@pytest.fixture(scope="module")
def atlas_list_csv_file():
    """Create a temporary CSV file with sample atlas data."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
        writer = csv.writer(temp_file)
        writer.writerow(['2', 'Neuromorphometrics atlas + GM parcels size ≤5cm3', '29', '33', '62'])
        writer.writerow(['4', 'Neuromorphometrics atlas + GM parcels size >5cm3', '29', '33', '59', '60', '62'])
        csv_file = temp_file.name

    yield csv_file

    # Cleanup
    if os.path.exists(csv_file):
        os.unlink(csv_file)


@pytest.fixture(scope="module")
def gateway(temp_db_path):
    """Create a SQLModelSQLiteDataGateway instance with a temporary database."""
    return SQLModelSQLiteDataGateway(temp_db_path)


@pytest.fixture(scope="module")
def centers_repository(gateway):
    """Create a DataBaseCenterRepository instance with the gateway."""
    return DataBaseCenterRepository(data_gateway=gateway)


@pytest.fixture
def centers_importer(centers_list_csv_path, centers_repository):
    """Create a CSVCenterImporter instance with the sample CSV and repository."""
    return CSVCenterImporter(centers_list_csv_path, centers_repository)


@pytest.fixture
def atlas_repository(gateway):
    return DataBaseAtlasRepository(data_gateway=gateway)


@pytest.fixture
def atlas_importer(atlas_list_csv_file, atlas_repository):
    return CSVAtlasImporter(atlas_list_csv_file, atlas_repository)


class TestCenterImportWorkflow:
    def test_end_to_end_center_import(self, centers_importer, centers_repository, temp_db_path):
        """Test the complete center import workflow from CSV to database."""
        # Import centers from CSV
        centers_importer.import_data()

        # Verify correct number of centers imported by
        # making a SQL request to the SQLite database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check number of centers
        cursor.execute("SELECT COUNT(*) FROM centers")
        count = cursor.fetchone()[0]
        assert count == 3

        # Check specific centers
        cursor.execute("SELECT id, name FROM centers ORDER BY id")
        centers = cursor.fetchall()

        assert centers[0][0] == 1
        assert centers[0][1] == "Center A"

        assert centers[1][0] == 2
        assert centers[1][1] == "Center B"

        assert centers[2][0] == 3
        assert centers[2][1] == "Center C"

        conn.close()

    def test_reimport_centers(self, centers_importer, centers_repository, temp_db_path):
        """Test that reimporting centers updates existing centers instead of creating duplicates."""
        # Import centers first time
        centers_importer.import_data()

        # Modify the data directly in the database to simulate changes
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE centers SET name = 'Modified Center A' WHERE id = 1")
        conn.commit()

        # Verify the modification
        cursor.execute("SELECT name FROM centers WHERE id = 1")
        modified_name = cursor.fetchone()[0]
        assert modified_name == "Modified Center A"

        # Import again
        centers_importer.import_data()

        # Verify the data was overwritten by the re-import
        cursor.execute("SELECT COUNT(*) FROM centers")
        count = cursor.fetchone()[0]
        assert count == 3  # Still only 3 centers

        cursor.execute("SELECT name FROM centers WHERE id = 1")
        name_after_reimport = cursor.fetchone()[0]
        assert name_after_reimport == "Center A"  # Name restored from CSV

        conn.close()


class TestAtlasImportWorkflow:
    def test_end_to_end_atlas_import(self, atlas_importer, temp_db_path):
        atlas_importer.import_data()

        # Verify correct number of atlases imported by
        # making a SQL request to the SQLite database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check number of atlases
        cursor.execute("SELECT COUNT(*) FROM atlases")
        count = cursor.fetchone()[0]
        assert count == 2


class TestNiftiImportWorkflow:
    @pytest.fixture
    def test_data_path(self):
        return str(path_to_test_data_folder() / "NiftiFoldersMRIExamRepository")

    def test_end_to_end_nifti_import(self,
                                     centers_importer,
                                     atlas_importer,
                                     test_data_path,
                                     gateway,
                                     atlas_repository,
                                     temp_db_path):
        # First, import centers and atlases
        centers_importer.import_data()
        atlas_importer.import_data()

        # Next, create MRI and subject repositories for persistent storage
        mri_repository = DataBaseMRIExamRepository(data_gateway=gateway)
        subject_repository = DataBaseSubjectRepository(data_gateway=gateway)

        # Now, import the NIfTI data
        importer = NiftiFoldersImporter(base_path=test_data_path,
                                        mri_exam_repository=mri_repository,
                                        atlas_repository=atlas_repository,
                                        subject_repository=subject_repository,
                                        )
        importer.import_data()

        # Verify correct number of MRI exams imported by
        # making a SQL request to the SQLite database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check number of MRI exams
        cursor.execute("SELECT COUNT(*) FROM mri_exams")
        mri_exam_count_from_database = cursor.fetchone()[0]
        # this number should be equal to the number of folders in the test data path
        mri_exam_count_from_folder = len(os.listdir(test_data_path))
        assert mri_exam_count_from_database == mri_exam_count_from_folder

        # Check number of subjects
        cursor.execute("SELECT COUNT(*) FROM subjects")
        subject_count_from_database = cursor.fetchone()[0]
        assert subject_count_from_database == mri_exam_count_from_folder

        # Check number of MRI data
        cursor.execute("SELECT COUNT(*) FROM mri_data")
        mri_data_count_from_database = cursor.fetchone()[0]
        # this number should be equal to the number of ".nii.gz" files
        # in the subfolders of the test data path
        mri_data_count_from_folder = 0
        for folder in os.listdir(test_data_path):
            for file in os.listdir(os.path.join(test_data_path, folder)):
                if file.endswith(".nii.gz"):
                    mri_data_count_from_folder += 1
        assert mri_data_count_from_database == mri_data_count_from_folder
