import logging
import os
from pathlib import Path
from dynaconf import Dynaconf


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

    # Set the log level from settings
    logger.setLevel(settings.logs.LogLevel.upper() if hasattr(settings.logs, "LogLevel") else "INFO")

    # Create file handler
    try:
        log_path = Path(settings.logs.LogsDirectoryPath)
        os.makedirs(log_path, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_path, settings.logs.LogsFilename))
    except AttributeError as error:
        raise AttributeError("Missing logs.LogsDirectoryPath and logs.LogsFilename in settings attributes.") from error

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to file handler
    file_handler.setFormatter(formatter)

    # Add file handler to logger
    logger.addHandler(file_handler)

    # Set SQLAlchemy log level to WARNING to make it less verbose
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    return logger
