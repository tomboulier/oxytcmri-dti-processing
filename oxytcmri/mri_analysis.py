from oxytcmri.models import MDLesionVolume


class MRIAnalysis:
    def __init__(self, db_controller: 'DatabaseController'):
        self.db_controller = db_controller

    def calculate_md_lesions(self):
        subjects = self.db_controller.get_all_subjects()
        for subject in subjects:
            if subject.subject_type != "Patient":
                continue

            for quantiles in ["7_94", "10_95"]:
                for lesion_type in ["low", "high"]:
                    for localisation in ["whole_brain", "left_hemisphere", "right_hemisphere"]:
                        try:
                            # Get the volume corresponding to the MD lesions
                            md_lesions_volume_value_in_mL = subject.compute_mean_diffusivity_lesions_volume(quantiles,
                                                                                                            lesion_type,
                                                                                                            localisation)
                        except ValueError:
                            md_lesions_volume_value_in_mL = None

                        if md_lesions_volume_value_in_mL is not None:
                            md_lesions_volume = MDLesionVolume(
                                subject_id=subject.id,
                                quantiles=quantiles,
                                lesion_type=lesion_type,
                                volume_value_in_mL=md_lesions_volume_value_in_mL,
                                localisation=localisation
                            )

                            self.db_controller.add_object(md_lesions_volume)

        self.db_controller.commit_changes()
