import enum
from typing import List
import numpy as np
from nibabel.filebasedimages import FileBasedImage
from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
import nibabel


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

    def nifti_file(self) -> FileBasedImage:
        """Open the Niftifile with nibabel

        :return: the Nifti file
        :rtype: FileBasedImage
        """
        return nibabel.load(self.filepath)

    def as_numpy_array(self) -> np.ndarray:
        """Convert the Nifti file into a numpy array

        :return: the numpy array
        :rtype: np.ndarray
        """
        return np.array(self.nifti_file().dataobj)

    def voxel_volume(self) -> float:
        """Compute the volume of a voxel (in mL)

        See https://stackoverflow.com/questions/62183303/how-to-compute-the-volume-of-a-single-voxel-of-nifti-medical-image

        :return: the volume of a voxel
        :rtype: float
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

    def get_volumes(self) -> List[MRIVolume]:
        """Get all the volumes of a subject type.

        :return: the list of volumes
        :rtype: List[MRIVolume]
        """
        return self.mri_exam.volumes

    def compute_mean_diffusivity_lesions_volume(self, quantiles="7_94", lesion_type="low") -> float:
        """Compute the volume of the MD lesions of the subject.

        This method works only with a patient of type "patient" or "test_patient".
        It will look for the MRIVolume with name "Pixyl_Staple_7_94" or "Pixyl_Staple_5_95", depending on the desired
        quantiles. Then, the volume of the low or high MD lesions will be computed by summing:
        - all the voxels with value 1 (low MD lesions),
        - all the voxels with value 2 (high MD lesions).

        :param quantiles: should be "7_94" or "5_95", which means that we take the 7% and 94% quantiles or the 5% and 95% quantiles
        :param lesion_type: should be "low" or "high", which means that we take the low or high MD lesions
        :return: the volume of the MD lesions
        :rtype: float
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

        :param volume_name: the name of the volume
        :return: the MRIVolume
        :rtype: MRIVolume
        """
        for volume in self.mri_exam.volumes:
            if volume.name == volume_name:
                return volume

        raise ValueError(f"Volume '{volume_name}' not found for subject '{self.id}'")


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
