import csv
from abc import ABC
from pathlib import Path

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas
from oxytcmri.domain.ports.repositories import CenterRepository, Repository, AtlasRepository
from oxytcmri.interface.importers import Importer


class CSVImporter(Importer, ABC):
    """
    Abstract base class for CSV importers.

    Attributes:
    -----------
        csv_file_path: str
            The path to the CSV file.
        repository: Repository
            The repository to save the data.
    """

    def __init__(self, filepath: str):
        self.csv_file_path = Path(filepath)
        # Ensure that the CSV file exists
        if not self.csv_file_path.exists():
            raise FileNotFoundError(f"CSV file not found: '{self.csv_file_path}'.")


class CSVCenterImporter(CSVImporter):
    """
    Import centers from a CSV file to the repository.

    Attributes:
    -----------
        csv_file_path: str
            The path to the CSV file.
        center_repository: CenterRepository
            The repository to save the centers.
    """

    def __init__(self, filepath: str, center_repository: CenterRepository = None):
        super().__init__(filepath)
        self.center_repository = center_repository

    def register_repository(self, repositories: list[Repository]):
        for repository in repositories:
            if isinstance(repository, CenterRepository):
                self.center_repository = repository

    def import_data(self) -> None:
        """
        Import centers from the CSV file to the repository.

        Returns:
        --------
        None
        """
        if self.center_repository is None:
            raise ValueError("Center repository is not set.")

        with open(self.csv_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            centers = [Center(id=int(row['id']), name=row['name']) for row in reader]

        self.center_repository.save_centers(centers)


class CSVAtlasImporter(CSVImporter):
    """Service for importing atlas data from a CSV file.

    The CSV file should have the following format:
    id,name_atlas,label1,label2,label3,...

    Attributes:
    -----------
    csv_file_path: str
        Path to the CSV file containing atlas data.
    atlas_repository: AtlasRepository
        Repository for storing atlas entities.
    """

    def __init__(self,
                 csv_file_path: str,
                 atlas_repository: AtlasRepository = None):
        """
        Initialize the importer.

        Parameters:
        -----------
            csv_file_path: str
                Path to the CSV file containing atlas data.
            atlas_repository: AtlasRepository
                Repository for storing atlas entities.
        """
        super().__init__(csv_file_path)
        self.atlas_repository = atlas_repository

    def register_repository(self, repositories: list[Repository]):
        for repository in repositories:
            if isinstance(repository, AtlasRepository):
                self.atlas_repository = repository

    def import_data(self) -> None:
        """
        Import atlases from the CSV file.

        The file has no header row.

        Each line of the CSV file should have the format:
        id,name_atlas,label1,label2,label3,...
        """
        if self.atlas_repository is None:
            raise ValueError("Atlas repository is not set.")

        with open(self.csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            # Process each row
            for row in reader:
                if not row or len(row) < 2:  # Need at least id and name
                    raise ValueError(f"Invalid row: {row}")

                try:
                    # Extract atlas ID and name
                    atlas_id = int(row[0])
                    atlas_name = row[1]

                    # Extract labels (all remaining columns)
                    # Filter out empty strings and convert to integers
                    labels = [int(label) for label in row[2:] if label.strip()]

                    # Create and save the Atlas entity
                    atlas = Atlas(id=atlas_id, name=atlas_name, labels=labels)
                    self.atlas_repository.save_atlas(atlas)

                except (ValueError, IndexError) as e:
                    # Log error and continue with next row
                    print(f"Error importing atlas from row {row}: {str(e)}")
                    continue


class CSVNormativeDTIValuesImporter(CSVImporter):
    def import_data(self):
        pass

    def register_repository(self, repositories: list[Repository]):
        pass
