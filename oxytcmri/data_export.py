import csv
import os


class DataExporter:
    def __init__(self, db_controller: "DatabaseController"):
        self.db_controller = db_controller

    def get_md_lesion_volumes(self, subject, quantiles, lesion_type, localisations):
        return {
            f"{lesion_type}_MD_lesions_in_mL_{quantiles}_{localisation}": subject.get_md_lesion_volumes(
                quantiles=quantiles, lesion_type=lesion_type, localisation=localisation
            )
            for localisation in localisations
        }

    def export_data_to_csv(self, csv_file_path: str) -> None:
        """Export all MD lesions (high and low) to a CSV file.

        Parameters
        ----------
        csv_file_path : str
            Path to the CSV file.

        Returns
        -------
        None
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

        # Get all the subjects from the database
        subjects = self.db_controller.get_all_subjects()

        # Define localisations
        localisations = self.db_controller.get_distinct_localizations()

        # Create the CSV file
        with open(csv_file_path, mode="w") as csv_file:
            fieldnames = (
                ["subject_id", "center_id", "center_name"]
                + [
                    f"{lesion_type}_MD_lesions_in_mL_{quantiles}_{localisation}"
                    for quantiles in ["7_94", "10_95"]
                    for lesion_type in ["low", "high"]
                    for localisation in localisations
                ]
                + [
                    "gose_6_months",
                    "gose_12_months",
                    "impact_score_mortality",
                    "impact_score_neurological_outcome",
                    "marshall_score",
                    "pbto2",
                    "age",
                    "sex",
                    "glasgow_coma_scale",
                    "IGS2",
                ]
            )
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()

            # For each subject, get the volume corresponding to the MD lesions
            for subject in subjects:
                if subject.subject_type != "Patient":
                    continue

                # Get MD lesion volumes
                md_lesion_volumes = {}
                for quantiles in ["7_94", "10_95"]:
                    for lesion_type in ["low", "high"]:
                        md_lesion_volumes.update(
                            self.get_md_lesion_volumes(
                                subject, quantiles, lesion_type, localisations
                            )
                        )

                # Write the data to the CSV file
                writer.writerow(
                    {
                        "subject_id": subject.id,
                        "center_id": subject.center.id,
                        "center_name": subject.center.name,
                        **md_lesion_volumes,
                        "gose_6_months": subject.gose_6_months,
                        "gose_12_months": subject.gose_12_months,
                        "impact_score_mortality": subject.impact_score_mortality,
                        "impact_score_neurological_outcome": subject.impact_score_neurological_outcome,
                        "marshall_score": subject.marshall_score,
                        "pbto2": subject.pbto2,
                        "age": subject.age,
                        "sex": subject.sex,
                        "glasgow_coma_scale": subject.glasgow_coma_scale,
                        "IGS2": subject.igs2_score,
                    }
                )
