import pytest

from oxytcmri.domain.entities.subject import SubjectId
from oxytcmri.domain.ports.repositories import Repository
from oxytcmri.infrastructure.importers.csv import CSVCenterImporter, CSVAtlasImporter, CSVNormativeDTIValuesImporter, \
    CSVImporter
from oxytcmri.infrastructure.importers.nifti_folders import NiftiFoldersImporter
from oxytcmri.tests.fixtures import path_to_test_data_folder
from oxytcmri.tests.unit.domain.mocks import (
    MockAtlasRepository,
    MockInMemoryMRIExamRepository,
    MockInMemorySubjectRepository,
    MockInMemoryNormativeValuesRepository,
    MockCenterRepository
)


class TestCSVImporter:
    @pytest.fixture()
    def mock_csv_importer(self):
        class MockCSVImporter(CSVImporter):
            def import_data(self):
                raise NotImplementedError

            def register_repository(self, repositories: list[Repository]):
                raise NotImplementedError

        return MockCSVImporter

    def test_raises_error_if_file_does_not_exist(self, mock_csv_importer):
        with pytest.raises(FileNotFoundError):
            mock_csv_importer("non/existing/file.csv")


class TestCSVCenterImporter:
    @pytest.fixture()
    def tmp_csv_file(self, tmp_path):
        csv_file = tmp_path / "centers.csv"
        csv_file.write_text("id,name\n1,Center 1\n2,Center 2\n3,Center 3")
        return str(csv_file)

    def test_imports_centers_from_csv(self, tmp_csv_file):
        mock_empty_center_repository = MockCenterRepository(centers=[])
        center_importer = CSVCenterImporter(tmp_csv_file, mock_empty_center_repository)
        center_importer.import_data()
        centers = mock_empty_center_repository.list_all()
        assert len(centers) == 3
        assert centers[0].id == 1
        assert centers[0].name == "Center 1"


class TestAtlasImporter:
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
        atlases = atlas_repository.list_all()
        assert len(atlases) == 2


class TestNiftiFoldersImporter:
    @pytest.fixture()
    def atlas_repository(self):
        return MockAtlasRepository()

    @pytest.fixture()
    def mri_exam_repository(self, atlas_repository):
        return MockInMemoryMRIExamRepository()

    @pytest.fixture()
    def empty_subject_repository(self):
        return MockInMemorySubjectRepository(subject_ids=[])

    def test_raises_error_if_file_does_not_exist(self,
                                                 empty_subject_repository,
                                                 atlas_repository,
                                                 mri_exam_repository):
        with pytest.raises(FileNotFoundError):
            NiftiFoldersImporter(base_path="non/existing/file.csv",
                                 subject_repository=empty_subject_repository,
                                 mri_exam_repository=mri_exam_repository,
                                 atlas_repository=atlas_repository)

    @pytest.fixture
    def folder_base_path(self) -> str:
        return str(path_to_test_data_folder() / "NiftiFoldersMRIExamRepository")

    def test_import_data(self,
                         folder_base_path,
                         atlas_repository,
                         mri_exam_repository,
                         empty_subject_repository):
        # initialize subject repository
        subject_repository = empty_subject_repository
        # build importer with this repository, and import data
        importer = NiftiFoldersImporter(folder_base_path,
                                        subject_repository,
                                        mri_exam_repository,
                                        atlas_repository)
        importer.import_data()

        # Check that the data was imported correctly
        for subject_id in ["01-01-V", "01-13-P", "02-01-T"]:
            assert subject_repository.find_by_id(subject_id) is not None
            mri_exam = mri_exam_repository.get_exam_for_subject(subject_id=SubjectId(subject_id))
            assert mri_exam is not None
            assert len(mri_exam.get_all_mri_data()) > 0


class TestCSVNormativeDTIValuesImporter:
    @pytest.fixture
    def tmp_csv_file(self, tmp_path):
        csv_file = tmp_path / "normative_dti_values.csv"
        with open(csv_file, 'w') as f:
            f.write("id,center_id,dti_metric,atlas_id,atlas_label,statistic_strategy,value\n")
            f.write("1,1,FA,2,29,mean,0.5\n")
        return str(csv_file)

    def test_imports_normative_dti_values_from_csv(self, tmp_csv_file):
        mock_normative_dti_values_repository = MockInMemoryNormativeValuesRepository()
        normative_dti_values_importer = CSVNormativeDTIValuesImporter(
            csv_file_path=tmp_csv_file,
            atlas_repository=MockAtlasRepository(),
            center_repository=MockCenterRepository(),
            normative_dti_values_repository=mock_normative_dti_values_repository
        )
        normative_dti_values_importer.import_data()
        normative_dti_values = mock_normative_dti_values_repository.get_all()
        assert len(normative_dti_values) == 1
        assert normative_dti_values[0].value == pytest.approx(0.5)
        assert normative_dti_values[0].atlas_label == 29
