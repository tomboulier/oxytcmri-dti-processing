from typing import List

import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.ports.repositories import CenterRepository
from oxytcmri.infrastructure.importers import CSVCenterImporter


class MockCenterRepository(CenterRepository):
    def __init__(self):
        self.centers: List[Center] = []

    def get_all_centers(self) -> List[Center]:
        return self.centers

    def save_centers(self, centers: List[Center]):
        self.centers = centers


class TestCSVImporter:
    def test_raises_error_if_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            center_importer = CSVCenterImporter("non/existing/file.csv", MockCenterRepository())

    @pytest.fixture()
    def tmp_csv_file(self, tmp_path):
        csv_file = tmp_path / "centers.csv"
        csv_file.write_text("id,name\n1,Center 1\n2,Center 2\n3,Center 3")
        return str(csv_file)

    def test_imports_centers_from_csv(self, tmp_csv_file):
        mock_center_repository = MockCenterRepository()
        center_importer = CSVCenterImporter(tmp_csv_file, mock_center_repository)
        center_importer.import_centers()
        assert len(mock_center_repository.get_all_centers()) == 3
