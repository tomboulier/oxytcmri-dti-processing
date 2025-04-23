"""
This module contains the `Subject` class which represents a subject in the Oxy-TC trial,
as well as the associated value objects:

- `SubjectType`: Represents the type of subject (e.g., "healthy volunteer", "patient");
- `SubjectID`: Represents the unique identifier for a subject.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


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


@dataclass(frozen=True)
class SubjectId:
    """Value Object representing a subject identifier.

    The ID follows the format "XX-YY-Z" where:
    
    - XX is the center number (01-99)
    - YY is the subject number within the center (01-99)
    - Z is the subject type (P, V, T)

    Examples: "01-02-P", "10-03-V", "13-03-P"
    """
    id: str

    def __post_init__(self):
        if not re.match(r"\d{2}-\d{2}-[PVT]", self.id):
            raise ValueError(
                f"Invalid subject ID: {self.id}. Expected format: 'XX-YY-Z'"
            )

    def __str__(self) -> str:
        return self.id

    @property
    def center_id(self) -> int:
        """Get the center ID from the subject ID."""
        return int(self.id[:2])

    @property
    def subject_number(self) -> str:
        """Get the subject number within the center."""
        return self.id[3:5]

    @property
    def subject_type(self) -> SubjectType:
        """Get the subject type."""
        return SubjectType.from_string(self.id[-1])


@dataclass
class Subject:
    """
    A subject participating in the study.

    Can be a healthy volunteer, a patient, or a test patient.
    """

    id: SubjectId
    subject_type: SubjectType
    center_id: int

    @classmethod
    def from_string_id(cls, id_str: str) -> Subject:
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
        subject_id = SubjectId(id_str)
        subject_type = subject_id.subject_type
        center_id = subject_id.center_id

        return cls(id=subject_id, subject_type=subject_type, center_id=center_id)
