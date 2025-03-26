import pytest

from oxytcmri.infrastructure.importers import CSVCenterImporter, CSVAtlasImporter
from oxytcmri.tests.unit.domain.mocks import MockEmptyCenterRepository, MockAtlasRepository


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


class TestAtlasImporter:
    def test_raises_error_if_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            atlas_importer = CSVAtlasImporter("non/existing/file.csv", MockEmptyCenterRepository())

    @pytest.fixture()
    def tmp_csv_file(self, tmp_path):
        csv_file = tmp_path / "atlases.csv"
        csv_file.write_text("2,Neuromorphometrics atlas + GM parcels size ≤5cm3,29,33,62\n"
                            "4,Neuromorphometrics atlas + GM parcels size >5cm3,29, 33, 59, 60, 62")
        return str(csv_file)

    def test_imports_atlases_from_csv(self, tmp_csv_file):
        # start with empty atlas repository
        atlas_repository = MockAtlasRepository(atlases={})
        # create importer
        atlas_importer = CSVAtlasImporter(tmp_csv_file, atlas_repository)
        # import
        atlas_importer.import_atlases()
        atlases = atlas_repository.get_all_atlases()
        assert len(atlases) == 2
