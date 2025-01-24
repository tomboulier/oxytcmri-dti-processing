import csv
import os
import pickle
import subprocess
from pathlib import Path

import nibabel as nib
import numpy as np


def compute_normal_values(image_files, atlas_files, output_csv, output_pkl, pmin=None, pmax=None):
    dataimg = []
    datatls = []
    for im in image_files:
        dataimg.append(nib.load(im).get_fdata())
    for im in atlas_files:
        datatls.append(nib.load(im).get_fdata().astype(int))

    dataimg = np.array(dataimg)
    datatls = np.array(datatls)

    if dataimg.shape != datatls.shape:
        raise ValueError(f"Image and atlas shapes do not match. "
                         f"Image shape: {dataimg.shape}, Atlas: {datatls.shape}. "
                         f"Image file: {image_files}, Atlas file: {atlas_files}")

    labels = np.unique(datatls)
    results = {}
    for label in labels:
        results[label] = {'mean': dataimg[datatls == label].mean(),
                          'std': dataimg[datatls == label].std()}
        if pmin and pmax:
            percentilemin, percentilemax = np.percentile(dataimg[datatls == label], [pmin, pmax])
            results[label]['pmin'] = percentilemin
            results[label]['pmax'] = percentilemax

        quartile_1, quartile_3 = np.percentile(dataimg[datatls == label], [25, 75])
        iqr = quartile_3 - quartile_1
        results[label]['25'] = quartile_1
        results[label]['75'] = quartile_3
        results[label]['iqr'] = iqr

    pickle.dump(results, open(output_pkl, "wb"))
    with open(output_csv, 'w') as f:
        w = csv.writer(f)
        w.writerow(results.keys())
        w.writerow([x['mean'] for x in results.values()])
        w.writerow([x['std'] for x in results.values()])
        w.writerow([x['25'] for x in results.values()])
        w.writerow([x['75'] for x in results.values()])
        w.writerow([x['iqr'] for x in results.values()])
        if pmin and pmax:
            w.writerow([x['pmin'] for x in results.values()])
            w.writerow([x['pmax'] for x in results.values()])


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


def process_center(base_dir: str, center_number: int, output_dir: str):
    """
    Process imaging data for a single patient.

    Parameters
    ----------
    base_dir : str
        Path to the directory containing centers folders. Each center folder
         contains healthy volunteers folder with imaging files (MD maps and atlas files).

    center_number : int
        The center number to process.

    output_dir : str
        Path to the output directory where the results will be saved.

    Returns
    -------
    None
        Prints the result of the process or any errors encountered.
    """
    center_dir = str(Path(base_dir) / f"C{center_number:02d}")

    # Define the input and output files
    image_filenames = get_filepaths(center_dir, "MD_map.nii.gz")

    # Process for each atlas
    for atlas_number in range(2, 7):
        print(f"\tProcessing atlas {atlas_number}...")
        atlas_filenames = get_filepaths(center_dir, f"Atlas{atlas_number}.nii.gz")
        csv_filename = str(
            Path(output_dir) / f"normal_MD_values_center{center_number:02d}_atlas{atlas_number}_quantiles_5_95.csv")
        pkl_filename = str(
            Path(output_dir) / f"normal_MD_values_center{center_number:02d}_atlas{atlas_number}_quantiles_5_95.pkl")
        compute_normal_values(image_filenames, atlas_filenames, csv_filename, pkl_filename, pmin=5, pmax=95)


if __name__ == "__main__":
    """
    Entry point for computing normal values for all centers
    """
    # Define the center directory to test
    base_dir = str(Path(__file__).resolve().parent.parent / 'data/input/MRI/DTI/Healthy')

    # Define the outputs directory
    output_dir = str(Path(__file__).resolve().parent.parent / 'data/output/normal_DTI_metrics_values')

    for center_number in range(1, 23):
        print(f"Processing center {center_number}...")
        process_center(base_dir, center_number=center_number, output_dir=output_dir)
