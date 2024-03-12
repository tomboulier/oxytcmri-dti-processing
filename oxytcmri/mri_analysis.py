class MRIAnalysis:
    def __init__(self, subjects):
        self.subjects = subjects
    @staticmethod
    def calculate_md_lesions(subject, quantiles, lesion_type):
        try:
            # Get the volume corresponding to the MD lesions
            md_lesions_volume = subject.compute_mean_diffusivity_lesions_volume(quantiles, lesion_type)
        except ValueError:
            md_lesions_volume = ""
        return md_lesions_volume
