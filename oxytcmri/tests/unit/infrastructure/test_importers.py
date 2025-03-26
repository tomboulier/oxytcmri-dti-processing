from typing import List

import pytest

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.ports.repositories import CenterRepository
from oxytcmri.infrastructure.importers import CSVCenterImporter


class MockCenterRepository(CenterRepository):
    def get_all_centers(self) -> List[Center]:
        pass
    
    def save_centers(self, centers: List[Center]):
        pass


class TestCSVImporter:
    def test_raises_error_if_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            center_importer = CSVCenterImporter("non/existing/file.csv", MockCenterRepository())
