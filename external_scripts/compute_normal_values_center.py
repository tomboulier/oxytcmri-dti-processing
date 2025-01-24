import os
import subprocess
from pathlib import Path

from external_scripts.oxytc_train import compute_normal_values


def get_filepaths(center_dir: str, filename: str) -> list[str]:
    """
    Get the list of image filenames in the center directory.

    In the center directory, the images are stored in the patients folder.

    Parameters
    ----------
    center_dir : str
        Path to the center's directory containing patients folder with imaging files (MD maps and atlas files).

    filename : str
        The filename to search for in the center directory.

    Returns
    -------
    list[str]
        List of image filenames.
    """
    results = []
    for root, dirs, files in os.walk(center_dir):
        for file in files:
            if file == filename:
                results.append(os.path.join(root, file))

    return results


def process_center(center_dir: str, output_dir: str):
    """
    Process imaging data for a single patient.

    Parameters
    ----------
    center_dir : str
        Path to the center's directory containing patients folder with imaging files (MD maps and atlas files).

    output_dir : str
        Path to the output directory where the results will be saved.

    Returns
    -------
    None
        Prints the result of the process or any errors encountered.
    """
    # Define the input and output files
    image_filenames = get_filepaths(center_dir, "MD_map.nii.gz")

    # Process for each atlas
    for atlas_number in range(2, 7):
        atlas_filenames = get_filepaths(center_dir, f"Atlas{atlas_number}.nii.gz")
        csv_filename = str(Path(output_dir) / f"normal_MD_values_atlas{atlas_number}_quantiles_5_95.csv")
        pkl_filename = str(Path(output_dir) / f"normal_MD_values_atlas{atlas_number}_quantiles_5_95.pkl")
        compute_normal_values(image_filenames, atlas_filenames, csv_filename, pkl_filename, pmin=5, pmax=95)


if __name__ == "__main__":
    """
    Entry point for testing the processing on a given center
    """
    # Define the center directory to test
    base_dir = Path(__file__).resolve().parent.parent / 'data/input/MRI/DTI/Healthy'
    center_dir = base_dir / "C01/"

    # Define the outputs directory
    output_dir = Path(__file__).resolve().parent.parent / 'data/output/normal_DTI_metrics_values'

    # Check if the specified patient directory exists
    if not os.path.exists(center_dir):
        raise FileNotFoundError(f"the specified directory does not exist ({center_dir})")
    else:
        # Process the patient directory
        process_center(center_dir, output_dir)
