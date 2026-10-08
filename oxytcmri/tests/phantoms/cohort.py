"""
Generation of a complete multi-centre phantom cohort on disk.

The output reproduces the folder layout expected by the pipeline
(``NiftiFoldersMRIExamRepository`` and the CSV importers), plus the lesion
ground truth needed to evaluate the segmentation:

.. code-block:: text

    <output_dir>/
    ├── centers_list.csv              # id,name
    ├── atlases_list.csv              # id,name,label1,label2,...  (no header)
    ├── settings.toml                 # ready-to-use settings for the CLI
    ├── ground_truth.csv              # expected lesion volumes per exam and type
    ├── ground_truth/
    │   └── <exam_id>_MD_lesions.nii.gz   # 0 normal, 1 high MD, 2 low MD
    └── nifti/
        └── <exam_id>/
            ├── MD_map.nii.gz
            ├── Atlas1.nii.gz
            └── Atlas2.nii.gz
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, cast

import nibabel as nib
import numpy as np

from oxytcmri.domain.entities.subject import SubjectType
from oxytcmri.tests.phantoms.anatomy import (
    DEFAULT_PARCELLATIONS,
    Parcellation,
    ParcellationBuilder,
    PhantomGeometry,
    TissueModel,
    build_tissue_model,
)
from oxytcmri.tests.phantoms.diffusivity import AcquisitionNoise, synthesize_md_map
from oxytcmri.tests.phantoms.lesions import (
    Lesion,
    LesionKind,
    apply_lesions,
    lesion_volume_ml,
    sample_lesions,
)

SUBJECT_TYPE_LETTERS: Dict[SubjectType, str] = {
    SubjectType.HEALTHY_VOLUNTEER: "v",
    SubjectType.PATIENT: "p",
    SubjectType.TEST_PATIENT: "t",
}
# Subject numbers 69-99 do not exist in the Oxy-TC trial: the phantom cohort only uses those.
FIRST_HEALTHY_SUBJECT_NUMBER = 71
FIRST_PATIENT_SUBJECT_NUMBER = 81


@dataclass(frozen=True)
class CohortSpec:
    """
    Description of the cohort to generate.

    Parameters
    ----------
    centers : Dict[int, str]
        Centre identifiers and names.
    healthy_per_center : int
        Number of healthy volunteers per centre (3 in Mistral et al.).
    patients_per_center : int
        Number of patients (with lesions) per centre.
    center_scales : Dict[int, float]
        Scanner-dependent multiplicative MD factor per centre (1.0 if omitted).
    geometry : PhantomGeometry
        Voxel grid.
    noise : AcquisitionNoise
        Variability parameters of healthy maps.
    parcellations : Dict[int, ParcellationBuilder]
        Atlas builders keyed by atlas identifier.
    seed : int
        Seed of the random generator; the same seed always yields the same cohort.
    """

    centers: Dict[int, str] = field(default_factory=lambda: {1: "Centre A", 2: "Centre B"})
    healthy_per_center: int = 3
    patients_per_center: int = 1
    center_scales: Dict[int, float] = field(default_factory=lambda: {1: 1.00, 2: 1.05})
    geometry: PhantomGeometry = PhantomGeometry()
    noise: AcquisitionNoise = AcquisitionNoise()
    parcellations: Dict[int, ParcellationBuilder] = field(default_factory=lambda: dict(DEFAULT_PARCELLATIONS))
    seed: int = 2024


@dataclass
class PhantomExam:
    """
    One generated exam.

    Attributes
    ----------
    exam_id : str
        Exam identifier in the trial format (e.g. ``01_71v_mr_010124``).
    center_id : int
        Centre identifier.
    subject_type : SubjectType
        Healthy volunteer or patient.
    folder : Path
        Folder holding the NIfTI files of the exam.
    lesions : List[Lesion]
        Inserted lesions (empty for healthy volunteers).
    ground_truth_path : Optional[Path]
        Ground-truth lesion NIfTI file (patients only).
    lesion_volumes_ml : Dict[LesionKind, float]
        Ground-truth lesion volume per type, in millilitres.
    """

    exam_id: str
    center_id: int
    subject_type: SubjectType
    folder: Path
    lesions: List[Lesion] = field(default_factory=list)
    ground_truth_path: Optional[Path] = None
    lesion_volumes_ml: Dict[LesionKind, float] = field(default_factory=dict)

    @property
    def md_map_path(self) -> Path:
        """Path of the MD map NIfTI file."""
        return self.folder / "MD_map.nii.gz"


@dataclass
class PhantomCohort:
    """
    A generated cohort and the files describing it.

    Attributes
    ----------
    spec : CohortSpec
        The specification used.
    output_dir : Path
        Root output folder.
    model : TissueModel
        Shared anatomy of all exams.
    parcellations : List[Parcellation]
        Atlases written for each exam.
    exams : List[PhantomExam]
        Generated exams.
    """

    spec: CohortSpec
    output_dir: Path
    model: TissueModel
    parcellations: List[Parcellation]
    exams: List[PhantomExam] = field(default_factory=list)

    @property
    def nifti_dir(self) -> Path:
        """Folder containing one sub-folder per exam."""
        return self.output_dir / "nifti"

    @property
    def centers_csv(self) -> Path:
        """CSV file of centres (``id,name``)."""
        return self.output_dir / "centers_list.csv"

    @property
    def atlases_csv(self) -> Path:
        """CSV file of atlases (``id,name,labels...``, no header)."""
        return self.output_dir / "atlases_list.csv"

    @property
    def settings_file(self) -> Path:
        """Settings file usable by the command line interface."""
        return self.output_dir / "settings.toml"

    @property
    def patients(self) -> List[PhantomExam]:
        """Exams of patients, i.e. those carrying lesions."""
        return [exam for exam in self.exams if exam.subject_type == SubjectType.PATIENT]

    def load_ground_truth(self, exam: PhantomExam) -> np.ndarray:
        """Integer ground-truth array of a patient exam (0 normal, 1 high MD, 2 low MD)."""
        if exam.ground_truth_path is None:
            raise ValueError(f"Exam {exam.exam_id} has no ground truth (healthy volunteer).")
        image = cast(nib.Nifti1Image, nib.load(str(exam.ground_truth_path)))
        return np.asarray(image.get_fdata()).astype(np.int16)


def make_exam_id(center_id: int, subject_number: int, subject_type: SubjectType) -> str:
    """
    Build an exam identifier in the format used by the trial (``CC_SSt_mr_DDMMYY``).

    The date is fictitious but deterministic, derived from the subject number.
    """
    letter = SUBJECT_TYPE_LETTERS[subject_type]
    day, month = 1 + subject_number % 28, 1 + subject_number % 12
    return f"{center_id:02d}_{subject_number:02d}{letter}_mr_{day:02d}{month:02d}24"


def save_nifti(array: np.ndarray, affine: np.ndarray, path: Path, dtype: type) -> None:
    """Write an array as a compressed NIfTI file with the given data type."""
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(np.ascontiguousarray(array.astype(dtype)), affine), str(path))


class CohortGenerator:
    """
    Generates a phantom cohort on disk from a specification.

    Parameters
    ----------
    spec : CohortSpec
        What to generate.
    output_dir : Path
        Where to write the files (created if missing).
    """

    def __init__(self, spec: CohortSpec, output_dir: Path):
        self.spec = spec
        self.output_dir = Path(output_dir)
        self.rng = np.random.default_rng(spec.seed)
        self.model = build_tissue_model(spec.geometry)
        self.parcellations = [builder(self.model, atlas_id) for atlas_id, builder in spec.parcellations.items()]

    def generate(self) -> PhantomCohort:
        """Generate every exam and the accompanying CSV, TOML and ground-truth files."""
        cohort = PhantomCohort(spec=self.spec, output_dir=self.output_dir,
                               model=self.model, parcellations=self.parcellations)
        for center_id in self.spec.centers:
            for index in range(self.spec.healthy_per_center):
                cohort.exams.append(self._generate_exam(
                    cohort, center_id, FIRST_HEALTHY_SUBJECT_NUMBER + index, SubjectType.HEALTHY_VOLUNTEER))
            for index in range(self.spec.patients_per_center):
                cohort.exams.append(self._generate_exam(
                    cohort, center_id, FIRST_PATIENT_SUBJECT_NUMBER + index, SubjectType.PATIENT))
        self._write_centers_csv(cohort)
        self._write_atlases_csv(cohort)
        self._write_ground_truth_csv(cohort)
        self._write_settings(cohort)
        return cohort

    def _generate_exam(self, cohort: PhantomCohort, center_id: int,
                       subject_number: int, subject_type: SubjectType) -> PhantomExam:
        exam_id = make_exam_id(center_id, subject_number, subject_type)
        folder = cohort.nifti_dir / exam_id
        exam = PhantomExam(exam_id=exam_id, center_id=center_id, subject_type=subject_type, folder=folder)

        center_scale = self.spec.center_scales.get(center_id, 1.0)
        md_map = synthesize_md_map(self.model, self.rng, center_scale, self.spec.noise)

        if subject_type == SubjectType.PATIENT:
            exam.lesions = sample_lesions(self.model, self.rng)
            md_map, ground_truth = apply_lesions(md_map, exam.lesions, self.model)
            exam.ground_truth_path = cohort.output_dir / "ground_truth" / f"{exam_id}_MD_lesions.nii.gz"
            save_nifti(ground_truth, self.spec.geometry.affine, exam.ground_truth_path, np.int16)
            exam.lesion_volumes_ml = {
                kind: lesion_volume_ml(ground_truth, kind, self.spec.geometry.voxel_volume_ml) for kind in LesionKind
            }

        save_nifti(md_map, self.spec.geometry.affine, exam.md_map_path, np.float32)
        for parcellation in self.parcellations:
            save_nifti(parcellation.labels, self.spec.geometry.affine,
                       folder / f"Atlas{parcellation.atlas_id}.nii.gz", np.int16)
        return exam

    def _write_centers_csv(self, cohort: PhantomCohort) -> None:
        with open(cohort.centers_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["id", "name"])
            for center_id, name in self.spec.centers.items():
                writer.writerow([center_id, name])

    def _write_atlases_csv(self, cohort: PhantomCohort) -> None:
        with open(cohort.atlases_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            for parcellation in self.parcellations:
                writer.writerow([parcellation.atlas_id, parcellation.name, *parcellation.label_values])

    def _write_ground_truth_csv(self, cohort: PhantomCohort) -> None:
        with open(cohort.output_dir / "ground_truth.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["mri_exam_id", "abnormal_value_type", "volume_ml", "number_of_lesions"])
            for exam in cohort.patients:
                for kind, volume in exam.lesion_volumes_ml.items():
                    count = sum(1 for lesion in exam.lesions if lesion.kind == kind)
                    writer.writerow([exam.exam_id, kind.abnormal_value_type.value, f"{volume:.3f}", count])

    def _write_settings(self, cohort: PhantomCohort) -> None:
        database_path = cohort.output_dir / "phantom_database.db"
        cohort.settings_file.write_text(
            "[database]\n"
            f'path = "{database_path}"\n'
            "overwrite_data = true\n\n"
            "[paths]\n"
            f'centers_list = "{cohort.centers_csv}"\n'
            f'atlases_list = "{cohort.atlases_csv}"\n'
            f'nifti_files_folder = "{cohort.nifti_dir}"\n\n'
            "[logs]\n"
            "log_to_console = false\n"
            "save_to_file = false\n",
            encoding="utf-8",
        )


def generate_cohort(spec: Optional[CohortSpec] = None, output_dir: Path = Path("data/phantoms")) -> PhantomCohort:
    """
    Generate a phantom cohort (convenience wrapper around ``CohortGenerator``).

    Parameters
    ----------
    spec : CohortSpec, optional
        What to generate (default specification if omitted).
    output_dir : Path
        Where to write the files.

    Returns
    -------
    PhantomCohort
        Description of the generated files.
    """
    return CohortGenerator(spec or CohortSpec(), output_dir).generate()


def summarize(cohort: PhantomCohort) -> str:
    """One-line-per-exam human-readable summary of a cohort."""
    lines = [f"Brain volume: {cohort.model.brain_volume_ml:.0f} ml, "
             f"voxel {cohort.spec.geometry.voxel_size_mm:g} mm, shape {cohort.spec.geometry.shape}"]
    for exam in cohort.exams:
        description = f"{exam.exam_id}  centre {exam.center_id}  {exam.subject_type.value}"
        if exam.subject_type == SubjectType.PATIENT:
            volumes = ", ".join(f"{kind.name} {volume:.1f} ml" for kind, volume in exam.lesion_volumes_ml.items())
            description += f"  lesions: {len(exam.lesions)} ({volumes})"
        lines.append(description)
    return "\n".join(lines)


def default_parcellations_with(extra: Sequence[int] = ()) -> Dict[int, ParcellationBuilder]:
    """Default atlases, optionally extended with the grid atlas for the given identifiers."""
    from oxytcmri.tests.phantoms.anatomy import grid_parcellation

    builders = dict(DEFAULT_PARCELLATIONS)
    for atlas_id in extra:
        builders[atlas_id] = grid_parcellation
    return builders
