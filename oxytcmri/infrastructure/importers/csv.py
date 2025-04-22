import csv
from abc import ABC
from pathlib import Path
from logging import getLogger

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import Atlas, DTIMetric
from oxytcmri.domain.use_cases.compute_dti_normative_values import (
    NormativeValueRepository, NormativeValue, StatisticsStrategies)
from oxytcmri.domain.ports.repositories import (
    CenterRepository, Repository, AtlasRepository
)
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
        logger = getLogger(__name__)
        logger.info(f"Importing centers from {self.csv_file_path}")

        if self.center_repository is None:
            raise ValueError("Center repository is not set.")

        with open(self.csv_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            centers = [Center(id=int(row['id']), name=row['name']) for row in reader]

        self.center_repository.save_centers(centers)

        logger.info(f"Imported {len(centers)} centers from {self.csv_file_path}")


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
        logger = getLogger(__name__)
        logger.info(f"Importing atlases from {self.csv_file_path}")

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

        logger.info(f"Successfully imported atlases from {self.csv_file_path}")


class CSVNormativeDTIValuesImporter(CSVImporter):
    """
    Service for importing normative DTI values from a CSV file.
    """

    def __init__(self,
                 csv_file_path: str,
                 center_repository: CenterRepository = None,
                 atlas_repository: AtlasRepository = None,
                 normative_dti_values_repository: NormativeValueRepository = None):
        """
        Initialize the importer.

        Parameters:
        -----------
            csv_file_path: str
                Path to the CSV file containing DTI values.
            center_repository: CenterRepository
                Repository for retrieving center entities.
            atlas_repository: AtlasRepository
                Repository for retrieving atlas entities.
            normative_dti_values_repository: NormativeValueRepository
                Repository for storing normative DTI values.
        """
        super().__init__(csv_file_path)
        self.center_repository = center_repository
        self.atlas_repository = atlas_repository
        self.normative_dti_values_repository = normative_dti_values_repository

    def register_repository(self, repositories: list[Repository]):
        repository_mapping = {
            AtlasRepository: 'atlas_repository',
            CenterRepository: 'center_repository',
            NormativeValueRepository: 'normative_dti_values_repository'
        }

        for repository in repositories:
            for repo_type, attr_name in repository_mapping.items():
                if isinstance(repository, repo_type):
                    setattr(self, attr_name, repository)
                    break

    def import_data(self) -> None:
        """
        Import normative DTI values from the CSV file.

        The CSV file should have the following columns:
        id,center_id,dti_metric,atlas_id,atlas_label,statistic_strategy,value
        """
        self.check_repositories()
        normative_values_to_import = []

        logger = getLogger(__name__)
        logger.info(f"Importing normative DTI values from {self.csv_file_path}")

        with open(self.csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                # Create the normative value,
                # and adds it to the list to be save
                normative_values_to_import.append(
                    NormativeValue(
                        center=self.get_center_from_id(int(row['center_id'])),
                        dti_metric=DTIMetric.from_acronym(row['dti_metric']),
                        atlas=self.get_atlas_from_id(int(row['atlas_id'])),
                        atlas_label=int(row['atlas_label']),
                        statistic_strategy=StatisticsStrategies.get_by_name(row['statistic_strategy']),
                        value=float(row['value'])
                    )
                )

        self.normative_dti_values_repository.batch_save(normative_values_to_import)

        logger.info(f"Successfully imported {len(normative_values_to_import)} normative DTI values "
                    f"from {self.csv_file_path}")

    def get_center_from_id(self, center_id: int) -> Center:
        """
        Retrieve a center from its ID.

        Parameters:
        -----------
            center_id: int
                The ID of the center to retrieve.

        Returns:
        --------
            Center: The center with the given ID.

        Raises:
        -------
            ValueError: If the center is not found in the repository.
        """
        center = self.center_repository.get_center_by_id(center_id)
        if center is None:
            raise ValueError(f"Center with ID {center_id} not found.")
        return center

    def get_atlas_from_id(self, atlas_id: int) -> Atlas:
        """
        Retrieve an atlas from its ID.

        Parameters:
        -----------
            atlas_id: int
                The ID of the atlas to retrieve.

        Returns:
        --------
            Atlas: The atlas with the given ID.

        Raises:
        -------
            ValueError: If the atlas is not found in the repository.
        """
        atlas = self.atlas_repository.get_atlas_by_id(atlas_id)
        if atlas is None:
            raise ValueError(f"Atlas with ID {atlas_id} not found.")
        return atlas

    def check_repositories(self) -> None:
        """
        Check if all required repositories are set.
        Raises:
        -------
            ValueError: If any repository is not set.
        """
        if self.normative_dti_values_repository is None:
            raise ValueError("Normative DTI values repository is not set.")
        if self.center_repository is None:
            raise ValueError("Center repository is not set.")
        if self.atlas_repository is None:
            raise ValueError("Atlas repository is not set.")
