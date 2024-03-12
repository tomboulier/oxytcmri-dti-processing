import csv

class DataExporter:
    def __init__(self, db_controller: 'DatabaseController'):
        self.db_controller = db_controller

    def export_md_lesions_to_csv(self, csv_file_path: str) -> None:
        """Export all MD lesions (high and low) to a CSV file.

        Parameters
        ----------
        csv_file_path : str
            Path to the CSV file.

        Returns
        -------
        None
        """
        # Get all the subjects from the database
        subjects = self.db_controller.get_all_subjects()

        # Create the CSV file
        with open(csv_file_path, mode='w') as csv_file:
            fieldnames = ['subject_id',
                          'center_id',
                          'center_name',
                          'low_MD_lesions_in_mL_7_94',
                          'high_MD_lesions_in_mL_7_94',
                          'low_MD_lesions_in_mL_10_95',
                          'high_MD_lesions_in_mL_10_95',
                          'gose_6_months',
                          'gose_12_months',
                          'impact_score_mortality',
                          'impact_score_neurological_outcome',
                          'marshall_score',
                          'pbto2',
                          'age',
                          'sex',
                          'glasgow_coma_scale',
                          ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()

            # For each subject, get the volume corresponding to the MD lesions
            for subject in subjects:
                if subject.subject_type != "Patient":
                    continue

                try:
                    # Get the volume corresponding to the MD lesions
                    low_md_lesions_volume_7_94 = subject.compute_mean_diffusivity_lesions_volume(quantiles="7_94",
                                                                                                 lesion_type="low")
                    high_md_lesions_volume_7_94 = subject.compute_mean_diffusivity_lesions_volume(quantiles="7_94",
                                                                                                  lesion_type="high")
                    low_md_lesions_volume_10_95 = subject.compute_mean_diffusivity_lesions_volume(quantiles="10_95",
                                                                                                  lesion_type="low")
                    high_md_lesions_volume_10_95 = subject.compute_mean_diffusivity_lesions_volume(quantiles="10_95",
                                                                                                   lesion_type="high")
                except ValueError:
                    low_md_lesions_volume_7_94 = ""
                    high_md_lesions_volume_7_94 = ""
                    low_md_lesions_volume_10_95 = ""
                    high_md_lesions_volume_10_95 = ""

                # Write the data to the CSV file
                writer.writerow({'subject_id': subject.id,
                                 'center_id': subject.center.id,
                                 'center_name': subject.center.name,
                                 'low_MD_lesions_in_mL_7_94': low_md_lesions_volume_7_94,
                                 'high_MD_lesions_in_mL_7_94': high_md_lesions_volume_7_94,
                                 'low_MD_lesions_in_mL_10_95': low_md_lesions_volume_10_95,
                                 'high_MD_lesions_in_mL_10_95': high_md_lesions_volume_10_95,
                                 'gose_6_months': subject.gose_6_months,
                                 'gose_12_months': subject.gose_12_months,
                                 'impact_score_mortality': subject.impact_score_mortality,
                                 'impact_score_neurological_outcome': subject.impact_score_neurological_outcome,
                                 'marshall_score': subject.marshall_score,
                                 'pbto2': subject.pbto2,
                                 'age': subject.age,
                                 'sex': subject.sex,
                                 'glasgow_coma_scale': subject.glasgow_coma_scale,
                                 }
                                )