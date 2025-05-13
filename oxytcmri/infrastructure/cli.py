"""
Command line interface.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List

import typer

# clean architecture coder
from oxytcmri.domain.entities.mri import DTIMetric
from oxytcmri.domain.use_cases.compute_dti_normative_values import StatisticsStrategies, StatisticStrategy
from oxytcmri.infrastructure.gateways.sqlmodel_data_gateway import SQLModelSQLiteDataGateway
from oxytcmri.infrastructure.importers.csv import (
    CSVCenterImporter, CSVAtlasImporter, CSVNormativeDTIValuesImporter)
from oxytcmri.infrastructure.importers.nifti_folders import NiftiFoldersImporter
from oxytcmri.infrastructure.listeners import TqdmProgressListener
from oxytcmri.infrastructure.logger import setup_logging
# legacy code
from oxytcmri.infrastructure.settings import Settings
from oxytcmri.interface.controllers import Controller
from oxytcmri.interface.repositories.database_repositories import DataBaseGateway

command_line_interface = typer.Typer(add_completion=False)


class CLIOptionFactory:
    """Factory class for creating Typer CLI options with consistent parameters."""

    @staticmethod
    def settings_option():
        """Create a standard settings file option.

        Returns
        -------
        typer.Option
            Option for settings file path
        """
        return typer.Option(
            ...,
            "--settings",
            "-s",
            help="Path to the settings file"
        )

    @staticmethod
    def overwrite_database_option():
        """Create a standard database overwrite option.
        
        Returns
        -------
        typer.Option
            Option for database overwrite flag
        """
        return typer.Option(
            True,
            "--overwrite_database_file",
            "-odbf",
            help="Delete the database file if it already exists"
        )

    @staticmethod
    def dti_metrics_option():
        """Create a standard DTI metrics option.
        
        Returns
        -------
        typer.Option
            Option for DTI metrics
        """
        return typer.Option(
            None,
            "--dti-metrics",
            "-dti",
            help="Comma-separated list of DTI metrics to include in computations (e.g. 'FA,MD')"
        )

    @staticmethod
    def statistics_strategies_option():
        """Create a statistics strategies option.
        
        Returns
        -------
        typer.Option
            Option for statistics strategies
        """
        return typer.Option(
            None,
            "--statistics-strategies",
            "-stats",
            help="Comma-separated list of statistical strategies to include in computations (e.g. 'mean,std_dev')"
        )


class DatabaseSetup:
    """Utility class for database configuration."""

    @staticmethod
    def create_database_gateway(settings: Settings,
                                overwrite_database_file: Optional[bool] = True) -> SQLModelSQLiteDataGateway:
        """Configure and return a database gateway.
        
        Parameters
        ----------
        settings: Settings
            The application settings
        overwrite_database_file: Optional[bool]
            Whether to overwrite existing database file
            
        Returns
        -------
        SQLModelSQLiteDataGateway
            Configured database gateway
            
        Raises
        ------
        FileExistsError
            If database file exists and overwrite_database_file is False
        """
        sqlite_database_path = settings.database.path
        if Path(sqlite_database_path).exists():
            if overwrite_database_file:
                Path(sqlite_database_path).unlink()
            else:
                raise FileExistsError(f"Database file already exists: '{sqlite_database_path}'.")
        else:
            # Create the database file
            Path(sqlite_database_path).touch()
        return SQLModelSQLiteDataGateway(sqlite_database_path)


class CLIArgumentParser:
    """Parser for CLI arguments with support for various data types.

    This class centralizes the parsing logic for different types of CLI arguments,
    providing consistent error handling and format conversion.
    """

    @staticmethod
    def parse_dti_metrics(metrics_input: Optional[List[str]]) -> List[DTIMetric]:
        """Parse DTI metrics input and return a typed list.

        Parameters
        ----------
        metrics_input: Optional[List[str]]
            Raw input from CLI for DTI metrics

        Returns
        -------
        List[DTIMetric]
            Parsed DTI metrics

        Raises
        ------
        ValueError
            If invalid metrics are provided
        """
        if not metrics_input:
            return []

        try:
            acronyms_list = metrics_input[0].split(',')
            return [DTIMetric.from_acronym(acronym) for acronym in acronyms_list]
        except KeyError:
            valid_options = ', '.join([m.name for m in DTIMetric])
            raise ValueError(f"Invalid DTI metrics. Valid options are: {valid_options}")

    @staticmethod
    def parse_statistics_strategies(strategies_input: Optional[List[str]]) -> List[StatisticStrategy]:
        """Parse statistics strategies input and return a typed list.

        Parameters
        ----------
        strategies_input: Optional[List[str]]
            Raw input from CLI for statistics strategies

        Returns
        -------
        List[StatisticStrategy]
            List of statistics strategies

        Raises
        ------
        ValueError
            If invalid strategies are provided
        """
        if not strategies_input:
            return list(StatisticsStrategies.all())

        try:
            stats_names_list = strategies_input[0].split(',')
            # Replace underscores with spaces in statistical strategy names
            stats_names_list_without_underscores = [name.replace('_', ' ') for name in stats_names_list]
            return [StatisticsStrategies.get_by_name(stat_name)
                    for stat_name in stats_names_list_without_underscores]
        except ValueError:
            valid_strategies = [s.name.replace(' ', '_') for s in StatisticsStrategies.all()]
            raise ValueError(f"Invalid statistical strategies. Valid options are: {', '.join(valid_strategies)}")


class ControllerFactory:
    """Factory for creating controllers with appropriate configurations."""

    @staticmethod
    def create_dti_controller(settings: Settings,
                              database_gateway: DataBaseGateway) -> Controller:
        """Create and configure a controller for DTI operations.
        
        Parameters
        ----------
        settings : Settings
            Application settings
        database_gateway : DataBaseGateway
            Configured database gateway
            
        Returns
        -------
        Controller
            Configured controller for DTI operations
        """
        return Controller(
            persistence_gateway=database_gateway,
            importers=[
                CSVCenterImporter(settings.paths.centers_list),
                CSVAtlasImporter(settings.paths.atlases_list),
                NiftiFoldersImporter(settings.paths.nifti_files_folder),
                CSVNormativeDTIValuesImporter(settings.paths.normative_dti_values_list)
            ],
            listeners=[
                TqdmProgressListener(),
            ]
        )


class BaseDTICommand(ABC):
    """Abstract base class defining the common workflow for DTI commands."""

    def __init__(self,
                 settings_filepath: str,
                 overwrite_database_file: bool):
        """
        Initialize the command with common parameters.

        Parameters
        ----------
        settings_filepath: str
            Path to settings file
        overwrite_database_file:  bool
            Whether to overwrite existing database
        """
        settings = Settings(settings_filepath)
        setup_logging()

        # Database setup
        database_gateway = DatabaseSetup.create_database_gateway(settings, overwrite_database_file)

        # Controller setup
        self.controller = ControllerFactory.create_dti_controller(settings, database_gateway)

    @abstractmethod
    def execute(self) -> None:
        """
        Template method defining the workflow.
        """


class ComputeDTINormativeValuesCommand(BaseDTICommand):
    """Command to compute DTI normative values."""

    def __init__(self,
                 settings_filepath: str,
                 overwrite_database_file: bool,
                 dti_metrics: Optional[List[str]] = None,
                 statistics_strategies: Optional[List[str]] = None):
        """
        Initialize the command with specific parameters.

        Parameters
        ----------
        settings_filepath: str
            Path to settings file
        overwrite_database_file: bool
            Whether to overwrite existing database
        dti_metrics: Optional[List[str]]
            List of DTI metrics to compute
        statistics_strategies: Optional[List[str]]
            List of statistics strategies to use
        """
        super().__init__(settings_filepath, overwrite_database_file)
        self.dti_metric_list = CLIArgumentParser.parse_dti_metrics(dti_metrics)
        self.statistics_strategies = CLIArgumentParser.parse_statistics_strategies(statistics_strategies)

    def execute(self) -> None:
        """Process the compute DTI normative values command.
        """
        self.controller.compute_normative_dti_values(
            dti_metrics=self.dti_metric_list,
            statistics_strategies=self.statistics_strategies
        )


class SegmentDTILesionsCommand(BaseDTICommand):
    """Command to segment DTI lesions."""

    def __init__(self,
                 settings_filepath: str,
                 overwrite_database_file: bool,
                 dti_metrics: Optional[List[str]] = None):
        """
        Initialize the command with specific parameters.

        Parameters
        ----------
        settings_filepath: str
            Path to settings file
        overwrite_database_file: bool
            Whether to overwrite existing database
        dti_metrics: Optional[List[str]]
            List of DTI metrics to segment
        """
        super().__init__(settings_filepath, overwrite_database_file)
        self.dti_metric_list = CLIArgumentParser.parse_dti_metrics(dti_metrics)

    def execute(self) -> None:
        """
        Process the segment DTI lesions command.
        """
        self.controller.segment_dti_abnormal_values(dti_metrics=self.dti_metric_list)


@command_line_interface.command()
def compute_dti_normative_values(
        settings_filepath: str = CLIOptionFactory.settings_option(),
        overwrite_database_file: bool = CLIOptionFactory.overwrite_database_option(),
        dti_metrics: Optional[List[str]] = CLIOptionFactory.dti_metrics_option(),
        statistics_strategies: Optional[List[str]] = CLIOptionFactory.statistics_strategies_option(),
):
    """Compute DTI normative values for all centers and store the results in the database.
    
    This command processes DTI data to calculate normative values across centers
    for specified metrics and statistical strategies.
    """
    command = ComputeDTINormativeValuesCommand(
        settings_filepath=settings_filepath,
        overwrite_database_file=overwrite_database_file,
        dti_metrics=dti_metrics,
        statistics_strategies=statistics_strategies
    )
    command.execute()


@command_line_interface.command()
def segment_dti_lesions(
        settings_filepath: str = CLIOptionFactory.settings_option(),
        overwrite_database_file: bool = CLIOptionFactory.overwrite_database_option(),
        dti_metrics: Optional[List[str]] = CLIOptionFactory.dti_metrics_option(),
):
    """Segment DTI lesions based on normative values.
    
    This command uses previously computed normative values to identify
    and segment abnormal regions in DTI data.
    """
    command = SegmentDTILesionsCommand(
        settings_filepath=settings_filepath,
        overwrite_database_file=overwrite_database_file,
        dti_metrics=dti_metrics
    )
    command.execute()
