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
    HEALTHY_VOLUNTEER = "Healthy Volunteer"
    PATIENT = "Patient"
    TEST_PATIENT = "Test Patient"

    @classmethod
    def from_string(cls, value: str) -> "SubjectType":
        """
        Convert a string to a SubjectType.

        Parameters
        ----------
        value: str
            String to convert to a SubjectType. Must be "T", "V", or "P".

        Returns
        -------
        SubjectType
            The corresponding SubjectType.

        Raises
        ------
        ValueError
            If the string is not "H", "V", or "P"
        """
        if value == "V":
            return cls.HEALTHY_VOLUNTEER
        if value == "P":
            return cls.PATIENT
        if value == "T":
            return cls.TEST_PATIENT

        raise ValueError(f"Invalid subject type: {value}. Expected 'V', 'P', or 'T'.")




@dataclass
class Subject:
    """
    A subject participating in the study.

    Can be a healthy volunteer, a patient, or a test patient.
    """
    id: str
    subject_type: SubjectType
    center_id: int

    @classmethod
    def from_string_id(cls, id_str: str) -> "Subject":
        """
        Create a Subject from its string identifier.

        Parameters
        ----------
        id_str : str
            String in the format "XX-YY-Z" where:
            - XX is the center number (01-99)
            - YY is the subject number within the center (01-99)
            - Z is the subject type (P, V, T)

        Returns
        -------
        Subject
            The created Subject instance
        """
        if not re.match(r"\d{2}-\d{2}-[PVT]", id_str):
            raise ValueError(f"Invalid subject ID: {id_str}. Expected format: 'XX-YY-Z'")

        subject_type = SubjectType.from_string(id_str[-1])
        center_id = int(id_str[:2])

        return cls(
            id=id_str,
            subject_type=subject_type,
            center_id=center_id
        )
