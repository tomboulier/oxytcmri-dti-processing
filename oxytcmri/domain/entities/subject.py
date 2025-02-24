from dataclasses import dataclass
from enum import Enum
import re

class SubjectType(str, Enum):
    """
    Types of subjects in the study.

    A subject can be:
    - a healthy volunteer: passed an MRI to compare DTI values with patients
    - a test patient: sometimes centers needed to test an MRI on a patient
    - a patient: a patient in the trial
    """
    HEALTHY_VOLUNTEER = "Healthy Control"
    PATIENT = "Patient"
    TEST_PATIENT = "Patient Test"

@dataclass(frozen=True)
class SubjectId:
    """
    Value Object representing a subject identifier.
    
    The ID follows the format "XX-YY" where:
    - XX is the center number (01-99)
    - YY is the subject number within the center (01-99)
    """
    center_number: int
    subject_number: int
    
    def __str__(self) -> str:
        return f"{self.center_number:02d}-{self.subject_number:02d}"
    
    @classmethod
    def from_string(cls, id_str: str) -> "SubjectId":
        """
        Create a SubjectId from its string representation.

        Parameters
        ----------
        id_str : str
            String in the format "XX-YY"

        Returns
        -------
        SubjectId
            The created SubjectId instance

        Raises
        ------
        ValueError
            If the string format is invalid
        """
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
    """
    A subject participating in the study.

    Can be a healthy volunteer, a patient, or a test patient.
    """
    id: SubjectId
    subject_type: SubjectType
    center_id: int
