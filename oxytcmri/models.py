from typing import List, Optional
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship


class Center(SQLModel, table=True):
    """
    Model for the centers table.

    Attributes:
    - id (int): unique identifying number for the center (primary key)
    - name (str): usually the city name, sometimes the name of the hospital is added
    - subjects (List[Subject]): list of subjects belonging to the center
    """
    id: int = Field(primary_key=True)
    name: str = Field(max_length=30)
    subjects: List["Subject"] = Relationship(back_populates="center")


class SubjectType(str, Enum):
    """
        SubjectType will be used in class Subject, as an attribute.

        Indeed, a subject can be:
        - a healthy volunteer: he/she has passed an MRI in order to compare DTI values of patients.
        - a test patient: sometimes centers needed to test an MRI on a patient, but it will
            not be included in the analysis.
        - a patient: a patient in the trial; the DTI values will be compared with respect to the
            healthy volunteers of the same center.
    """
    healthy_volunteer = "healthy_volunteer"
    patient = "patient"
    test_patient = "test_patient"


class Subject(SQLModel, table=True):
    """
    Model for the subjects table.

    Attributes:
    - id (str): Unique identifier for the subject (primary key).
    - subject_type (SubjectType): Type of subject ("healthy_volunteer", "patient", "test_patient").
    - center_id (Optionnal[int]): id referring to the Center model.
    - center (Center): relationship to the Center model (one-to-many).
    - mri_exam_id (Optionnal[int]): id referring to the ExamMRI model.
    - mri_exam (Optional[MRIExam]): relationship to the ExamMRI model (one-to-one).

    N.B. the one-to-one relationship with SQLModel is difficult to handle, see this post
    on StackOverflow: https://stackoverflow.com/questions/70759112/one-to-one-relationships-with-sqlmodel
    """
    id: str = Field(primary_key=True)
    subject_type: SubjectType

    center_id: Optional[int] = Field(foreign_key="center.id")
    center: Center = Relationship(back_populates="subjects")

    mri_exam_id: Optional[int] = Field(default=None, foreign_key="mriexam.id")
    mri_exam: Optional["MRIExam"] = Relationship(back_populates="subject")


class MRIExam(SQLModel, table=True):
    """
    Model for the MRI Exams table.

    An MRI exam was taken by a unique subject and contains several MRI volumes.

    Attributes:
    - id (int): primary key
    - subject (Subject): subject who took the MRI (one-to-one relationship)
    - volumes (List["MRIVolume"]): list of all the volumes concerning this MRI

    N.B. the one-to-one relationship with SQLModel is difficult to handle, see this post
    on StackOverflow: https://stackoverflow.com/questions/70759112/one-to-one-relationships-with-sqlmodel
    """
    id: Optional[int] = Field(primary_key=True)
    subject: Subject = Relationship(
        sa_relationship_kwargs={'uselist': False},
        back_populates="mri_exam"
    )
    volumes: List["MRIVolume"] = Relationship(back_populates="exam")


class MRIVolume(SQLModel, table=True):
    """
    Model for the MRI volumes table.

    An MRI exam consists of several sequences (T1, T2, FLAIR, FA, MD, etc.), and then we
    can compute volumes from that (atlases, masks, etc.). All these are called "volumes",
    they are stored into one Nifti file (".nii.gz" extension)

    Attributes:
    - id (int): primary key
    - name (str): name of the volume (T1, T2, FLAIR, FA, MD, atlas, name_of_the_mask, etc.)
    - filepath (str): path to the Nifti file
    - exam_id (Optionnal[int]): id of the MRIExam instance
    - exam (MRIExam): relationship to the MRIExam model (one-to-many relationship)
    """
    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=30)
    filepath: str = Field(max_length=300)

    exam_id: Optional[int] = Field(foreign_key="mriexam.id")
    exam: MRIExam = Relationship(back_populates="volumes")
