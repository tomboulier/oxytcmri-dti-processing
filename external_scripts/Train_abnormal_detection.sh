pmin=$1
pmax=$2
#LFD_DISTANCE_THRESHOLD=2
#PCSF_THRESHOLD=0.05


CODE=Train

atlas2_cmd=""
atlas3_cmd=""
atlas4_cmd=""
atlas5_cmd=""
atlas6_cmd=""
atlas7_cmd=""

# 1st pass - generate training mask based on parameters here

for f in $(ls); do

if [[ -d $f ]]; then
# $f is a directory

echo "$f"
#PCSF=${f}/tmp/S002v_PCSF_TX_MD_2.nii.gz
#LFD=${f}/tmp/S002v_LFD_TX_MD_2.nii.gz
#T1_SEG=${f}/tmp/S002v_T1SEG_TX_MD_2.nii.gz
#SUPRATENTORIAL_MASK=${f}/tmp/S002v_SupratentorialMask.nii.gz
#=====
# new:
# ====
#T1_PARENCHYMA_MASK=${f}/${CODE}_T1ParenchymaMask.nii.gz
#c3d ${T1_SEG} -threshold 3 4 1 0 -o ${T1_PARENCHYMA_MASK} # this is conservative; add class 5 for full parenchyma

#PCSF_MASK=${f}/${CODE}_PCSFMask.nii.gz
#c3d ${PCSF} -threshold ${PCSF_THRESHOLD} inf 1 0 -o ${PCSF_MASK}

#LFD_MASK=${f}/${CODE}_LFDMask.nii.gz
#c3d ${LFD} -threshold ${LFD_DISTANCE_THRESHOLD} inf 1 0 -o ${LFD_MASK}

#TRAINING_MASK=${f}/${CODE}_Mask.nii.gz
#c3d ${SUPRATENTORIAL_MASK} ${T1_PARENCHYMA_MASK} -multiply -o ${TRAINING_MASK}
#c3d ${LFD_MASK} ${TRAINING_MASK} -multiply -o ${TRAINING_MASK}
#c3d ${TRAINING_MASK} ${PCSF_MASK} -threshold 0 0 1 0 -multiply -o ${TRAINING_MASK}

#ATLAS_2=${f}/tmp/S002v_Atlas2_2.nii.gz
#ATLAS_3=${f}/tmp/S002v_Atlas3_2.nii.gz
#ATLAS_4=${f}/tmp/S002v_Atlas4_2.nii.gz
#ATLAS_5=${f}/tmp/S002v_Atlas5_2.nii.gz
#ATLAS_6=${f}/tmp/S002v_Atlas6_2.nii.gz
#ATLAS_7=${f}/tmp/S002v_Atlas7_2.nii.gz

TRAIN_ATLAS_2=${f}/${CODE}_Atlas2.nii.gz
TRAIN_ATLAS_3=${f}/${CODE}_Atlas3.nii.gz
TRAIN_ATLAS_4=${f}/${CODE}_Atlas4.nii.gz
TRAIN_ATLAS_5=${f}/${CODE}_Atlas5.nii.gz
TRAIN_ATLAS_6=${f}/${CODE}_Atlas6.nii.gz
TRAIN_ATLAS_7=${f}/${CODE}_Atlas7.nii.gz

#c3d ${ATLAS_2} ${TRAINING_MASK} -multiply -o ${TRAIN_ATLAS_2}
#c3d ${ATLAS_3} ${TRAINING_MASK} -multiply -o ${TRAIN_ATLAS_3}
#c3d ${ATLAS_4} ${TRAINING_MASK} -multiply -o ${TRAIN_ATLAS_4}
#c3d ${ATLAS_5} ${TRAINING_MASK} -multiply -o ${TRAIN_ATLAS_5}
#c3d ${ATLAS_6} ${TRAINING_MASK} -multiply -o ${TRAIN_ATLAS_6}
#c3d ${ATLAS_7} ${TRAINING_MASK} -multiply -o ${TRAIN_ATLAS_7}

MD_FILENAME=${f}/MD_map.nii.gz

atlas2_cmd="${atlas2_cmd} --i ${MD_FILENAME} --a ${TRAIN_ATLAS_2}"
atlas3_cmd="${atlas3_cmd} --i ${MD_FILENAME} --a ${TRAIN_ATLAS_3}"
atlas4_cmd="${atlas4_cmd} --i ${MD_FILENAME} --a ${TRAIN_ATLAS_4}"
atlas5_cmd="${atlas5_cmd} --i ${MD_FILENAME} --a ${TRAIN_ATLAS_5}"
atlas6_cmd="${atlas6_cmd} --i ${MD_FILENAME} --a ${TRAIN_ATLAS_6}"
atlas7_cmd="${atlas7_cmd} --i ${MD_FILENAME} --a ${TRAIN_ATLAS_7}"

fi

done


echo ${atlas2_cmd}
echo ${atlas3_cmd}
echo ${atlas4_cmd}
echo ${atlas5_cmd}
echo ${atlas6_cmd}
echo ${atlas7_cmd}

oxytc_train.py -ocsv roi_atlas2_vox2-5_"${pmin/./-}"_"${pmax/./-}".csv -opkl roi_atlas2_"${pmin/./-}"_"${pmax/./-}".pkl ${atlas2_cmd} -pmin $pmin -pmax $pmax
oxytc_train.py -ocsv roi_atlas3_vox2-5_"${pmin/./-}"_"${pmax/./-}".csv -opkl roi_atlas3_"${pmin/./-}"_"${pmax/./-}".pkl ${atlas3_cmd} -pmin $pmin -pmax $pmax
oxytc_train.py -ocsv roi_atlas4_vox2-5_"${pmin/./-}"_"${pmax/./-}".csv -opkl roi_atlas4_"${pmin/./-}"_"${pmax/./-}".pkl ${atlas4_cmd} -pmin $pmin -pmax $pmax
oxytc_train.py -ocsv roi_atlas5_vox2-5_"${pmin/./-}"_"${pmax/./-}".csv -opkl roi_atlas5_"${pmin/./-}"_"${pmax/./-}".pkl ${atlas5_cmd} -pmin $pmin -pmax $pmax
oxytc_train.py -ocsv roi_atlas6_vox2-5_"${pmin/./-}"_"${pmax/./-}".csv -opkl roi_atlas6_"${pmin/./-}"_"${pmax/./-}".pkl ${atlas6_cmd} -pmin $pmin -pmax $pmax
oxytc_train.py -ocsv roi_atlas7_vox2-5_"${pmin/./-}"_"${pmax/./-}".csv -opkl roi_atlas7_"${pmin/./-}"_"${pmax/./-}".pkl ${atlas7_cmd} -pmin $pmin -pmax $pmax

done
