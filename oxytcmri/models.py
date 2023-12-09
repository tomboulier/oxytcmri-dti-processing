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
from typing import List
import numpy as np
from nibabel.filebasedimages import FileBasedImage
from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
import nibabel


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
    """

    __tablename__ = "subject"

    id: Mapped[str] = mapped_column(primary_key=True)
    subject_type: Mapped[SubjectType] = mapped_column(Enum(SubjectType))

    center_id: Mapped[int] = mapped_column(ForeignKey("center.id"))
    center: Mapped["Center"] = relationship(back_populates="subjects")

    mri_exam: Mapped["MRIExam"] = relationship("MRIExam", uselist=False, back_populates="subject")

    def __repr__(self):
        """Return a string representation of the Subject instance."""
        return f"Subject(id={self.id}, " \
               f"subject_type={self.subject_type}, " \
               f"center_id={self.center_id})"

    def get_volumes(self) -> List[MRIVolume]:
        """Get all the volumes of a subject type.

        Returns
        -------
        List[MRIVolume]
            The list of volumes.
        """
        return self.mri_exam.volumes

    def get_volume(self, volume_name: str) -> MRIVolume:
        """Get a volume of a subject type.

        Returns
        -------
        MRIVolume
            The volume.
        """
        volumes = self.get_volumes()
        for volume in volumes:
            if volume.name == volume_name:
                return volume

        raise ValueError(f"Volume '{volume_name}' not found for subject '{self.id}'")

    def compute_mean_diffusivity_lesions_volume(self, quantiles="7_94", lesion_type="low") -> float:
        """Compute the volume of the MD lesions of the subject.

        This method works only with a patient of type "patient" or "test_patient".
        It will look for the MRIVolume with name "Pixyl_Staple_7_94" or "Pixyl_Staple_5_95", depending on the desired
        quantiles. Then, the volume of the low or high MD lesions will be computed by summing:
        - all the voxels with value 1 (low MD lesions),
        - all the voxels with value 2 (high MD lesions).

        Parameters
        ----------
        quantiles : str
            Should be "7_94" or "5_95", which means that we take the 7% and 94% quantiles or the 5% and 95% quantiles.
        lesion_type : str
            Should be "low" or "high", which means that we take the low or high MD lesions.

        Returns
        -------
        float
            The volume of the MD lesions.

        Raises
        ------
        ValueError
            If `quantiles` or `lesion_type` have invalid values.
        """
        if quantiles not in ["7_94", "5_95"]:
            raise ValueError("quantiles should be '7_94' or '5_95'")

        if lesion_type not in ["low", "high"]:
            raise ValueError("lesion_type should be 'low' or 'high'")

        if self.subject_type == SubjectType.healthy_volunteer:
            raise ValueError("This method can only be used with a patient of type 'patient' or 'test_patient'")

        # Get the MRIVolume corresponding to the MD lesions
        mri_volume = self.get_mri_volume(volume_name=f"Pixyl_Staple_{quantiles}")

        # Get the numpy array corresponding to the MD lesions
        mri_volume_array = mri_volume.as_numpy_array()

        # Get the volume of a voxel
        volume = mri_volume.voxel_volume()

        # Compute the volume of the MD lesions
        if lesion_type == "low":
            return (np.rint(mri_volume_array) == 1).sum() * volume
        elif lesion_type == "high":
            return (np.rint(mri_volume_array) == 2).sum() * volume
        else:
            raise ValueError("type should be 'low' or 'high'")

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

    def view_md_map(self):
        """Open the MD map of the subject in a viewer (ITK-snap)."""
        md_map = self.get_mri_volume("MD_map")
        md_lesions_segmentation = self.get_mri_volume("Pixyl_Staple_10_95")
        import subprocess
        subprocess.run(["itksnap",
                        "-g", md_map.filepath,
                        "-s", md_lesions_segmentation.filepath])


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
