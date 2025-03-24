import re
from dataclasses import dataclass
from typing import List, Optional, Generic, TypeVar
from abc import ABC, abstractmethod
from enum import Enum

T = TypeVar("T")


class DTIMetric(Enum):
    """Different metrics derived from diffusion tensor imaging."""

    MD = "Mean Diffusivity"
    FA = "Fractional Anisotropy"
    AD = "Axial Diffusivity"
    RD = "Radial Diffusivity"

    @classmethod
    def from_acronym(cls, acronym: str):
        """
        Get a DTIMetric enum value from its acronym.

        Parameters
        ----------
        acronym : str
            The acronym (e.g., 'MD', 'FA')

        Returns
        -------
        DTIMetric
            The corresponding enum value

        Raises
        ------
        ValueError
            If no enum value matches the given acronym
        """
        for metric in cls:
            if metric.name == acronym:
                return metric
        raise ValueError(f"No DTIMetric found for acronym: {acronym}")


@dataclass
class Atlas:
    """
    An atlas is a set of labels that can be used to segment the brain.
    """

    id: str
    labels: List[int]
    name: str = None


@dataclass
class RegionOfInterest:
    """
    Represents a Region of Interest (ROI) in medical imaging.

    Parameters
    ----------
    atlas : Atlas
        The atlas used to define the region
    labels : List[int]
        The list of labels within the atlas defining the region
    """

    atlas: Atlas
    labels: List[int]


class VoxelData(ABC, Generic[T]):
    """
    Protocol defining the interface for voxel data access.

    This interface abstracts the underlying data representation (numpy arrays, etc.)
    to keep the domain layer independent from technical implementations.
    """

    @abstractmethod
    def get_value_at(self, x: int, y: int, z: int) -> T:
        """
        Get the value of a voxel at a specific position.

        Parameters
        ----------
        x : int
            x-coordinate of the voxel
        y : int
            y-coordinate of the voxel
        z : int
            z-coordinate of the voxel

        Returns
        -------
        T
            Value of the voxel
        """

    @abstractmethod
    def get_dimensions(self) -> tuple[int, int, int]:
        """
        Get the dimensions of the voxel data.

        Returns
        -------
        tuple[int, int, int]
            Dimensions of the voxel data
        """

    @abstractmethod
    def get_voxel_volume_in_ml(self) -> float:
        """
        Get the volume of a voxel in milliliters (mL).

        Returns
        -------
        float
            Volume of a voxel, in mL.
        """


@dataclass(frozen=True)
class MRIExamId:
    """
    Value Object representing an MRI examination identifier.

    The ID can have different formats in the database:
    - "06-08P-MR-170918"
    - "10_03V_MR301015"
    - "13-03P-190717"
    """

    id: str

    def __str__(self) -> str:
        return self.id

    def to_subject_id(self) -> str:
        """
        Convert the MRIExamId to a subject ID.

        For example:
        - "06-08P-MR-170918" -> "06-08-P"
        - "10_03V_MR301015" -> "10-03-V"
        - "13-03P-190717" -> "13-03-P"

        Returns
        -------
        str
            The subject ID derived from the MRIExamId
        """
        cleaned = re.sub(r"[-_]", "", self.id.upper())

        if len(cleaned) < 5:
            raise ValueError(f"Invalid MRIExamId format (too short): {self.id}")

        center = cleaned[0:2]
        subject = cleaned[2:4]
        subject_type = cleaned[4]

        if not center.isdigit() or not subject.isdigit():
            raise ValueError(f"Invalid center or subject number in ID: {self.id}")
        if subject_type not in {"P", "V", "T"}:
            raise ValueError(f"Invalid subject type (expected P, V or T) in ID: {self.id}")

        return f"{center}-{subject}-{subject_type}"


class MRIData(Generic[T]):
    """
    Represents a 3D MRI data volume.

    This can be:
    - An anatomical sequence (T1, T2, FLAIR)
    - A DTI-derived map (MD, FA)
    - An atlas or segmentation mask

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Name of the data (e.g. "Atlas3", "FA_map", etc.)
    voxel_data_provider : VoxelData
        Provider for voxel data
    """

    def __init__(
            self, id: str, name: str, voxel_data: VoxelData
    ) -> None:
        self.id = id
        self.name = name
        self.voxel_data = voxel_data

    def get_voxel_data(self) -> VoxelData[T]:
        """
        Get the voxel data of this MRI volume.

        Returns
        -------
        VoxelData[T]
            Interface to access the underlying voxel data
        """
        return self.voxel_data


@dataclass
class MRIExam:
    """
    A complete MRI examination.

    Contains all the MRI data (sequences, maps, masks) associated with a subject's exam.

    Parameters
    ----------
    id : MRIExamId
        Unique identifier of the exam
    subject_id : str
        ID of the subject who underwent the exam
    data : List[MRIData]
        List of all MRI data associated with this exam
    """

    id: MRIExamId
    subject_id: str
    data: List[MRIData]

    def __init__(self, id: str, subject_id: str = "", data: List[MRIData] = None) -> None:
        mri_exam_id = MRIExamId(id)
        self.id = mri_exam_id
        self.subject_id = subject_id if subject_id else mri_exam_id.to_subject_id()
        self.data = data if data is not None else []

    def get_data(self, name: str) -> Optional[MRIData]:
        """
        Get MRI data by its name.

        Parameters
        ----------
        name : str
            Name of the data to retrieve

        Returns
        -------
        Optional[MRIData]
            The requested data if found, None otherwise
        """
        return next((d for d in self.data if d.name == name), None)

    def get_dti_map(self, metric: DTIMetric) -> MRIData:
        """
        Retrieve the DTI map for a specific metric.

        Parameters
        ----------
        metric : DTIMetric
            The type of DTI metric to retrieve

        Returns
        -------
        MRIData
            The DTI map for the specified metric
        """
        return next((d for d in self.data if d.name == metric.value), None)

    def get_atlas_segmentation(self, atlas: Atlas) -> MRIData:
        """
        Retrieve the segmentation for a specific atlas.

        Parameters
        ----------
        atlas : Atlas

        Returns
        -------
        MRIData
            The atlas segmentation data
        """
        # look for atlas by atlas id
        atlas_data = next((d for d in self.data if d.name == str(atlas.id)), None)

        return atlas_data

    def get_mask(self, roi: RegionOfInterest) -> "Mask":
        """
        Create a mask for a given region of interest.

        Parameters
        ----------
        roi : RegionOfInterest
            The region of interest to create a mask for

        Returns
        -------
        Mask
            A mask representing the specified region of interest
        """
        # Get the atlas segmentation data for the ROI's atlas
        atlas_segmentation = self.get_atlas_segmentation(roi.atlas)
        if atlas_segmentation is None:
            raise LookupError(f"Atlas segmentation not found for atlas "
                              f"'{roi.atlas.id}' in MRI exam '{self.id}'")

        # Get voxel data from atlas segmentation
        voxel_data = atlas_segmentation.get_voxel_data()

        # Create a mask that includes all specified labels
        mask = voxel_data.create_mask(roi.labels)

        return mask

    def extract_dti_values_for_region(
            self, dti_metric: DTIMetric, roi: RegionOfInterest
    ) -> List[float]:
        """
        Extract DTI metric values for a specific region of interest.

        Parameters
        ----------
        dti_metric : DTIMetric
            The type of DTI metric to extract (MD, FA, etc.)
        roi : RegionOfInterest
            The region of interest to extract values from

        Returns
        -------
        List[float]
            DTI values corresponding to the specified ROI
        """
        # Get the DTI metric data for the specified metric
        dti_map = self.get_dti_map(dti_metric)

        # Create a mask for the ROI
        mask = self.get_mask(roi)

        # Get voxel data from DTI map
        voxel_data = dti_map.get_voxel_data()

        # Apply the mask to DTI data to extract values
        dti_values = voxel_data.apply_mask(mask)

        return dti_values

    def add_mri_data(self, mri_data: MRIData) -> None:
        """
        Add MRI data to the MRI exam

        Parameters
        ----------
        mri_data : MRIData
            The MRI data to add to the exam

        Returns
        -------
        None
        """
        self.data.append(mri_data)
