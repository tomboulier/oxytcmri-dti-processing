import os
import subprocess


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

    # Construct the command to run the training script
    command = [
        "python", "oxytc_train.py",
        "--i", os.path.join(patient_dir, "MD_map.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas2.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas3.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas4.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas5.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas6.nii.gz"),
        "-ocsv", os.path.join(patient_dir, "MD_results.csv"),
        "-opkl", os.path.join(patient_dir, "MD_results.pkl"),
        "-pmin", "5",
        "-pmax", "95"
    ]

    # Print the constructed command for debugging
    print(f"Executing command: {' '.join(command)}")

    # Execute the command using subprocess
    try:
        subprocess.run(command, check=True)
        print(f"Processing completed successfully for {patient_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error during execution for {patient_dir}: {e}")


if __name__ == "__main__":
    """
    Entry point for testing the processing of a single patient.
    """
    # Define the patient directory to test
    patient_dir = "OxyTC_Pixyl_results/Healthy/C01/01_03v_mr_19062015"

    # Check if the specified patient directory exists
    if not os.path.exists(patient_dir):
        print(f"The specified directory does not exist: {patient_dir}")
    else:
        # Process the patient directory
        process_single_patient(patient_dir)
