from dataclasses import dataclass
from typing import List, Optional, Protocol
from pathlib import Path
import numpy as np

class VoxelData(Protocol):
    """Interface pour les données voxeliques"""
    def get_value_at(self, x: int, y: int, z: int) -> float: ...
    def get_dimensions(self) -> tuple[int, int, int]: ...
    def get_voxel_volume(self) -> float: ...  # en mL

@dataclass(frozen=True)
class MRIExamId:
    """Value Object représentant l'identifiant d'un examen IRM"""
    id: str
    
    def __str__(self) -> str:
        return self.id

@dataclass
class MRIData:
    """Représente une donnée IRM 3D"""
    id: str
    name: str  # ex: "Atlas3", "FA_map", "MD_high_lesions"
    filepath: Path
    
    def get_voxel_data(self) -> VoxelData:
        """
        Retourne les données voxeliques.
        L'implémentation sera fournie par l'infrastructure.
        """
        raise NotImplementedError

@dataclass
class MRIExam:
    """Un examen IRM complet"""
    id: MRIExamId
    subject_id: str
    data: List[MRIData]

    def get_data(self, name: str) -> Optional[MRIData]:
        return next((d for d in self.data if d.name == name), None) 