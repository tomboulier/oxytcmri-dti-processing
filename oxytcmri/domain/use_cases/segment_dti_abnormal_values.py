"""
This module segments the abnormal values in DTI images using the normative values computed in each center from healthy subjects.
"""
from enum import Enum
from typing import Optional, List

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import MRIExam, Atlas, DTIMetric, DTIMap, MRIData
from oxytcmri.domain.entities.subject import Subject
from oxytcmri.domain.ports.monitoring import EventDispatcher
from oxytcmri.domain.ports.repositories import (
    SubjectRepository, MRIExamRepository, AtlasRepository, CenterRepository, RepositoriesRegistry)
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValueRepository, NormativeValue


class AbnormalValueType(Enum):
    """
    Enum for the type of abnormal values.
    """
    HIGH = "high"
    LOW = "low"


class DTIAbnormalValues(MRIData[AbnormalValueType]):
    """
    Class to store the abnormal values in DTI images.
    """

    def __init__(self):
        """
        Initializes the DTIAbnormalValues object.
        """
        super().__init__()
        self._abnormal_values = {}

    def __getitem__(self, item: str) -> AbnormalValueType:
        return self._abnormal_values[item]

    def __setitem__(self, item: str, value: AbnormalValueType) -> None:
        self._abnormal_values[item] = value


class SegmentDTIAbnormalValues:
    """
    Segment abnormal values in DTI images compared to normative values (computed in each center from healthy subjects).
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
        self.centers_repository: CenterRepository = repositories_registry.get_repository(Center)
        self.normative_values_repository: NormativeValueRepository = (
            repositories_registry.get_repository(NormativeValue))

    def __call__(self,
                 dti_metrics: Optional[List[DTIMetric]] = None) -> None:
        """
        Runs the use-case.

        Segments the DTI images of all patients in the SubjectRepository, for DTI metrics provided.

        Parameters
        ----------
        dti_metrics : List[DTIMetric], optional
            The DTI metrics to segment. If None, all the DTI metrics will be segmented.
        """
        self.segment_all_mri_exams_of_patients(dti_metrics)

    def segment_all_mri_exams_of_patients(self,
                                          dti_metrics: Optional[List[DTIMetric]] = None):
        """
        Segments all the MRI exams of all patients.

        It will look for all the patients in the SubjectRepository and for each patient, it will segment the DTI images.
        This segmentation process will have access to the normative values stored in the NormativeValuesRepository.
        """
        dti_metrics = dti_metrics or list(DTIMetric)
        # Get all the patients
        patients = self.subjects_repository.list_all_patients()
        for patient in patients:
            # Get the MRI exam for the patient
            mri_exam = self.mri_repository.get_exam_for_subject(patient)
            for dti_metric in dti_metrics:
                # Get the DTI map associated with the DTI metric
                try:
                    dti_image = mri_exam.get_dti_map(dti_metric)
                    self.segment_dti_map(dti_image)
                except LookupError:
                    # If the DTI image is not found, skip this metric
                    continue

    def segment_dti_map(self, dti_image: DTIMap) -> MRIData:
        """
        Segments the DTI map, i.e. build a map with values indicating the abnormal values in the input DTI map.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map to segment.
        """
        segmentations = []
        for atlas in self.atlas_repository.list_all():
            segmentations.append(self.segment_dti_map_for_atlas(dti_image, atlas))
        return self.merge_segmentations(segmentations)

    def segment_dti_map_for_atlas(self, dti_image: DTIMap, atlas: Atlas) -> MRIData:
        """
        Segments the DTI map for a given atlas, using the normative values.

        Parameters
        ----------
        dti_image : DTIMap
            The DTI map to segment.
        atlas : Atlas
            The atlas to use for segmentation.

        Returns
        -------
        MRIData
            The list of segmentations for the DTI map.
        """
        results = DTIAbnormalValues()
        for atlas_label in atlas.labels:
            thresholds = self.compute_thresholds(dti_image, atlas, atlas_label)
            self.mark_abdormal_voxels(dti_image, atlas, atlas_label, thresholds, results)
        return results


    def merge_segmentations(self, segmentations: List[MRIData]) -> MRIData:
        """
        Merges the segmentations into a single MRIData object.

        Parameters
        ----------
        segmentations : List[MRIData]
            The list of segmentations to merge.

        Returns
        -------
        MRIData
            The merged segmentation.
        """
        raise NotImplementedError("SegmentDTIAbnormalValues.merge_segmentations")
