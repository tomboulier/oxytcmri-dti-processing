"""
Command line interface.
"""
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
# legacy code
from oxytcmri.infrastructure.settings import Settings
from oxytcmri.interface.controllers import Controller

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
    def create_database_gateway(settings, overwrite_database_file=True) -> SQLModelSQLiteDataGateway:
        """Configure and return a database gateway.
        
        Parameters
        ----------
        settings : Settings
            The application settings
        overwrite_database_file : bool, default=True
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


class DTIMetricStrategy:
    """Strategy for processing DTI metrics input."""
    
    def parse_metrics(self, metrics_input):
        """Process DTI metrics input and return a typed list.
        
        Parameters
        ----------
        metrics_input : list of str or None
            Raw input from CLI for DTI metrics
            
        Returns
        -------
        list of DTIMetric
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


class StatisticsStrategy:
    """Strategy for processing statistics strategies input."""
    
    def parse_strategies(self, strategies_input):
        """Process statistics strategies input and return a typed list.
        
        Parameters
        ----------
        strategies_input : list of str or None
            Raw input from CLI for statistics strategies
            
        Returns
        -------
        list
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
    def create_dti_controller(settings, database_gateway):
        """Create and configure a controller for DTI operations.
        
        Parameters
        ----------
        settings : Settings
            Application settings
        database_gateway : SQLModelSQLiteDataGateway
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


class BaseDTICommand:
    """Abstract base class defining the common workflow for DTI commands."""
    
    def execute(self, settings_filepath, overwrite_database_file, dti_metrics, **kwargs):
        """Template method defining the workflow.
        
        Parameters
        ----------
        settings_filepath : str
            Path to settings file
        overwrite_database_file : bool
            Whether to overwrite existing database
        dti_metrics : list of str or None
            DTI metrics to process
        **kwargs
            Additional command-specific parameters
        """
        # Common steps
        settings = Settings(settings_filepath)
        setup_logging()
        
        # Database setup
        database_gateway = DatabaseSetup.create_database_gateway(settings, overwrite_database_file)
        
        # DTI metrics processing
        metric_strategy = DTIMetricStrategy()
        dti_metric_list = metric_strategy.parse_metrics(dti_metrics)
        
        # Command-specific processing
        self._process_command(settings, database_gateway, dti_metric_list, **kwargs)
    
    def _process_command(self, settings, database_gateway, dti_metric_list, **kwargs):
        """Method to be implemented by subclasses.
        
        Parameters
        ----------
        settings : Settings
            Application settings
        database_gateway : SQLModelSQLiteDataGateway
            Configured database gateway
        dti_metric_list : list of DTIMetric
            Processed DTI metrics
        **kwargs
            Additional command-specific parameters
            
        Raises
        ------
        NotImplementedError
            When not implemented by a subclass
        """
        raise NotImplementedError("Subclasses must implement this method")


class ComputeDTINormativeValuesCommand(BaseDTICommand):
    """Command to compute DTI normative values."""
    
    def _process_command(self, settings, database_gateway, dti_metric_list, statistics_strategies=None, **kwargs):
        """Process the compute DTI normative values command.
        
        Parameters
        ----------
        settings : Settings
            Application settings
        database_gateway : SQLModelSQLiteDataGateway
            Configured database gateway
        dti_metric_list : list of DTIMetric
            Processed DTI metrics
        statistics_strategies : list of str or None, optional
            Statistics strategies to use
        **kwargs
            Additional parameters
        """
        # Process statistics strategies
        stats_strategy = StatisticsStrategy()
        stat_strategy_list = stats_strategy.parse_strategies(statistics_strategies)
        
        # Create and use controller
        controller = ControllerFactory.create_dti_controller(settings, database_gateway)
        controller.compute_normative_dti_values(
            dti_metrics=dti_metric_list,
            statistics_strategies=stat_strategy_list
        )


class SegmentDTILesionsCommand(BaseDTICommand):
    """Command to segment DTI lesions."""
    
    def _process_command(self, settings, database_gateway, dti_metric_list, **kwargs):
        """Process the segment DTI lesions command.
        
        Parameters
        ----------
        settings : Settings
            Application settings
        database_gateway : SQLModelSQLiteDataGateway
            Configured database gateway
        dti_metric_list : list of DTIMetric
            Processed DTI metrics
        **kwargs
            Additional parameters
            
        Raises
        ------
        NotImplementedError
            Until implementation is complete
        """
        # Create controller
        controller = ControllerFactory.create_dti_controller(settings, database_gateway)
        
        # Add your implementation here
        # controller.segment_dti_lesions(dti_metrics=dti_metric_list, ...)
        raise NotImplementedError("Segment DTI lesions not yet implemented")


@command_line_interface.command()
def compute_dti_normative_values(
        settings_filepath: str = CLIOptionFactory.settings_option(),
        overwrite_database_file: bool = CLIOptionFactory.overwrite_database_option(),
        dti_metrics: Optional[List[str]] = CLIOptionFactory.dti_metrics_option(),
        statistics_strategies: Optional[List[str]] = CLIOptionFactory.statistics_strategies_option(),
):
    """Compute DTI normative values for all centers and store the results in the database."""
    command = ComputeDTINormativeValuesCommand()
    command.execute(settings_filepath, overwrite_database_file, dti_metrics, statistics_strategies=statistics_strategies)


@command_line_interface.command()
def segment_dti_lesions(
        settings_filepath: str = CLIOptionFactory.settings_option(),
        overwrite_database_file: bool = CLIOptionFactory.overwrite_database_option(),
        dti_metrics: Optional[List[str]] = CLIOptionFactory.dti_metrics_option(),
):
    """Segment DTI lesions based on normative values."""
    command = SegmentDTILesionsCommand()
    command.execute(settings_filepath, overwrite_database_file, dti_metrics)
