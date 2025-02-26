from dataclasses import dataclass
from typing import List, Optional, Protocol
from pathlib import Path

class VoxelData(Protocol):
    """
    Protocol defining the interface for voxel data access.

    This interface abstracts the underlying data representation (numpy arrays, etc.)
    to keep the domain layer independent from technical implementations.
    """
    def get_value_at(self, x: int, y: int, z: int) -> float: ...
    def get_dimensions(self) -> tuple[int, int, int]: ...
    def get_voxel_volume(self) -> float: ...  # en mL

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

@dataclass
class MRIData:
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
    filepath : Path
        Path to the data file
    """
    id: str
    name: str
    filepath: Path
    
    def get_voxel_data(self) -> VoxelData:
        """
        Get the voxel data of this MRI volume.

        Returns
        -------
        VoxelData
            Interface to access the underlying voxel data

        Notes
        -----
        Implementation is provided by the infrastructure layer
        """
        raise NotImplementedError

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