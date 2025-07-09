from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from logging import getLogger
from typing import Optional, List, cast

from oxytcmri.domain.entities.mri import DTIMetric, MRIExamId, MRIExam, Atlas, RegionOfInterest, AbnormalValueType, \
    DTIAbnormalValues, AbnormalVoxelData, Mask
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.monitoring import EventDispatcher
from oxytcmri.domain.ports.repositories import RepositoriesRegistry, SubjectRepository, MRIExamRepository, \
    AtlasRepository, RegionOfInterestRepository, Repository

logger = getLogger(__name__)

@dataclass
class BrainLesionsVolume:
    """
    Represents the volume of brain lesions for a specific MRI exam, DTI metric,
    and region of interest.

    Attributes
    ----------
    mri_exam_id : MRIExamId
        The ID of the MRI exam.
    dti_metric : DTIMetric
        The DTI metric for which the volume is computed.
    region_of_interest : Optional[RegionOfInterest]
        The region of interest for which the volume is computed.
    abnormal_value_type : AbnormalValueType
        The type of abnormal value (HIGH or LOW) for which the volume is computed.
    value_ml : float
        The computed volume in milliliters (ml) of the brain lesions.
    """
    mri_exam_id: MRIExamId
    dti_metric: DTIMetric
    region_of_interest: Optional[RegionOfInterest]
    abnormal_value_type: AbnormalValueType
    value_ml: float


class BrainLesionsVolumeRepository(Repository[BrainLesionsVolume, None], ABC):
    """
    Abstract base class for Brain Lesions Volume repository.
    Defines the interface for retrieving brain lesions volume data.
    """


class ComputeBrainLesionsVolumes:
    """
    Use-case for computing the volumes of brain lesions in MRI exams.
    """

    def __init__(self,
                 repositories_registry: RepositoriesRegistry,
                 dispatcher: Optional[EventDispatcher] = None):
        """
        Initializes the SegmentDtiAbnormalValues use-case.
        """
        self.subjects_repository: SubjectRepository = repositories_registry.get_repository(Subject)
        self.mri_repository: MRIExamRepository = repositories_registry.get_repository(MRIExam)
        self.atlas_repository: AtlasRepository = repositories_registry.get_repository(Atlas)
        self.roi_repository: RegionOfInterestRepository = repositories_registry.get_repository(RegionOfInterest)
        self.brain_lesions_volume_repository = repositories_registry.get_repository(BrainLesionsVolume)

        self.dispatcher = dispatcher

    def __call__(self,
                 dti_metrics: Optional[List[DTIMetric]] = None,
                 mri_exam_id: Optional[MRIExamId] = None,
                 regions_of_interest: Optional[List[RegionOfInterest]] = None) -> None:
        """
        Runs the use-case.

        Computes brain lesions of all patients in the SubjectRepository, for DTI metrics provided.

        Parameters
        ----------
        dti_metrics : List[DTIMetric], optional
            The DTI metrics to segment. If None, all the DTI metrics will be segmented.
        mri_exam_id : Optional[MRIExamId], optional
            The ID of the MRI exam to segment. If None, all the MRI exams will be segmented.
        regions_of_interest : Optional[List[RegionOfInterest]], optional
            The supplementary regions of interest to consider for the segmentation.
            If None, only the whole brain will be considered.
        """
        dti_metrics = dti_metrics or list(DTIMetric)
        roi_list = regions_of_interest or self.roi_repository.list_all()
        if mri_exam_id:
            mri_exam = self.mri_repository.get_by_id(mri_exam_id)
            self.compute_brain_lesions_associated_to_mri_exam(mri_exam, dti_metrics, roi_list)
        else:
            self.compute_all_brain_lesions(dti_metrics, roi_list)

    def compute_all_brain_lesions(self,
                                  dti_metrics: List[DTIMetric],
                                  regions_of_interest: List[RegionOfInterest]) -> None:
        """
        Computes the brain lesions for all patients in the SubjectRepository.
        """
        patients = self.subjects_repository.list_all_patients()
        for patient in patients:
            # Get the MRI exam for the patient
            mri_exam = self.mri_repository.get_exam_for_subject(patient)
            self.compute_brain_lesions_associated_to_mri_exam(mri_exam, dti_metrics, regions_of_interest)

    def compute_brain_lesions_associated_to_mri_exam(self,
                                                     mri_exam: MRIExam,
                                                     dti_metrics: List[DTIMetric],
                                                     regions_of_interest: List[RegionOfInterest]) -> None:
        """
        Computes the brain lesions associated to a specific MRI exam.

        Parameters
        ----------
        mri_exam : MRIExam
            The MRI exam for which to compute the brain lesions.
        dti_metrics : List[DTIMetric]
            The DTI metrics for which to compute the brain lesions.
        regions_of_interest : List[RegionOfInterest]
            The supplementary regions of interest to consider for the segmentation.
            If None, only the whole brain will be considered.
        """
        logger.info(f"Computing brain lesions for MRI exam {mri_exam.id}")

        # Get the masks for the regions of interest
        all_masks = {}
        for roi in regions_of_interest:
            if roi.name is None:
                raise ValueError("Region of interest must have a name.")
            mask = mri_exam.get_mask(roi)
            all_masks[roi.name] = mask
        all_masks["whole_brain"] = None

        for abnormal_value_type in AbnormalValueType:
            for dti_metric in dti_metrics:
                segmented_dti_map = mri_exam.get_segmented_dti_abnormal_values(dti_metric)
                for region_name, mask in all_masks.items():
                    volume_value = self.compute_volume_value(segmented_dti_map, mask, abnormal_value_type)
                    brain_lesions_volume = BrainLesionsVolume(
                        mri_exam_id=mri_exam.id,
                        dti_metric=dti_metric,
                        region_of_interest=next((roi for roi in regions_of_interest if roi.name == region_name), None),
                        abnormal_value_type=abnormal_value_type,
                        value_ml=volume_value
                    )
                    self.store_brain_lesions_volume(brain_lesions_volume)

    def store_brain_lesions_volume(self, brain_lesions_volume: BrainLesionsVolume) -> None:
        """
        Stores the computed brain lesions volume in the repository.

        Parameters
        ----------
        brain_lesions_volume : BrainLesionsVolume
            The brain lesions volume to store.

        Returns
        -------
        None
        """
        self.brain_lesions_volume_repository.save(brain_lesions_volume)

    @staticmethod
    def compute_volume_value(segmented_dti_map: DTIAbnormalValues,
                             region_of_interest_mask: Optional[Mask],
                             abnormal_value_type: AbnormalValueType) -> float:
        """
        Computes the volume of brain lesions for a specific MRI exam, DTI metric, and region of interest.

        Parameters
        ----------
        segmented_dti_map : DTIAbnormalValues
            The segmented DTI abnormal values map for the MRI exam.
        region_of_interest_mask : Optional[Mask]
            The mask defining the region of interest for which to compute the volume.
            If None, no mask is applied (case of the whole brain).
        abnormal_value_type : AbnormalValueType
            The type of abnormal value to compute the volume for (HIGH of LOW).

        Returns
        -------
        float
            The computed volume in milliliters (ml) of the brain lesions.
        """
        abnormal_voxel_data = cast(AbnormalVoxelData, segmented_dti_map.get_voxel_data())
        abnormal_coordinates = abnormal_voxel_data.get_abnormal_voxels_coordinates(abnormal_value_type)

        if region_of_interest_mask is not None:
            # Filter the coordinates by the region of interest
            true_voxels_maks = region_of_interest_mask.get_true_voxel_coordinates()
            abnormal_coordinates = [coord for coord in abnormal_coordinates if coord in true_voxels_maks]

        # Compute the volume
        return len(abnormal_coordinates) * abnormal_voxel_data.get_voxel_volume_in_ml()
