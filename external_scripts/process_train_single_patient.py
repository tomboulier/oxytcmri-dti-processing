import os
import subprocess
from pathlib import Path

from external_scripts.oxytc_train import compute_normal_values


def process_single_patient(patient_dir):
    """
    Process imaging data for a single patient.

    Parameters
    ----------
    patient_dir : str
        Path to the patient's directory containing imaging files (MD maps and atlas files).

    Returns
    -------
    None
        Prints the result of the process or any errors encountered.
    """
    # Required files in the patient directory
    required_files = [
        "MD_map.nii.gz",
        "Atlas2.nii.gz",
        "Atlas3.nii.gz",
        "Atlas4.nii.gz",
        "Atlas5.nii.gz",
        "Atlas6.nii.gz"
    ]

    # Check for missing files
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(patient_dir, f))]
    if missing_files:
        print(f"Missing files for {patient_dir}: {missing_files}")
        return

    # Define the input and output files
    image_files = [str(Path(patient_dir) / "MD_map.nii.gz")]
    atlas_files = [str(Path(patient_dir) / f"Atlas{i}.nii.gz") for i in range(2, 7)]
    output_csv = str(Path(patient_dir) / "MD_results.csv")
    output_pkl = str(Path(patient_dir) / "MD_results.pkl")

    compute_normal_values(image_files, atlas_files, output_csv, output_pkl, pmin=0.1, pmax=0.9)


if __name__ == "__main__":
    """
    Entry point for testing the processing of a single patient.
    """
    # Define the patient directory to test
    base_dir = Path(__file__).resolve().parent.parent / 'data/input/MRI/DTI/Healthy'
    patient_dir = base_dir / "C01/01_03v_mr_19062015"

    # Check if the specified patient directory exists
    if not os.path.exists(patient_dir):
        raise FileNotFoundError(f"the specified directory does not exist ({patient_dir})")
    else:
        # Process the patient directory
        process_single_patient(patient_dir)
