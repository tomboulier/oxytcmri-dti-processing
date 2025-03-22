import argparse
import pickle

import nibabel as nib
import numpy as np


def parseargs():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate abnormal detection metrics."
    )
    parser.add_argument("-i", help="Input image file", required=True, type=str)
    parser.add_argument("-a", help="Atlas file", required=True, type=str)
    parser.add_argument("-o", help="Output image file", required=True, type=str)
    parser.add_argument(
        "-p", help="Pickle file with parameters", required=True, type=str
    )
    parser.add_argument(
        "-m",
        help="Mode: percentile, mean or iqr",
        required=False,
        default="mean",
        type=str,
    )
    parser.add_argument(
        "-devcyto",
        help="Number of deviations for cytogenic lesions",
        required=False,
        default=2,
        type=float,
    )
    parser.add_argument(
        "-devvaso",
        help="Number of deviations for vasogenic lesions",
        required=False,
        default=2,
        type=float,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parseargs()
    print(args)

    # Load parameters from pickle file
    parameters = pickle.load(open(args.p, "rb"))

    # Load input image and atlas
    input_image = nib.load(args.i)
    input_data = input_image.get_fdata()
    atlas_data = nib.load(args.a).get_fdata().astype(int)

    # Initialize output image
    output_data = np.zeros(input_data.shape)

    # Process each label in the atlas
    for label in np.unique(atlas_data):
        if label > 0 and label in parameters:
            # Calculate high threshold
            if args.m == "mean":
                high_threshold = (
                    parameters[label]["mean"] + parameters[label]["std"] * args.devvaso
                )
            elif args.m == "percentile":
                high_threshold = parameters[label]["pmax"]
            elif args.m == "iqr":
                high_threshold = parameters[label]["75"] + (
                    parameters[label]["iqr"] * args.devvaso
                )

            # Identify voxels above the high threshold
            high_mask = np.logical_and(atlas_data == label, input_data > high_threshold)
            output_data[high_mask] = 1

            # Calculate low threshold
            if args.m == "mean":
                low_threshold = (
                    parameters[label]["mean"] - parameters[label]["std"] * args.devcyto
                )
            elif args.m == "percentile":
                low_threshold = parameters[label]["pmin"]
            elif args.m == "iqr":
                low_threshold = parameters[label]["25"] - (
                    parameters[label]["iqr"] * args.devcyto
                )

            # Identify voxels below the low threshold
            low_mask = np.logical_and(atlas_data == label, input_data < low_threshold)
            output_data[low_mask] = 2

    # Save the output image
    output_image = nib.Nifti1Image(
        output_data, affine=input_image.affine, header=input_image.header
    )
    nib.save(output_image, args.o)
