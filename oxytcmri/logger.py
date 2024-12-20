import logging
import os
from pathlib import Path
from oxytcmri.settings import Settings
import tempfile


class LoggerSingleton:
    _instance = None

    def __new__(cls, settings: Settings):
        if cls._instance is None:
            cls._instance = super(LoggerSingleton, cls).__new__(cls)
            cls._instance._initialize(settings)
        return cls._instance

    def _initialize(self, settings: Settings):
        """
        Configure logging based on the provided settings.

        Parameters:
        settings (Settings): Configuration settings for logging.

        Returns:
        None
        """
        logger_name = self._get_logger_name(settings)
        self.logger = logging.getLogger(logger_name)
        self._configure_logger(settings)

    def _get_logger_name(self, settings: Settings) -> str:
        """
        Get the logger name based on the settings.

        Parameters:
        settings (Settings): Configuration settings for logging.

        Returns:
        str: The logger name.
        """
        return f"oxytcmri_{Path(settings.filepath).stem}"

    def _configure_logger(self, settings: Settings):
        """
        Configure the logger based on the settings.

        Parameters:
        settings (Settings): Configuration settings for logging.

        Returns:
        None
        """
        log_path, log_filename, log_level = self._get_log_config(settings)
        self._set_log_level(log_level)
        self._create_log_directory(log_path)
        file_handler = self._create_file_handler(log_path, log_filename)
        self._set_formatter(file_handler)
        self.logger.addHandler(file_handler)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    def _get_log_config(self, settings: Settings):
        """
        Get the log configuration from the settings.

        Parameters:
        settings (Settings): Configuration settings for logging.

        Returns:
        tuple: The log path, log filename, and log level.
        """
        if not hasattr(settings, "logs"):
            temp_dir = tempfile.TemporaryDirectory()
            log_path = Path(temp_dir.name)
            log_filename = "temp_logs.log"
            log_level = "INFO"
        else:
            log_path = Path(settings.logs.LogsDirectoryPath)
            log_filename = settings.logs.LogsFilename
            log_level = settings.logs.LogLevel.upper() if hasattr(settings.logs, "LogLevel") else "INFO"
        return log_path, log_filename, log_level

    def _set_log_level(self, log_level: str):
        """
        Set the log level for the logger.

        Parameters:
        log_level (str): The log level.

        Returns:
        None
        """
        self.logger.setLevel(log_level)

    def _create_log_directory(self, log_path: Path):
        """
        Create the log directory if it does not exist.

        Parameters:
        log_path (Path): The path to the log directory.

        Returns:
        None
        """
        try:
            os.makedirs(log_path, exist_ok=True)
        except PermissionError:
            raise PermissionError(f"Permission denied to create log directory: '{log_path}'.")

    def _create_file_handler(self, log_path: Path, log_filename: str) -> logging.FileHandler:
        """
        Create a file handler for logging.

        Parameters:
        log_path (Path): The path to the log directory.
        log_filename (str): The name of the log file.

        Returns:
        logging.FileHandler: The file handler for logging.
        """
        try:
            return logging.FileHandler(os.path.join(log_path, log_filename))
        except PermissionError:
            raise PermissionError(f"Permission denied to create log file: '{log_filename}' in '{log_path}'.")

    def _set_formatter(self, file_handler: logging.FileHandler):
        """
        Set the formatter for the file handler.

        Parameters:
        file_handler (logging.FileHandler): The file handler.

        Returns:
        None
        """
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

def get_logger(settings: Settings) -> logging.Logger:
    """Get the singleton logger instance."""
    return LoggerSingleton(settings).logger


def log_and_raise(logger: logging.Logger, exception, message: str):
    """Log an exception and raise it."""
    logger.error(message)
    raise exception(message)
