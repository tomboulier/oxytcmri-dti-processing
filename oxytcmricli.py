from pathlib import Path
from typing import Optional, List

import typer

# clean architecture coder
from oxytcmri.domain.entities.mri import DTIMetric
from oxytcmri.domain.use_cases.compute_dti_normative_values import StatisticsStrategies
from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.infrastructure.importers.csv import (
    CSVCenterImporter, CSVAtlasImporter, CSVNormativeDTIValuesImporter)
from oxytcmri.infrastructure.importers.nifti_folders import NiftiFoldersImporter
from oxytcmri.infrastructure.listeners import TqdmProgressListener
from oxytcmri.infrastructure.logger import setup_logging
from oxytcmri.interface.controllers import Controller
# legacy code
from oxytcmri.settings import Settings

app = typer.Typer(add_completion=False)


@app.command()
def compute_dti_normative_values(
        settings_filepath: str = typer.Option(
            ...,
            "--settings",
            "-s",
            help="Path to the settings file"
        ),
        overwrite_database_file: bool = typer.Option(
            True,
            "--overwrite_database_file",
            "-odbf",
            help="Delete the database file if it already exists"
        ),
        dti_metrics: Optional[List[str]] = typer.Option(
            None,
            "--dti-metrics",
            "-dti",
            help="Comma-separated list of DTI metrics to include in computations (e.g. 'FA,MD')"
        ),
        statistics_strategies: Optional[List[str]] = typer.Option(
            None,
            "--statistics-strategies",
            "-stats",
            help="Comma-separated list of statistical strategies to include in computations (e.g. 'mean,std_dev')"
        ),
):
    """
    Compute DTI normative values for all subjects and store the results in the database.
    """
    settings = Settings(settings_filepath)
    setup_logging()

    # create database gateway for persistent storage
    sqlite_database_path = settings.database.path
    if Path(sqlite_database_path).exists():
        if overwrite_database_file:
            Path(sqlite_database_path).unlink()
        else:
            raise FileExistsError(f"Database file already exists: '{sqlite_database_path}'.")
    else:
        # Create the database file
        Path(sqlite_database_path).touch()
    database_gateway = SQLModelSQLiteDataGateway(sqlite_database_path)

    # Convert string inputs to proper types if provided
    dti_metric_list = None
    if dti_metrics:
        try:
            acronyms_list = dti_metrics[0].split(',')
            dti_metric_list = [DTIMetric.from_acronym(acronym) for acronym in acronyms_list]
        except KeyError as e:
            raise ValueError(f"Invalid DTI metric: {e}. Valid options are: {', '.join([m.name for m in DTIMetric])}")

    stat_strategy_list = None
    if statistics_strategies:
        try:
            stats_names_list = statistics_strategies[0].split(',')
            # Replace underscores with spaces in statistical strategy names
            stats_names_list_without_underscores = [name.replace('_', ' ') for name in stats_names_list]
            stat_strategy_list = [StatisticsStrategies.get_by_name(stat_name)
                                  for stat_name in stats_names_list_without_underscores]
        except ValueError as e:
            valid_strategies = [s.name for s in StatisticsStrategies.all()]
            raise ValueError(f"Invalid statistical strategy: {e}. Valid options are: {', '.join(valid_strategies)}")

    controller = Controller(persistence_gateway=database_gateway,
                            importers=[
                                CSVCenterImporter(settings.paths.centers_list),
                                CSVAtlasImporter(settings.paths.atlases_list),
                                NiftiFoldersImporter(settings.paths.nifti_files_folder),
                                CSVNormativeDTIValuesImporter(settings.paths.normative_dti_values_list)
                            ],
                            listeners=[
                                TqdmProgressListener(),  # Progress bar using tqdm
                            ])

    controller.compute_normative_dti_values(
        dti_metrics=dti_metric_list,
        statistics_strategies=stat_strategy_list
    )
