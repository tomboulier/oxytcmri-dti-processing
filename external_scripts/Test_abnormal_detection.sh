

f=$1

LFD_DISTANCE_THRESHOLD=2
PCSF_THRESHOLD=0.05

CODE=Test
THRESHOLD_MODE=$3
DEVCYTO=$4
DEVVASO=$5
VOLCYTO=$6
VOLVASO=$7

PCSF=${f}/tmp/S002_PCSF_TX_MD.nii.gz
LFD=${f}/tmp/S002_LFD_TX_MD.nii.gz
T1_SEG=${f}/tmp/S002_T1SEG_TX_MD.nii.gz
SUPRATENTORIAL_MASK=${f}/tmp/S002_SupratentorialMask.nii.gz
#=====
# new:
# ====
#T1_PARENCHYMA_MASK=${f}/${CODE}_T1ParenchymaMask.nii.gz
#c3d ${T1_SEG} -threshold 3 4 1 0 -o ${T1_PARENCHYMA_MASK} # this is conservative; add class 5 for full parenchyma

#PCSF_MASK=${f}/${CODE}_PCSFMask.nii.gz
#c3d ${PCSF} -threshold ${PCSF_THRESHOLD} inf 1 0 -o ${PCSF_MASK}

#LFD_MASK=${f}/${CODE}_LFDMask.nii.gz
#c3d ${LFD} -threshold ${LFD_DISTANCE_THRESHOLD} inf 1 0 -o ${LFD_MASK}

#TEST_MASK=${f}/${CODE}_Mask.nii.gz
#c3d ${SUPRATENTORIAL_MASK} ${T1_PARENCHYMA_MASK} -multiply -o ${TEST_MASK}
#c3d ${LFD_MASK} ${TEST_MASK} -multiply -o ${TEST_MASK}
#c3d ${TEST_MASK} ${PCSF_MASK} -threshold 0 0 1 0 -multiply -o ${TEST_MASK}

#ATLAS_2=${f}/tmp/S002_Atlas2.nii.gz
#ATLAS_3=${f}/tmp/S002_Atlas3.nii.gz
#ATLAS_4=${f}/tmp/S002_Atlas4.nii.gz
#ATLAS_5=${f}/tmp/S002_Atlas5.nii.gz
#ATLAS_6=${f}/tmp/S002_Atlas6.nii.gz
#ATLAS_7=${f}/tmp/S002_Atlas7.nii.gz

#TEST_ATLAS_2=${f}/${CODE}_Atlas2.nii.gz
#TEST_ATLAS_3=${f}/${CODE}_Atlas3.nii.gz
#TEST_ATLAS_4=${f}/${CODE}_Atlas4.nii.gz
#TEST_ATLAS_5=${f}/${CODE}_Atlas5.nii.gz
#TEST_ATLAS_6=${f}/${CODE}_Atlas6.nii.gz
#TEST_ATLAS_7=${f}/${CODE}_Atlas7.nii.gz

#c3d ${ATLAS_2} ${TEST_MASK} -multiply -o ${TEST_ATLAS_2}
#c3d ${ATLAS_3} ${TEST_MASK} -multiply -o ${TEST_ATLAS_3}
#c3d ${ATLAS_4} ${TEST_MASK} -multiply -o ${TEST_ATLAS_4}
#c3d ${ATLAS_5} ${TEST_MASK} -multiply -o ${TEST_ATLAS_5}
#c3d ${ATLAS_6} ${TEST_MASK} -multiply -o ${TEST_ATLAS_6}
#c3d ${ATLAS_7} ${TEST_MASK} -multiply -o ${TEST_ATLAS_7}

TEST_ATLAS_2=${f}/tmp/S002_Atlas2.nii.gz
TEST_ATLAS_3=${f}/tmp/S002_Atlas3.nii.gz
TEST_ATLAS_4=${f}/tmp/S002_Atlas4.nii.gz
TEST_ATLAS_5=${f}/tmp/S002_Atlas5.nii.gz
TEST_ATLAS_6=${f}/tmp/S002_Atlas6.nii.gz
TEST_ATLAS_7=${f}/tmp/S002_Atlas7.nii.gz

MD_FILENAME=${f}/MD_map.nii.gz

staple_cmd=""
for i in {2..7}; do

MDSEG_FILENAME=${f}/pixyl_${i}.nii.gz
#rm ${MDSEG_FILENAME}
if [ ! -f ${MDSEG_FILENAME} ]; then
#oxytc_test.py -i ${MD_FILENAME} -a ${f}/${CODE}_Atlas${i}.nii.gz -p roi_atlas${i}.pkl -o ${MDSEG_FILENAME} -m $THRESHOLD_MODE -devcyto $DEVCYTO -devvaso $DEVVASO
oxytc_test.py -i ${MD_FILENAME} -a ${f}/${CODE}_Atlas${i}.nii.gz -p roi_atlas${i}.pkl -o ${MDSEG_FILENAME} -m $THRESHOLD_MODE 
fi
staple_cmd="${staple_cmd} ${MDSEG_FILENAME}"


done


c3d ${staple_cmd} -staple 1 -o ${f}/${CODE}_StapleSegmentation1_v1.nii.gz
c3d ${staple_cmd} -staple 2 -o ${f}/${CODE}_StapleSegmentation2_v1.nii.gz


INV_TEST_MASK=${f}/${CODE}_InvTestMask.nii.gz
c3d ${TEST_MASK} -threshold 0 0 1 0 -o ${INV_TEST_MASK}
RES=${f}/${CODE}_RO.nii.gz

###Remove voxels near csf
##stkRemoveObjects -i ${f}/${CODE}_StapleSegmentation1_v1.nii.gz -am ${INV_TEST_MASK} -v $VOLVASO -d 1 -o ${f}/${CODE}_StapleSegmentation1.nii.gz
##stkRemoveObjects -i ${f}/${CODE}_StapleSegmentation2_v1.nii.gz -am ${INV_TEST_MASK} -v $VOLCYTO -d 1 -o ${f}/${CODE}_StapleSegmentation2.nii.gz

##MDSEG_FILENAME=${f}/${CODE}_Pixyl_Staple.nii.gz
##c3d ${f}/${CODE}_StapleSegmentation1.nii.gz ${f}/${CODE}_StapleSegmentation2.nii.gz -scale 2 -add -o ${MDSEG_FILENAME}


### GT_FILENAME=${f}/gt.nii.gz #ground true.
##GT_CYTO_FILENAME=${f}/gt_cyto.nii.gz
##GT_VASO_FILENAME=${f}/gt_vaso.nii.gz

### c3d ${GT_FILENAME} -threshold 1 1 1 0 -o ${GT_VASO_FILENAME}
### c3d ${GT_FILENAME} -threshold 2 2 1 0 -o ${GT_CYTO_FILENAME}

###ImageValidationISLES ${GT_VASO_FILENAME} ${f}/${CODE}_StapleSegmentation1.nii.gz
###ImageValidationISLES ${GT_CYTO_FILENAME} ${f}/${CODE}_StapleSegmentation2.nii.gz

### senan:
### c3d ${GT_FILENAME} ${MDSEG_FILENAME} -overlap 1 >> "Overlap1.csv"
### c3d ${GT_FILENAME} ${MDSEG_FILENAME} -overlap 2 >> "Overlap2.csv"

###pauline
##c3d ${GT_CYTO_FILENAME} ${f}/${CODE}_StapleSegmentation2.nii.gz -overlap 1 -verbose >> ${CODE}"_Overlap_cyto.csv"
##c3d ${GT_VASO_FILENAME} ${f}/${CODE}_StapleSegmentation1.nii.gz -overlap 1 -verbose >> ${CODE}"_Overlap_vaso.csv"

exit
