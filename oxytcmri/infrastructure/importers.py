from pathlib import Path

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
