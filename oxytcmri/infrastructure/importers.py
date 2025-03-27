import csv
from pathlib import Path

from oxytcmri.domain.entities.mri import Atlas
from oxytcmri.domain.ports.repositories import AtlasRepository
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
        with open(self.filepath, mode='r') as file:
            reader = csv.DictReader(file)
            centers = [Center(id=int(row['id']), name=row['name']) for row in reader]

        self.center_repository.save_centers(centers)


class CSVAtlasImporter:
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

    def __init__(self, csv_file_path: str, atlas_repository: AtlasRepository):
        """
        Initialize the importer.

        Parameters:
        -----------
            csv_file_path: str
                Path to the CSV file containing atlas data.
            atlas_repository: AtlasRepository
                Repository for storing atlas entities.
        """
        self.csv_file_path = Path(csv_file_path)
        # Check if file exists
        if not self.csv_file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file_path}")
        self.atlas_repository = atlas_repository

    def import_atlases(self) -> None:
        """
        Import atlases from the CSV file.

        The file has no header row.

        Each line of the CSV file should have the format:
        id,name_atlas,label1,label2,label3,...
        """
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
