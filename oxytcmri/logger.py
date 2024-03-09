import logging
import os
from pathlib import Path
from dynaconf import Dynaconf
import tempfile


def get_logger(settings: Dynaconf) -> logging.Logger:
    """Configure logging and return the configured logger.

    Parameters
    ----------
    settings: Dynaconf
        Settings object containing paths to the logs directory and logs filename in the following format:
        - settings.logs.LogsDirectoryPath: str
        - settings.logs.LogsFilename: str

    Returns
    -------
    logging.Logger
        Configured logger.
    """

    # Create a custom logger
    logger = logging.getLogger(__name__)

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
    logger.setLevel(log_level)

    # Create file handler
    os.makedirs(log_path, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(log_path, log_filename))

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to file handler
    file_handler.setFormatter(formatter)

    # Add file handler to logger
    logger.addHandler(file_handler)

    # Set SQLAlchemy log level to WARNING to make it less verbose
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    return logger


def log_and_raise(logger: logging.Logger, exception, message: str):
    """Log an exception and raise it.

    Parameters
    ----------
    logger: logging.Logger
        Logger object.
    exception: Exception
        Exception to be raised.
    message: str
        Message to be logged.
    """
    logger.error(message)
    raise exception(message)
