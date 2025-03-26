from pathlib import Path

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.ports.repositories import CenterRepository


class CSVCenterImporter:
    """
    Import centers from a CSV file to the repository.

    Attributes:
    -----------
        filepath: str
            The path to the CSV file.
        center_repository: CenterRepository
            The repository to save the centers.
    """
    def __init__(self, filepath: str, center_repository: CenterRepository):
        self.filepath = Path(filepath)
        # Ensure that the CSV file exists
        if not self.filepath.exists():
            raise FileNotFoundError(f"CSV file not found: '{self.filepath}'.")

        self.center_repository = center_repository

    def import_centers(self) -> None:
        """
        Import centers from the CSV file to the repository.

        Returns:
        --------
        None
        """
        import csv

        with open(self.filepath, mode='r') as file:
            reader = csv.DictReader(file)
            centers = [Center(id=int(row['id']), name=row['name']) for row in reader]

        self.center_repository.save_centers(centers)
