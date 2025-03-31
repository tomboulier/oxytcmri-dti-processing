from oxytcmri.domain.use_cases.compute_dti_normative_values import ComputeDTINormativeValues
from oxytcmri.interface.importers import (
    CSVCenterImporter, CSVAtlasImporter, NiftiFoldersImporter)
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseCenterRepository, DataBaseAtlasRepository, DataBaseSubjectRepository, DataBaseMRIExamRepository,
    DataBaseGateway, DataBaseDTINormativeValuesRepository
)
from oxytcmri.interface.repositories.nifti_folders_mri_exam_repository import NiftiFoldersMRIExamRepository


class Controller:
    def __init__(self,
                 center_importer: CSVCenterImporter,
                 atlas_importer: CSVAtlasImporter,
                 nifti_folder_importer: NiftiFoldersImporter,
                 atlas_repository: DataBaseAtlasRepository,
                 center_repository: DataBaseCenterRepository,
                 subjects_repository: DataBaseSubjectRepository,
                 mri_exams_repository: DataBaseMRIExamRepository,
                 normative_values_repository: DataBaseDTINormativeValuesRepository):
        self.atlases_repository = atlas_repository
        self.centers_repository = center_repository
        self.subjects_repository = subjects_repository
        self.mri_exams_repository = mri_exams_repository
        self.normative_values_repository = normative_values_repository

        # import data
        center_importer.import_centers()
        atlas_importer.import_atlases()
        nifti_folder_importer.import_data()

    def compute_normative_dti_values(self):
        compute_normative_dti_values = ComputeDTINormativeValues(
            atlas_repository=self.atlases_repository,
            normative_values_repository=self.normative_values_repository,
            centers_repository=self.centers_repository,
            subjects_repository=self.subjects_repository,
            mri_repository=self.mri_exams_repository
        )
        compute_normative_dti_values()
