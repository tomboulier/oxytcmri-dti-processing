"""Génère les données de test synthétiques du dossier ``test-data``.

Toutes les images NIfTI de test sont produites ici, à partir de la
spécification ``test-data-spec.json`` (chemin, dimensions, affine, type) et
d'un générateur pseudo-aléatoire déterministe. Aucune donnée de participant
à l'étude Oxy-TC n'est utilisée : les identifiants d'examen (par exemple
``01_71v_mr_170913``) sont fictifs, les numéros de sujets 69 à 99 n'existant
pas dans l'essai, et le contenu des volumes est tiré au sort.

Deux voxels du fichier ``dti-data/Healthy/C01/01_71v_mr_170913/MD_map.nii.gz``
sont fixés à des valeurs précises car les tests unitaires de
``NiftiVoxelData`` les vérifient explicitement.

Usage : ``uv run python -m oxytcmri.tests.generate_test_data``
"""
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np

SPEC_FILE = Path(__file__).parent / "test-data-spec.json"
TEST_DATA_DIR = Path(__file__).parent / "test-data"

# Valeurs de voxels attendues par test_unit_voxel_data_adapters.py
FICHIER_CONTRAINT = "dti-data/Healthy/C01/01_71v_mr_170913/MD_map.nii.gz"
VOXELS_IMPOSES = {(0, 0, 0): 0.0, (32, 32, 32): 131.0}

LABELS_ATLAS = {
    "Atlas2": [0, 0, 0, 29, 33, 62],  # le 0 (fond) est surreprésenté à dessein
    "Atlas4": [0, 0, 0, 55, 59, 62],
}


def _rng_pour(chemin: str) -> np.random.Generator:
    """Un générateur aléatoire déterministe propre à chaque fichier."""
    graine = int(hashlib.sha1(chemin.encode()).hexdigest()[:8], 16)
    return np.random.default_rng(graine)


def _contenu(entree: dict) -> np.ndarray:
    rng = _rng_pour(entree["path"])
    forme = tuple(entree["shape"])
    nom = Path(entree["path"]).name
    if entree["kind"] == "atlas":
        labels = LABELS_ATLAS["Atlas2" if nom.startswith("Atlas2") else "Atlas4"]
        return rng.choice(labels, size=forme)
    if entree["kind"] == "mask":
        valeurs = [0, 1, 2] if "segmentation" in nom else [0, 1]
        return rng.choice(valeurs, size=forme)
    # carte MD : valeurs plausibles, positives
    donnees = rng.normal(loc=100.0, scale=25.0, size=forme).clip(0, 250)
    if entree["path"] == FICHIER_CONTRAINT:
        for coord, valeur in VOXELS_IMPOSES.items():
            donnees[coord] = valeur
    return donnees


def main() -> None:
    spec = json.loads(SPEC_FILE.read_text())
    for entree in spec:
        cible = TEST_DATA_DIR / entree["path"]
        cible.parent.mkdir(parents=True, exist_ok=True)
        affine = np.array(entree["affine"]).reshape(4, 4)
        donnees = _contenu(entree).astype(entree["dtype"])
        nib.save(nib.Nifti1Image(donnees, affine), str(cible))
    print(f"{len(spec)} fichiers générés dans {TEST_DATA_DIR}")


if __name__ == "__main__":
    main()
