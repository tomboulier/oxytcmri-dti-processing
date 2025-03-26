# oxytcmri/tests/integration/test_workflow_import_center.py
import pytest
import tempfile
import os
import csv
import sqlite3

from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.interface.repositories.database_repositories import DataBaseCenterRepository
from oxytcmri.infrastructure.importers import CSVCenterImporter


class TestCenterImportWorkflow:
    @pytest.fixture
    def sample_csv_path(self):
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

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def gateway(self, temp_db_path):
        """Create a SQLModelSQLiteDataGateway instance with a temporary database."""
        return SQLModelSQLiteDataGateway(temp_db_path)

    @pytest.fixture
    def repository(self, gateway):
        """Create a DataBaseCenterRepository instance with the gateway."""
        return DataBaseCenterRepository(data_gateway=gateway)

    @pytest.fixture
    def importer(self, sample_csv_path, repository):
        """Create a CSVCenterImporter instance with the sample CSV and repository."""
        return CSVCenterImporter(sample_csv_path, repository)

    def test_end_to_end_center_import(self, importer, repository, temp_db_path):
        """Test the complete center import workflow from CSV to database."""
        # Import centers from CSV
        importer.import_centers()

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

    def test_reimport_centers(self, importer, repository, temp_db_path):
        """Test that reimporting centers updates existing centers instead of creating duplicates."""
        # Import centers first time
        importer.import_centers()

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
        importer.import_centers()

        # Verify the data was overwritten by the re-import
        cursor.execute("SELECT COUNT(*) FROM centers")
        count = cursor.fetchone()[0]
        assert count == 3  # Still only 3 centers

        cursor.execute("SELECT name FROM centers WHERE id = 1")
        name_after_reimport = cursor.fetchone()[0]
        assert name_after_reimport == "Center A"  # Name restored from CSV

        conn.close()
