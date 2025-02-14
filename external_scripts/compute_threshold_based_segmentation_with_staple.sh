#!/bin/bash

# Check if the required number of arguments is provided
if [ "$#" -lt 5 ]; then
echo "Usage: $0 <folder> <threshold_mode> <devcyto> <devvaso> <volcyto> <volvaso>"
echo "  <folder>          : Path to the folder containing the necessary files"
echo "  <threshold_mode>  : Mode for thresholding (percentile, mean or iqr)"
echo "  <devcyto>         : Number of deviations for cytogenic lesions"
echo "  <devvaso>         : Number of deviations for vasogenic lesions"
exit 1
fi

# Input arguments
f=$1
THRESHOLD_MODE=$2
DEVCYTO=$3
DEVVASO=$4

# Constants
LFD_DISTANCE_THRESHOLD=2
PCSF_THRESHOLD=0.05
CODE=Test

# File paths
PCSF=${f}/tmp/S002_PCSF_TX_MD.nii.gz
LFD=${f}/tmp/S002_LFD_TX_MD.nii.gz
T1_SEG=${f}/tmp/S002_T1SEG_TX_MD.nii.gz
SUPRATENTORIAL_MASK=${f}/tmp/S002_SupratentorialMask.nii.gz
MD_FILENAME=${f}/MD_map.nii.gz

# Check if required files exist
for file in "$PCSF" "$LFD" "$T1_SEG" "$SUPRATENTORIAL_MASK" "$MD_FILENAME"; do
    if [ ! -f "$file" ]; then
        echo "Error: File $file not found!"
        exit 1
    fi
done

# Process each atlas
staple_cmd=""
for i in {2..7}; do
    ATLAS=${f}/tmp/S002_Atlas${i}.nii.gz
    MDSEG_FILENAME=${f}/pixyl_${i}.nii.gz

    if [ ! -f "$ATLAS" ]; then
        echo "Error: Atlas file $ATLAS not found!"
        exit 1
    fi

    if [ ! -f "$MDSEG_FILENAME" ]; then
        python compute_threshold_based_segmentation_from_atlas.py -i "$MD_FILENAME" -a "$ATLAS" -p "roi_atlas${i}.pkl" -o "$MDSEG_FILENAME" -m "$THRESHOLD_MODE" -devcyto "$DEVCYTO" -devvaso "$DEVVASO"
    fi

    staple_cmd="${staple_cmd} ${MDSEG_FILENAME}"
done

# Run STAPLE algorithm
c3d ${staple_cmd} -staple 1 -o ${f}/${CODE}_StapleSegmentation1_v1.nii.gz
c3d ${staple_cmd} -staple 2 -o ${f}/${CODE}_StapleSegmentation2_v1.nii.gz

# Invert test mask
INV_TEST_MASK=${f}/${CODE}_InvTestMask.nii.gz
c3d ${SUPRATENTORIAL_MASK} -threshold 0 0 1 0 -o ${INV_TEST_MASK}

# Final result
RES=${f}/${CODE}_RO.nii.gz

# Exit script
exit 0
