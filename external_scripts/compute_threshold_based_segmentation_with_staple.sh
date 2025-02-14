#!/bin/bash

# Check if the required number of arguments is provided
if [ "$#" -lt 7 ]; then
echo "Usage: $0 <images_folder> <threshold_mode> <devcyto> <devvaso> <volcyto> <volvaso> <normal_values_folder> <center_number> <dti-metric>"
echo "  <images_folder>        : Path to the folder containing the necessary Nifti files (*.nii.gz)"
echo "  <threshold_mode>       : Mode for thresholding (percentile, mean or iqr)"
echo "  <devcyto>              : Number of deviations for cytogenic lesions"
echo "  <devvaso>              : Number of deviations for vasogenic lesions"
echo "  <normal_values_folder> : Path to the folder containing the normal values"
echo "  <center_number>        : Number of the center"
echo "  <dti-metric>           : DTI metric to be used (FA or MD)"
exit 1
fi

# Input arguments
f=$1
THRESHOLD_MODE=$2
DEVCYTO=$3
DEVVASO=$4
NORMAL_VALUES_FOLDER=$5
CENTER_NUMBER=$6
DTI_METRIC=$7

# Constants
CODE=Test

# Check arguments
if [ "$THRESHOLD_MODE" != "percentile" ] && [ "$THRESHOLD_MODE" != "mean" ] && [ "$THRESHOLD_MODE" != "iqr" ]; then
    echo "Error: Threshold mode must be percentile, mean or iqr"
    exit 1
fi
if [ "$DEVCYTO" -lt 0 ] || [ "$DEVVASO" -lt 0 ]; then
    echo "Error: Deviations must be positive integers"
    exit 1
fi
if [ "$CENTER_NUMBER" -lt 0 ] || [ "$CENTER_NUMBER" -gt 23 ]; then
    echo "Error: Center number must be an integer between 0 and 23"
    exit 1
fi
if [ "$DTI_METRIC" != "FA" ] && [ "$DTI_METRIC" != "MD" ]; then
    echo "Error: DTI metric must be FA or MD"
    exit 1
fi

# File paths
dti_metric_map_filepath=${f}/${DTI_METRIC}_map.nii.gz

# Check if required files exist
if [ ! -f "$dti_metric_map_filepath" ]; then
    echo "Error: File $file not found!"
    exit 1
fi

# Process each atlas
staple_cmd=""
for atlas_number in {2..6}; do
    atlas_filepath=${f}/Atlas${atlas_number}.nii.gz
    threshold_mask_filepath=${f}/${DTI_METRIC}_threshold_Atlas${atlas_number}_${DEVCYTO}_${DEVVASO}.nii.gz
    pickle_filepath=${NORMAL_VALUES_FOLDER}/normal_${DTI_METRIC}_values_center${CENTER_NUMBER}_atlas${atlas_number}_quantiles_${DEVCYTO}_${DEVVASO}.pkl

    for file in "$atlas_filepath" "$pickle_filepath"; do
        if [ ! -f "$file" ]; then
            echo "Error: File $file not found!"
            exit 1
        fi
    done

    # Compute threshold-based segmentation from atlas with python script
    python compute_threshold_based_segmentation_from_atlas.py -i "$dti_metric_map_filepath" -a "$atlas_filepath" -p "$pickle_filepath" -o "$threshold_mask_filepath" -m "$THRESHOLD_MODE" -devcyto 2 -devvaso 2

    staple_cmd="${staple_cmd} ${threshold_mask_filepath}"
done

# Run STAPLE algorithm
c3d ${staple_cmd} -staple 1 -o ${f}/${CODE}_StapleSegmentation1_v1.nii.gz
c3d ${staple_cmd} -staple 2 -o ${f}/${CODE}_StapleSegmentation2_v1.nii.gz

# Exit script
exit 0
