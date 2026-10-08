"""
Realistic digital DTI phantoms for testing.

This package generates fully synthetic, reproducible test images that mimic
the *realistic TBI phantoms* used to validate the lesion quantification
method (Mistral et al., Front. Neurol. 2022, doi:10.3389/fneur.2021.740603):

- a simplified brain anatomy (cortex, white matter, deep grey nuclei, corpus
  callosum, ventricles) with physiological mean diffusivity (MD) values;
- several atlas parcellations of that anatomy;
- lesions inserted in patient images by multiplying MD by a coefficient
  (0.41-0.91 for low MD, 1.10-2.10 for high MD), then smoothed with a 3 mm
  Gaussian filter, together with the ground-truth lesion masks.

No participant data is used: everything is derived from a seeded random
generator.
"""
from oxytcmri.tests.phantoms.anatomy import (
    PhantomGeometry,
    Tissue,
    TissueModel,
    build_tissue_model,
)
from oxytcmri.tests.phantoms.cohort import (
    CohortSpec,
    PhantomCohort,
    PhantomExam,
    generate_cohort,
)
from oxytcmri.tests.phantoms.lesions import (
    Lesion,
    LesionKind,
    apply_lesions,
    sample_lesions,
)

__all__ = [
    "PhantomGeometry", "Tissue", "TissueModel", "build_tissue_model",
    "Lesion", "LesionKind", "apply_lesions", "sample_lesions",
    "CohortSpec", "PhantomCohort", "PhantomExam", "generate_cohort",
]
