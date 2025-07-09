from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, List

from oxytcmri.domain.entities.mri import MRIExam, MRIData, DTIMetric, DTIMap, AtlasSegmentation, MRIExamId, \
    DTIAbnormalValues
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.repositories import MRIExamRepository, AtlasRepository, Entity
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData


@dataclass
class FileInfo:
    filepath: Path
    filename: str
    mri_exam_id: MRIExamId


class MRIDataFactory(Protocol):
    def create_mri_data(self, file_info: FileInfo) -> MRIData:
        pass


class DTIMapFactory:
    @staticmethod
    def create_mri_data(file_info: FileInfo) -> DTIMap:
        metric_name = file_info.filename.split("_")[0]
        metric = DTIMetric.from_acronym(metric_name)
        return DTIMap(
            mri_exam_id=file_info.mri_exam_id,
            voxel_data=NiftiVoxelData[float](file_info.filepath),
            dti_metric=metric,
        )


class AtlasSegmentationFactory:
    def __init__(self, atlas_repository: AtlasRepository):
        self.atlas_repository = atlas_repository

    def create_mri_data(self, file_info: FileInfo) -> AtlasSegmentation:
        atlas_id = int(file_info.filename[5:6])
        atlas = self.atlas_repository.get_by_id(atlas_id)
        return AtlasSegmentation(
            mri_exam_id=file_info.mri_exam_id,
            voxel_data=NiftiVoxelData[int](file_info.filepath),
            atlas=atlas,
        )


class DTISegmentationFactory:
    """
    Factory for creating DTI segmentation MRI data.
    """

    def create_mri_data(self, file_info: FileInfo) -> MRIData:
        source_dti_map = self._create_source_dti_map(file_info)
        result = DTIAbnormalValues.from_dti_map(source_dti_map)
        # modify voxel_data in order to register only what we need: the filepath
        result.voxel_data = NiftiVoxelData(nifti_path=file_info.filepath)
        return result

    @staticmethod
    def _create_source_dti_map(file_info: FileInfo) -> DTIMap:
        source_file_info = FileInfo(
            filepath=file_info.filepath,
            filename=file_info.filename.replace("_segmentation", "_map"),
            mri_exam_id=file_info.mri_exam_id
        )
        return DTIMapFactory.create_mri_data(source_file_info)


class DefaultMRIDataFactory:
    @staticmethod
    def create_mri_data(file_info: FileInfo) -> MRIData:
        return MRIData(
            mri_exam_id=file_info.mri_exam_id,
            voxel_data=NiftiVoxelData[float](file_info.filepath),
            name=file_info.filename,
        )


class NiftiFoldersMRIExamRepository(MRIExamRepository):
    def __init__(self, base_path: str, atlas_repository: AtlasRepository = None):
        self.base_path = Path(base_path)
        self.atlas_repository = atlas_repository

        if not self.base_path.exists():
            raise FileNotFoundError(f"path '{base_path}' does not exist.")

        self.mri_exam_list = self.scan_nifti_folders() if atlas_repository else []

    def _get_factory(self, filename: str) -> MRIDataFactory:
        if filename.endswith("_map"):
            return DTIMapFactory()
        if filename.endswith("_segmentation"):
            return DTISegmentationFactory()
        if filename.startswith("Atlas"):
            return AtlasSegmentationFactory(self.atlas_repository)
        return DefaultMRIDataFactory()

    def _create_mri_data(self, file_path: Path, filename: str, mri_exam_id: MRIExamId) -> MRIData:
        file_info = FileInfo(file_path, filename, mri_exam_id)
        factory = self._get_factory(filename)
        return factory.create_mri_data(file_info)

    def exists(self, entity: Entity) -> bool:
        """Check if an MRI exam exists in the repository.

        Parameters
        ----------
        entity : Entity
            The entity to check for existence

        Returns
        -------
        bool
            True if the entity exists, False otherwise
        """
        # check if the entity is an instance of MRIExam
        if not isinstance(entity, MRIExam):
            raise TypeError(f"Expected MRIExam, got {type(entity)}")

        # check if the entity's ID exists in the list of MRI exams
        return any(mri_exam.id == entity.id for mri_exam in self.mri_exam_list)

    def scan_nifti_folders(self) -> list[MRIExam]:
        """
        Scan the base path for NIfTI folders and create MRIExam objects.

        Returns
        -------
        list[MRIExam]
            A list of MRIExam objects representing the NIfTI folders found in the base path.
        """
        result = []

        for mri_exam_folder in self.base_path.iterdir():
            if mri_exam_folder.is_dir():
                mri_exam = self._create_mri_exam_from_folder(mri_exam_folder)
                if mri_exam is not None:
                    result.append(mri_exam)

        return result

    def _create_mri_exam_from_folder(self, folder_path: Path) -> MRIExam:
        """
        Create an MRIExam object from a folder containing NIfTI files.

        Parameters
        ----------
        folder_path : Path
            Path to the folder containing NIfTI files

        Returns
        -------
        MRIExam
            A fully initialized MRIExam object with loaded data
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Path '{folder_path}' does not exist.")
        if not folder_path.is_dir():
            raise ValueError(f"Path '{folder_path}' is not a directory.")
        string_mri_exam_id = folder_path.name

        # Create basic MRIExam object
        mri_exam = MRIExam.from_string_exam_id(string_mri_exam_id)

        # Load NIfTI files and populate the MRIExam object
        for file in folder_path.iterdir():
            if file.is_file() and file.name.endswith('.nii.gz'):
                filename = file.name.removesuffix('.nii.gz')
                mri_data = self._create_mri_data(file, filename, mri_exam.id)
                mri_exam.add_mri_data(mri_data)

        return mri_exam

    def get_exam_for_subject(self, subject: Subject) -> MRIExam:
        """Retrieve the MRI exam for a specific subject.

        Parameters
        ----------
        subject : Subject
            The subject to retrieve the MRI exam for

        Returns
        -------
        MRIExam
            The MRI exam for the subject
        """
        for mri_exam in self.mri_exam_list:
            if mri_exam.subject_id == subject.id:
                return mri_exam

        raise LookupError(f"No MRI exam found for subject {subject}")

    def find_by_id(self, entity_id: MRIExamId) -> Optional[MRIExam]:
        """Find an MRIExam by its ID.

        Parameters
        ----------
        entity_id : MRIExamId
            The ID of the MRI exam

        Returns
        -------
        Entity
            The entity if found, otherwise None
        """
        for mri_exam in self.mri_exam_list:
            if mri_exam.id == entity_id:
                return mri_exam
        return None

    def list_all(self) -> List[MRIExam]:
        """List all MRI exams in the repository.

        Returns
        -------
        List[MRIExam]
            A list of all MRI exams in the repository
        """
        return self.mri_exam_list

    def delete(self, entity: Entity) -> None:
        raise NotImplementedError("Deleting MRI exams is not supported in this repository.")

    def save(self, mri_exam: MRIExam) -> None:
        raise NotImplementedError("Saving MRI exams is not supported in this repository.")
