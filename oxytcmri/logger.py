import logging
import os
from pathlib import Path
from dynaconf import Dynaconf
import tempfile


class LoggerSingleton:
    _instance = None

    def __new__(cls, settings: Dynaconf):
        if cls._instance is None:
            cls._instance = super(LoggerSingleton, cls).__new__(cls)
            cls._instance._initialize(settings)
        return cls._instance

    def _initialize(self, settings: Dynaconf):
        """Configure logging and return the configured logger."""
        self.logger = logging.getLogger(__name__)

        # Verify if the logs module exists in settings
        if not hasattr(settings, "logs"):
            # If not, logs will be written in a temporary directory
            temp_dir = tempfile.TemporaryDirectory()
            log_path = Path(temp_dir.name)
            log_filename = "temp_logs.log"
            log_level = "INFO"
        else:
            log_path = Path(settings.logs.LogsDirectoryPath)
            log_filename = settings.logs.LogsFilename
            # Set the log level to INFO if not specified in settings
            log_level = settings.logs.LogLevel.upper() if hasattr(settings.logs, "LogLevel") else "INFO"

        # Set the log level from settings
        self.logger.setLevel(log_level)

        # Create file handler
        os.makedirs(log_path, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_path, log_filename))

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Add formatter to file handler
        file_handler.setFormatter(formatter)

        # Add file handler to logger
        self.logger.addHandler(file_handler)

        # Set SQLAlchemy log level to WARNING to make it less verbose
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def get_logger(settings: Dynaconf) -> logging.Logger:
    """Get the singleton logger instance."""
    return LoggerSingleton(settings).logger


def log_and_raise(logger: logging.Logger, exception, message: str):
    """Log an exception and raise it."""
    logger.error(message)
    raise exception(message)
