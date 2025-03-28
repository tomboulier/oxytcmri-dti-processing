from pathlib import Path

from oxytcmri.domain.entities.mri import MRIExam, MRIData, DTIMetric, DTIMap, AtlasSegmentation
from oxytcmri.domain.ports.repositories import MRIExamRepository, AtlasRepository
from oxytcmri.interface.mri.voxel_data_adapters import NiftiVoxelData


class NiftiFoldersMRIExamRepository(MRIExamRepository):
    def __init__(self, base_path: str, atlas_repository: AtlasRepository):
        """Initialize the repository with a base path for NIfTI files.

        Parameters
        ----------
        base_path : str
            The base path where NIfTI files are stored.
        """
        self.base_path = Path(base_path)
        self.atlas_repository = atlas_repository

        # Ensure that the base path exists
        if not self.base_path.exists():
            raise FileNotFoundError(f"path '{base_path}' does not exist.")

        self.mri_exam_list = self.scan_nifti_folders()

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
        mri_exam_id = folder_path.name

        # Create basic MRIExam object
        mri_exam = MRIExam(id=mri_exam_id)

        # Load NIfTI files and populate the MRIExam object
        for file in folder_path.iterdir():
            if file.is_file() and file.name.endswith('.nii.gz'):
                # Determine MRI data type based on file name
                if "map" in file.stem.lower():
                    # This is a DTI map
                    metric_name = file.stem.split("_")[0]
                    metric = DTIMetric.from_acronym(metric_name)
                    dti_map = DTIMap(
                        id=f"{mri_exam_id}_{file.stem}",
                        name=file.stem,
                        voxel_data=NiftiVoxelData[float](file),
                        dti_metric=metric,
                    )
                    mri_exam.add_mri_data(dti_map)
                elif file.stem.startswith("Atlas"):
                    # This is an atlas segmentation
                    atlas_name = file.name.removesuffix('.nii.gz')
                    atlas_id = int(file.stem[5:6])
                    atlas = self.atlas_repository.get_atlas_by_id(atlas_id)
                    atlas_segmentation = AtlasSegmentation(
                        id=f"{mri_exam_id}_{atlas_name}",
                        name=atlas_name,
                        voxel_data=NiftiVoxelData[int](file),
                        atlas=atlas,
                    )
                    mri_exam.add_mri_data(atlas_segmentation)
                else:
                    # Load the NIfTI file and add it to the MRIExam object
                    voxel_data = NiftiVoxelData[float](file)
                    mri_data = MRIData(id=f"{mri_exam_id}_{file.stem}",
                                       name=file.stem,
                                       voxel_data=voxel_data)
                    mri_exam.add_mri_data(mri_data)

        return mri_exam

    def get_exam_for_subject(self, subject_id: str) -> MRIExam:
        """Retrieve the MRI exam for a specific subject.

        Parameters
        ----------
        subject_id : str
            The ID of the subject

        Returns
        -------
        MRIExam
            The MRI exam for the subject
        """
        for mri_exam in self.mri_exam_list:
            if mri_exam.subject_id == subject_id:
                return mri_exam

        raise LookupError(f"No MRI exam found for subject {subject_id}")

    def save(self, mri_exam: MRIExam) -> None:
        raise NotImplementedError("Saving MRI exams is not supported in this repository.")
