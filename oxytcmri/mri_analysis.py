from typing import List
import csv

import numpy as np

from oxytcmri.controllers import DatabaseController
from oxytcmri.models import MDLesionVolume, BrainRegionLocalizer, Subject, SubjectType, WholeBrainLocalizer


def compute_mean_diffusivity_lesions_volume(subject: Subject,
                                            quantiles: str = "7_94",
                                            lesion_type: str = "low",
                                            localizer: BrainRegionLocalizer = None) -> float:
    """Compute the volume of the MD lesions for a given subject.

    This method works only with a patient of type "patient" or "test_patient".
    It will look for the MRIVolume with name "Pixyl_Staple_7_94" or "Pixyl_Staple_5_95", depending on the desired
    quantiles. Then, the volume of the low or high MD lesions will be computed by summing:
    - all the voxels with value 1 (high MD lesions),
    - all the voxels with value 2 (low MD lesions).

    Parameters
    ----------
    subject : Subject
        The subject for which to compute the volume of the MD lesions.
    quantiles : str
        Should be "7_94" or "10_95", which means that we take the 7% and 94% quantiles or the 10% and 95% quantiles.
    lesion_type : str
        Should be "low" or "high", which means that we take the low or high MD lesions.
    localizer: BrainRegionLocalizer
        The localizer to use to get the localisation of the MD lesions.

    Returns
    -------
    float
        The volume of the MD lesions.

    Raises
    ------
    ValueError
        If `quantiles` or `lesion_type` have invalid values.
    """
    if quantiles not in ["7_94", "10_95"]:
        raise ValueError("quantiles should be '7_94' or '10_95'")

    if subject.subject_type == SubjectType.healthy_volunteer:
        raise ValueError("This method can only be used with a patient of type 'patient' or 'test_patient'")

    # Get the MRIVolume corresponding to the MD lesions
    mri_volume = subject.get_mri_volume(volume_name=f"Pixyl_Staple_{quantiles}")

    # Get the numpy array corresponding to the MD lesions
    mri_volume_array = mri_volume.as_numpy_array()

    # Get the mask corresponding to the brain region
    region_mask = localizer.get_mask(subject)

    # Get the volume of a voxel
    voxel_volume = mri_volume.voxel_volume()

    # Compute the volume of the MD lesions
    if lesion_type == "high":
        return (np.rint(mri_volume_array[region_mask]) == 1).sum() * voxel_volume
    elif lesion_type == "low":
        return (np.rint(mri_volume_array[region_mask]) == 2).sum() * voxel_volume
    else:
        raise ValueError("lesion_type should be 'low' or 'high'")


class BrainRegionLocalizerFactory:
    @staticmethod
    def from_csv(region_name: str, atlas_number: int, csv_file_path: str) -> BrainRegionLocalizer:
        labels_list = []
        with open(csv_file_path, 'r') as file:
            reader = csv.reader(file)
            labels_list = [int(row[0]) for row in reader]
        return BrainRegionLocalizer(region_name, atlas_number, labels_list)


class MRIAnalysis:
    def __init__(self, settings, db_controller: DatabaseController):
        self.db_controller = db_controller
        self.brain_region_localizers = [WholeBrainLocalizer()] + self.get_list_of_localizers(settings)

    def get_list_of_localizers(self, settings) -> List[BrainRegionLocalizer]:
        localizers = []

        # Add the localizers from the settings file for left and right hemisphere
        left_hemisphere_localizer = BrainRegionLocalizerFactory.from_csv(
            region_name="left_hemisphere",
            atlas_number=4,
            csv_file_path=settings.brainlocalizers.LeftHemisphereLocalizerInAtlas4CSVPath)
        localizers.append(left_hemisphere_localizer)

        right_hemisphere_localizer = BrainRegionLocalizerFactory.from_csv(
            region_name="right_hemisphere",
            atlas_number=4,
            csv_file_path=settings.brainlocalizers.RightHemisphereLocalizerInAtlas4CSVPath)
        localizers.append(right_hemisphere_localizer)

        return localizers

    def compute_all_mean_diffusivity_lesions_volumes(self):
        subjects = self.db_controller.get_all_subjects()
        for subject in subjects:
            if subject.subject_type != "Patient":
                continue

            for quantiles in ["7_94", "10_95"]:
                for lesion_type in ["low", "high"]:
                    for localizer in self.brain_region_localizers:
                        try:
                            # Get the volume corresponding to the MD lesions
                            md_lesions_volume_value_in_mL = compute_mean_diffusivity_lesions_volume(subject,
                                                                                                    quantiles,
                                                                                                    lesion_type,
                                                                                                    localizer)
                        except ValueError:
                            md_lesions_volume_value_in_mL = None

                        if md_lesions_volume_value_in_mL is not None:
                            md_lesions_volume = MDLesionVolume(
                                subject_id=subject.id,
                                quantiles=quantiles,
                                lesion_type=lesion_type,
                                volume_value_in_mL=md_lesions_volume_value_in_mL,
                                localisation=localizer.region_name
                            )

                            self.db_controller.add_object(md_lesions_volume)

        self.db_controller.commit_changes()
