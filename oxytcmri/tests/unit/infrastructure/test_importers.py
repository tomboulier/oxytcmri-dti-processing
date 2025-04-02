import pytest

from oxytcmri.interface.importers import CSVCenterImporter, CSVAtlasImporter, NiftiFoldersImporter
from oxytcmri.tests.fixtures import path_to_test_data_folder
from oxytcmri.tests.unit.domain.mocks import MockEmptyCenterRepository, MockAtlasRepository, \
    MockInMemoryEmptyMRIRepository, \
    MockInMemoryEmptySubjectRepository


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
        center_importer.import_data()
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
        atlas_importer.import_data()
        atlases = atlas_repository.get_all_atlases()
        assert len(atlases) == 2


class TestNiftiFoldersImporter:
    @pytest.fixture()
    def atlas_repository(self):
        return MockAtlasRepository()

    @pytest.fixture()
    def mri_exam_repository(self, atlas_repository):
        return MockInMemoryEmptyMRIRepository()

    @pytest.fixture()
    def subject_repository(self):
        return MockInMemoryEmptySubjectRepository()

    def test_raises_error_if_file_does_not_exist(self,
                                                 atlas_repository,
                                                 mri_exam_repository,
                                                 subject_repository):
        with pytest.raises(FileNotFoundError):
            NiftiFoldersImporter(base_path="non/existing/file.csv",
                                 subject_repository=subject_repository,
                                 mri_exam_repository=mri_exam_repository,
                                 atlas_repository=atlas_repository)

    @pytest.fixture
    def folder_base_path(self) -> str:
        return str(path_to_test_data_folder() / "NiftiFoldersMRIExamRepository")

    def test_import_data(self,
                         folder_base_path,
                         atlas_repository,
                         mri_exam_repository,
                         subject_repository):
        importer = NiftiFoldersImporter(folder_base_path,
                                        subject_repository,
                                        mri_exam_repository,
                                        atlas_repository)
        importer.import_data()

        # Check that the data was imported correctly
        for subject_id in ["01-01-V", "01-13-P", "02-01-T"]:
            assert subject_repository.find_by_id(subject_id) is not None
            mri_exam = mri_exam_repository.get_exam_for_subject(subject_id=subject_id)
            assert mri_exam is not None
            assert len(mri_exam.get_all_mri_data()) > 0
