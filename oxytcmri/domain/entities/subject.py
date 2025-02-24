from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re

class SubjectType(str, Enum):
    HEALTHY_VOLUNTEER = "Healthy Control"
    PATIENT = "Patient"
    TEST_PATIENT = "Patient Test"

class Sex(str, Enum):
    FEMALE = "F"
    MALE = "M"
    UNKNOWN = "nan"

@dataclass(frozen=True)
class SubjectId:
    """Value Object représentant l'identifiant d'un sujet"""
    center_number: int
    subject_number: int
    
    def __str__(self) -> str:
        return f"{self.center_number:02d}-{self.subject_number:02d}"
    
    @classmethod
    def from_string(cls, id_str: str) -> "SubjectId":
        pattern = r"^(\d{2})-(\d{2})$"
        match = re.match(pattern, id_str)
        if not match:
            raise ValueError(f"Invalid subject ID format: {id_str}. Expected format: XX-YY")
        
        center, number = match.groups()
        return cls(
            center_number=int(center),
            subject_number=int(number)
        )

@dataclass
class Subject:
    id: str  # On garde l'id sous forme de string pour l'instant
    subject_type: SubjectType
    center_id: int
    gose_6_months: Optional[int] = None
    gose_12_months: Optional[int] = None
    impact_score_mortality: Optional[float] = None
    impact_score_neurological_outcome: Optional[float] = None
    marshall_score: Optional[int] = None
    age: Optional[int] = None
    sex: Optional[Sex] = None
    glasgow_coma_scale: Optional[int] = None
    pbto2: Optional[bool] = None
    igs2_score: Optional[int] = None

    def update_gose(self, delay_in_month: int, gose_score: int) -> None:
        if delay_in_month == 6:
            self.gose_6_months = gose_score
        elif delay_in_month == 12:
            self.gose_12_months = gose_score
        else:
            raise ValueError("delay_in_month should be 6 or 12")

    def get_number_within_center(self) -> int:
        return int(self.id[3:5]) 