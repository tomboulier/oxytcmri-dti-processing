import csv
from pathlib import Path

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.ports.repositories import CenterRepository, Repository
from oxytcmri.interface.importers import Importer


class CSVCenterImporter(Importer):
    """
    Import centers from a CSV file to the repository.

    Attributes:
    -----------
        filepath: str
            The path to the CSV file.
        center_repository: CenterRepository
            The repository to save the centers.
    """

    def __init__(self, filepath: str, center_repository: CenterRepository = None):
        self.filepath = Path(filepath)
        # Ensure that the CSV file exists
        if not self.filepath.exists():
            raise FileNotFoundError(f"CSV file not found: '{self.filepath}'.")

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

        with open(self.filepath, mode='r') as file:
            reader = csv.DictReader(file)
            centers = [Center(id=int(row['id']), name=row['name']) for row in reader]

        self.center_repository.save_centers(centers)
