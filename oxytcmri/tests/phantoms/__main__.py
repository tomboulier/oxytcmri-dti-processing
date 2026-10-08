"""
Command line entry point: write a phantom cohort to a folder.

Usage::

    uv run python -m oxytcmri.tests.phantoms --output data/phantoms --voxel-size 2 --patients 2

The generated ``settings.toml`` can then be passed to the pipeline::

    uv run python main.py load-data -s data/phantoms/settings.toml
    uv run python main.py compute-dti-normative-values -s data/phantoms/settings.toml -dti MD
    uv run python main.py segment-dti-lesions -s data/phantoms/settings.toml -dti MD
"""
import argparse
from pathlib import Path

from oxytcmri.tests.phantoms.anatomy import PhantomGeometry
from oxytcmri.tests.phantoms.cohort import (
    CohortSpec,
    default_parcellations_with,
    generate_cohort,
    summarize,
)


def parse_arguments() -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description="Generate synthetic DTI phantoms with ground-truth lesions.")
    parser.add_argument("--output", type=Path, default=Path("data/phantoms"), help="output folder")
    parser.add_argument("--voxel-size", type=float, default=3.0, help="isotropic voxel size in mm")
    parser.add_argument("--centers", type=int, default=2, help="number of centres")
    parser.add_argument("--healthy", type=int, default=3, help="healthy volunteers per centre")
    parser.add_argument("--patients", type=int, default=1, help="patients per centre")
    parser.add_argument("--grid-atlas", action="store_true", help="add a third, grid-based atlas")
    parser.add_argument("--seed", type=int, default=2024, help="random seed")
    return parser.parse_args()


def main() -> None:
    """Generate the cohort described on the command line and print its summary."""
    args = parse_arguments()
    centers = {index: f"Centre {chr(ord('A') + index - 1)}" for index in range(1, args.centers + 1)}
    scales = {index: 1.0 + 0.04 * ((index - 1) % 3 - 1) for index in centers}
    spec = CohortSpec(
        centers=centers,
        healthy_per_center=args.healthy,
        patients_per_center=args.patients,
        center_scales=scales,
        geometry=PhantomGeometry.isotropic(voxel_size_mm=args.voxel_size),
        parcellations=default_parcellations_with([3] if args.grid_atlas else []),
        seed=args.seed,
    )
    cohort = generate_cohort(spec, args.output)
    print(summarize(cohort))
    print(f"\nFiles written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
