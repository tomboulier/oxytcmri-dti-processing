import os
import subprocess


def process_single_patient(patient_dir):
    """
    Traite les données pour un patient donné.
    Args:
        patient_dir (str): Chemin vers le répertoire du patient.
    """
    # Vérifiez si les fichiers nécessaires existent
    required_files = [
        "MD_map.nii.gz",
        "Atlas2.nii.gz",
        "Atlas3.nii.gz",
        "Atlas4.nii.gz",
        "Atlas5.nii.gz",
        "Atlas6.nii.gz"
    ]

    missing_files = [f for f in required_files if not os.path.exists(os.path.join(patient_dir, f))]
    if missing_files:
        print(f"Fichiers manquants pour {patient_dir} : {missing_files}")
        return

    # Construisez la commande pour oxytc_train.py
    command = [
        "python", "oxytc_train.py",
        "--i", os.path.join(patient_dir, "MD_map.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas2.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas3.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas4.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas5.nii.gz"),
        "--a", os.path.join(patient_dir, "Atlas6.nii.gz"),
        "-ocsv", os.path.join(patient_dir, "MD_results.csv"),
        "-opkl", os.path.join(patient_dir, "MD_results.pkl"),
        "-pmin", "5",
        "-pmax", "95"
    ]

    # Affichez la commande pour debug
    print(f"Commande exécutée : {' '.join(command)}")

    # Exécutez la commande
    try:
        subprocess.run(command, check=True)
        print(f"Traitement terminé pour {patient_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution pour {patient_dir} : {e}")


if __name__ == "__main__":
    # Chemin vers le répertoire du patient à tester
    patient_dir = "OxyTC_Pixyl_results/Healthy/C01/01_03v_mr_19062015"

    # Vérifiez si le répertoire existe
    if not os.path.exists(patient_dir):
        print(f"Le répertoire spécifié n'existe pas : {patient_dir}")
    else:
        # Lancez le traitement pour un seul patient
        process_single_patient(patient_dir)
