# -*- coding: utf-8 -*-
"""Module documenting the data models used in the database:

- **Center**: a center is a hospital or a research center where MRI exams were taken;
- **Subject**: a subject is a person who took an MRI exam; it can be a healthy volunteer, or a patient (test or involved
  in the study);
- **MRIExam**: an MRI exam is an exam taken by a subject (it contains several MRI volumes);
- **MRIVolume**: an MRI volume is a volume of an MRI exam (it can be a T1/T2/FLAIR sequence, or DTI measures such as FA or
  MD, or other derivatives such as atlases).

Example
-------
>>> from oxytcmri.models import Center, Subject, SubjectType, MRIExam, MRIVolume
>>> from sqlalchemy import create_engine
>>> engine = create_engine("sqlite:///:memory:")
>>> from sqlalchemy.orm import sessionmaker
>>> Session = sessionmaker(bind=engine)
>>> session = Session()
>>> center = Center(id=1, name="Paris")
>>> subject = Subject(id="subject_1", subject_type=SubjectType.healthy_volunteer, center=center)
>>> mri_exam = MRIExam(id=1, subject=subject)
>>> mri_exam.volumes = [MRIVolume(id=1, name="T1", filepath="path/to/T1.nii.gz", exam=mri_exam),
...                     MRIVolume(id=2, name="T2", filepath="path/to/T2.nii.gz", exam=mri_exam)]
>>> session.add(center)
>>> session.add(subject)
>>> session.add(mri_exam)
>>> session.commit()
>>> session.query(Center).all()
[Center(id=1, name='Paris')]
>>> session.query(Subject).all()
[Subject(id='subject_1', subject_type=<SubjectType.healthy_volunteer: 'Healthy Control'>, center_id=1)]
>>> session.query(MRIExam).all()
[MRIExam(id=1, subject_id='subject_1')]
>>> session.query(MRIVolume).all()
[MRIVolume(id=1, name='T1', filepath='path/to/T1.nii.gz', exam_id=1),
 MRIVolume(id=2, name='T2', filepath='path/to/T2.nii.gz', exam_id=1)]
"""
import enum
import csv
from dataclasses import dataclass
from typing import List
import numpy as np
from nibabel.filebasedimages import FileBasedImage
from sqlalchemy import String, Enum, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
import nibabel
import subprocess


class Base(DeclarativeBase):
    """Base class for all data models."""
    pass


class Center(Base):
    """Model for the centers table.

    Attributes
    ----------
    id : int
        Unique identifying number for the center (primary key).
    name : str
        Usually the city name, sometimes the name of the hospital is added.
    subjects : List[Subject]
        List of subjects belonging to the center.
    """

    __tablename__ = "center"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    subjects: Mapped[List["Subject"]] = relationship(back_populates="center")

    def __repr__(self) -> str:
        """Returns a string representation of the Center instance."""
        return f"Center(id={self.id}, name={self.name})"


class MRIVolume(Base):
    """Model for the MRI volumes table.

    An MRI exam consists of several sequences (T1, T2, FLAIR, FA, MD, etc.), and then we
    can compute volumes from that (atlases, masks, etc.). All these are called "volumes",
    they are stored into one Nifti file (".nii.gz" extension)

    Attributes
    ----------
    id : int
        Primary key.
    name : str
        Name of the volume (T1, T2, FLAIR, FA, MD, atlas, name_of_the_mask, etc.).
    filepath : str
        Path to the Nifti file.
    exam_id : Optional[int]
        Id of the MRIExam instance.
    exam : MRIExam
        Relationship to the MRIExam model (one-to-many relationship).
    """
    __tablename__ = "mrivolume"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    filepath: Mapped[str] = mapped_column(String(300))

    exam_id: Mapped[int] = mapped_column(ForeignKey("mriexam.id"))
    exam: Mapped["MRIExam"] = relationship(back_populates="volumes")

    def __repr__(self):
        """Return a string representation of the MRIVolume instance."""
        return f"MRIVolume(id={self.id}, " \
               f"name={self.name}, " \
               f"filepath={self.filepath}, " \
               f"exam_id={self.exam_id}"

    def nifti_file(self) -> FileBasedImage:
        """Open the Niftifile with nibabel.

        Returns
        -------
        FileBasedImage
            The Nifti file.
        """
        return nibabel.load(self.filepath)

    def as_numpy_array(self) -> np.ndarray:
        """Convert the Nifti file into a numpy array.

        Returns
        -------
        np.ndarray
            The numpy array.
        """
        return np.array(self.nifti_file().dataobj)

    def voxel_volume(self) -> float:
        """Compute the volume of a voxel (in mL)

        See https://stackoverflow.com/questions/62183303/how-to-compute-the-volume-of-a-single-voxel-of-nifti-medical-image

        Returns
        -------
        float
            The volume of a voxel.
        """
        # get spacing between voxels (in mm)
        sx, sy, sz = self.nifti_file().header.get_zooms()
        return sx * sy * sz / 1000


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
    healthy_volunteer = "Healthy Control"
    patient = "Patient"
    test_patient = "Patient Test"


class Sex(str, enum.Enum):
    """
        Sex will be used in class Subject, as an attribute.
    """
    female = "F"
    male = "M"
    unknown = "nan"


class Subject(Base):
    """
    Model for the subjects table.

    Attributes
    ----------
    id : str
        Unique identifier for the subject (primary key).
    subject_type : SubjectType
        Type of subject ("healthy_volunteer", "patient", "test_patient").
    center_id : Optional[int]
        Id referring to the Center model.
    center : Center
        Relationship to the Center model (one-to-many).
    mri_exam_id : Optional[int]
        Id referring to the ExamMRI model.
    mri_exam : Optional[MRIExam]
        Relationship to the ExamMRI model (one-to-one).
    gose_6_months : Optional[int]
        GOSE score at 6 months.
    gose_12_months : Optional[int]
        GOSE score at 12 months.
    impact_score_mortality : Optional[float]
        Impact score for mortality
    impact_score_neurological_outcome : Optional[float]
        Impact score for neurological outcome
    marshall_score : Optional[int]
        CT-scan Marshall score
    pbto2 : Optional[bool]
        True if the patient has a PbtO2 measurement, False otherwise.
    igs2_score : Optional[int]
        IGS2 score (Index de Gravité Simplifié 2, a score to evaluate the severity of a patient in the ICU.
         (cf. https://www.sfar.org/scores2/igs2/)
    """

    __tablename__ = "subject"

    id: Mapped[str] = mapped_column(primary_key=True)

    subject_type: Mapped[SubjectType] = mapped_column(Enum(SubjectType))

    center_id: Mapped[int] = mapped_column(ForeignKey("center.id"))
    center: Mapped["Center"] = relationship(back_populates="subjects")

    mri_exam: Mapped["MRIExam"] = relationship("MRIExam", uselist=False, back_populates="subject")

    gose_6_months: Mapped[int] = mapped_column(Integer, nullable=True)
    gose_12_months: Mapped[int] = mapped_column(Integer, nullable=True)

    impact_score_mortality: Mapped[float] = mapped_column(Integer, nullable=True)
    impact_score_neurological_outcome: Mapped[float] = mapped_column(Integer, nullable=True)

    marshall_score: Mapped[int] = mapped_column(Integer, nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    sex: Mapped[Sex] = mapped_column(Enum(Sex), nullable=True)

    glasgow_coma_scale: Mapped[int] = mapped_column(Integer, nullable=True)
    pbto2: Mapped[bool] = mapped_column(Boolean, nullable=True)

    igs2_score: Mapped[int] = mapped_column(Integer, nullable=True)

    md_lesion_volumes: Mapped[List["MDLesionVolume"]] = relationship("MDLesionVolume", back_populates="subject")

    def __repr__(self):
        """Return a string representation of the Subject instance."""
        return f"Subject(id={self.id}, " \
               f"subject_type={self.subject_type}, " \
               f"center_id={self.center_id})"

    def get_number_within_center(self) -> int:
        """Get the number of the subject within the center.

        Returns
        -------
        int
            The number of the subject within the center.
        """
        return int(self.id[3:5])

    def get_mri_volume(self, volume_name: str) -> MRIVolume:
        """Get the MRIVolume corresponding to the volume name.

        Parameters
        ----------
        volume_name : str
            The name of the volume.

        Returns
        -------
        MRIVolume
            The MRIVolume.

        Raises
        ------
        ValueError
            If the volume is not found for the subject.
        """
        for volume in self.mri_exam.volumes:
            if volume.name == volume_name:
                return volume

        raise ValueError(f"Volume '{volume_name}' not found for subject '{self.id}'")

    def get_md_lesion_volumes(self, quantiles: str, lesion_type: str, localisation: str) -> float:
        """Get the MD lesion volumes of the subject.

        Parameters
        ----------
        quantiles : str
            Should be "7_94" or "10_95", which means that we take the 7% and 94% quantiles or the 10% and 95% quantiles.
        lesion_type : str
            Should be "low" or "high", which means that we take the low or high MD lesions.

        localisation : str
            Should be "whole_brain", "left_hemisphere" or "right_hemisphere".

        Returns
        -------
        List[MDLesionVolume]
            The MD lesion volumes.
        """
        if self.md_lesion_volumes == []:
            return None

        md_lesion_volume = [md_lesion_volume for md_lesion_volume in self.md_lesion_volumes
                            if md_lesion_volume.quantiles == quantiles
                            and md_lesion_volume.lesion_type == lesion_type
                            and md_lesion_volume.localisation == localisation][0]

        return md_lesion_volume.volume_value_in_mL

    def view_mri(self, volume_name: str, segmentation_name: str = None, overlay_name: str = None):
        """Open the MRI of the subject in a viewer (ITK-snap).

        Parameters
        ----------
        volume_name : str
            The name of the volume.
        segmentation_name : str
            The name of the segmentation.
        overlay_name : str
            The name of the overlay.
        """
        volume = self.get_mri_volume(volume_name)
        arguments_list = ["itksnap", "-g", volume.filepath]
        if segmentation_name is not None:
            segmentation = self.get_mri_volume(segmentation_name)
            arguments_list.extend(["-s", segmentation.filepath])
        if overlay_name is not None:
            overlay = self.get_mri_volume(overlay_name)
            arguments_list.extend(["-o", overlay.filepath])
        subprocess.run(arguments_list)

    def view_md_map(self):
        """Open the MD map of the subject in a viewer (ITK-snap)."""
        self.view_mri("MD_map", "Pixyl_Staple_10_95", "T1")

    def update_gose(self, delay_in_month: int, gose_score: int):
        """Update the GOSE score of the subject.

        Parameters
        ----------
        delay_in_month : int
            The delay in months (6 or 12).
        gose_score : int
            The GOSE score.
        """
        if delay_in_month == 6:
            self.gose_6_months = gose_score
        elif delay_in_month == 12:
            self.gose_12_months = gose_score
        else:
            raise ValueError("delay_in_month should be 6 or 12")


@dataclass
class BrainRegionLocalizer:
    """Class to localize the MD lesions in the brain.

    This class is used to localize the MD lesions in the brain.
    The localizer is specific to a brain region, and it will return a mask of the brain region.

    Attributes
    ----------
    region_name : str
        Name of the brain region.
    atlas_number : int
        Number of the atlas.
    labels_list : List[int]
        List of labels corresponding to the brain region.

    Methods
    -------
    get_mask()
        Return the mask of the brain region.
    """
    region_name: str
    atlas_number: int
    labels_list: List[int]

    def get_mask(self, subject: Subject) -> np.ndarray:
        """Return the mask of the brain region's maks for a given subject."""

        # load atlas as numpy array
        atlas_array = subject.get_mri_volume(f"Atlas{self.atlas_number}").as_numpy_array()

        # initialize mask
        mask = atlas_array * 0

        # apply labels to mask
        for label in self.labels_list:
            mask[atlas_array == label] = 1

        return mask == 1


class WholeBrainLocalizer(BrainRegionLocalizer):
    """Class to localize the MD lesions in the whole brain.

    This class is used to localize the MD lesions in the whole brain.
    The localizer will return a mask of the whole brain.

    Methods
    -------
    get_mask()
        Return the mask of the whole brain.
    """
    def __init__(self):
        """Initialize the WholeBrainLocalizer."""
        super().__init__(region_name="whole_brain", atlas_number=4, labels_list=None)

    def get_mask(self, subject: Subject) -> np.ndarray:
        """Return the mask of the whole brain for a given subject."""
        return np.ones(subject.get_mri_volume(f"Atlas{self.atlas_number}").as_numpy_array().shape, dtype=int) == 1


class MRIExam(Base):
    """
    Model for the MRI Exams table.

    An MRI exam was taken by a unique subject and contains several MRI volumes.

    Attributes
    ----------
    id : int
        Primary key.
    subject : Subject
        Subject who took the MRI (one-to-one relationship).
    volumes : List[MRIVolume]
        List of all the volumes concerning this MRI.
    """
    __tablename__ = "mriexam"

    id: Mapped[int] = mapped_column(primary_key=True)

    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
    subject: Mapped["Subject"] = relationship(back_populates="mri_exam")

    volumes: Mapped[List["MRIVolume"]] = relationship(back_populates="exam")

    def __repr__(self):
        """Return a string representation of the MRIExam instance."""
        return f"MRIExam(id={self.id}, subject.id={self.subject.id})"


def get_center_id_from_subject_id(subject_id: str) -> int:
    """Get the center id from a subject id.

    In our database, the subject id starts with the center id. As an example,
    the subject "08_001" is from the center "08".

    Parameters
    ----------
    subject_id : str
        The subject id.

    Returns
    -------
    int
        The center id.
    """
    try:
        return int(subject_id[:2])
    except ValueError:
        raise ValueError(f"Invalid center id in subject id: '{subject_id}'. "
                         f"The subject id should start with the center id.")


class Quantiles(str, enum.Enum):
    seven_ninetyfour = "7_94"
    ten_ninetyfive = "10_95"


class LesionType(str, enum.Enum):
    high = "high"
    low = "low"


class MDLesionVolume(Base):
    __tablename__ = 'md_lesion_volume'

    id: Mapped[int] = mapped_column(primary_key=True)

    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
    subject: Mapped["Subject"] = relationship("Subject", back_populates="md_lesion_volumes")

    volume_value_in_mL: Mapped[float] = mapped_column(Integer, nullable=True)

    quantiles: Mapped[Quantiles] = mapped_column(Enum(Quantiles), nullable=False)
    lesion_type: Mapped[LesionType] = mapped_column(Enum(LesionType), nullable=False)
    localisation: Mapped[str] = mapped_column(String(50), nullable=True)

    def __repr__(self):
        """Return a string representation of the MDLesionVolume instance."""
        return f"MDLesionVolume(id={self.id}, " \
               f"subject_id={self.subject_id}, " \
               f"volume_value_in_mL={self.volume_value_in_mL}, " \
               f"quantiles={self.quantiles}, " \
               f"lesion_type={self.lesion_type}," \
               f"localisation={self.localisation})"
