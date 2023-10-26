from typing import List, Optional
import enum
from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Center(Base):
    """
    Model for the centers table.

    Attributes:
    - id (int): unique identifying number for the center (primary key)
    - name (str): usually the city name, sometimes the name of the hospital is added
    - subjects (List[Subject]): list of subjects belonging to the center
    """

    __tablename__ = "center"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    subjects: Mapped[List["Subject"]] = relationship(back_populates="center")

    def __repr__(self):
        return f"Center(id={self.id}, name={self.name})"


class SubjectType(str, enum.Enum):
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


class Subject(Base):
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

    __tablename__ = "subject"

    id: Mapped[str] = mapped_column(primary_key=True)
    subject_type: Mapped[SubjectType] = mapped_column(Enum(SubjectType))

    center_id: Mapped[int] = mapped_column(ForeignKey("center.id"))
    center: Mapped["Center"] = relationship(back_populates="subjects")

    mri_exam: Mapped["MRIExam"] = relationship("MRIExam", uselist=False, back_populates="subject")

    def __repr__(self):
        return f"Subject(id={self.id}, " \
               f"subject_type={self.subject_type}, " \
               f"center_id={self.center_id})"


class MRIExam(Base):
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
    __tablename__ = "mriexam"

    id: Mapped[int] = mapped_column(primary_key=True)

    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
    subject: Mapped["Subject"] = relationship(back_populates="mri_exam")

    volumes: Mapped[List["MRIVolume"]] = relationship(back_populates="exam")

    def __repr__(self):
        return f"MRIExam(id={self.id}, subject.id={self.subject.id})"


class MRIVolume(Base):
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
    __tablename__ = "mrivolume"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    filepath: Mapped[str] = mapped_column(String(300))

    exam_id: Mapped[int] = mapped_column(ForeignKey("mriexam.id"))
    exam: Mapped["MRIExam"] = relationship(back_populates="volumes")

    def __repr__(self):
        return f"MRIVolume(id={self.id}, " \
               f"name={self.name}, " \
               f"filepath={self.filepath}, " \
               f"exam_id={self.exam_id}"
