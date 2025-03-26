import pytest

from oxytcmri.infrastructure.importers import CSVCenterImporter
from oxytcmri.tests.unit.domain.mocks import MockEmptyCenterRepository


class TestCSVImporter:
    def test_raises_error_if_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            center_importer = CSVCenterImporter("non/existing/file.csv", MockEmptyCenterRepository())

    @pytest.fixture()
    def tmp_csv_file(self, tmp_path):
        csv_file = tmp_path / "centers.csv"
        csv_file.write_text("id,name\n1,Center 1\n2,Center 2\n3,Center 3")
        return str(csv_file)

    def test_imports_centers_from_csv(self, tmp_csv_file):
        mock_center_repository = MockEmptyCenterRepository()
        center_importer = CSVCenterImporter(tmp_csv_file, mock_center_repository)
        center_importer.import_centers()
        centers = mock_center_repository.get_all_centers()
        assert len(centers) == 3
        assert centers[0].id == 1
        assert centers[0].name == "Center 1"
