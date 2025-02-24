from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass
class MRIData:
    """Représente une donnée IRM 3D"""
    id: str
    name: str  # ex: "Atlas3", "FA_map", "MD_high_lesions"
    filepath: Path

@dataclass
class MRIExam:
    """Un examen IRM complet"""
    id: str  # ex: "06-08P-MR-170918"
    subject_id: str
    data: List[MRIData]

    def get_data(self, name: str) -> Optional[MRIData]:
        return next((d for d in self.data if d.name == name), None) 