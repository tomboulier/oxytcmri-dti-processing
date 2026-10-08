# Données de test synthétiques

Tout le contenu de ce dossier est **synthétique** : les volumes NIfTI sont
générés par `oxytcmri/tests/generate_test_data.py` à partir de la
spécification `oxytcmri/tests/test-data-spec.json` (dimensions, affine et type
de chaque fichier) et d'un générateur pseudo-aléatoire déterministe.

Aucune donnée de participant à l'étude Oxy-TC n'est présente ici. Les
identifiants d'examen (par exemple `01_71v_mr_170913`) sont fictifs : les
numéros de sujets 69 à 99 n'existent pas dans l'essai.

Pour régénérer les fichiers :

```bash
uv run python -m oxytcmri.tests.generate_test_data
```

Les valeurs attendues des tests (moyennes, écarts-types de MD par région
d'atlas) sont calculées sur ces données synthétiques ; si la graine ou la
spécification change, elles doivent être recalculées.

## Fantômes réalistes

Des images de test plus réalistes (anatomie simplifiée, valeurs de MD
physiologiques, lésions insérées selon la recette de Mistral et al. 2022 avec
vérité terrain) sont générées à la volée par le package
`oxytcmri.tests.phantoms` ; elles ne sont pas stockées dans ce dossier. Voir la
section « Realistic digital phantoms » du README principal.
