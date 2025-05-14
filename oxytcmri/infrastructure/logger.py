"""
Logging configuration module for the package.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

from oxytcmri.infrastructure.settings import Settings


class Logger:
    """
    Logger class for configuring logging settings.

    This class sets up logging configuration based on the provided settings.

    Attributes
    ----------
    log_level : str
            The logging level.
    save_to_file : bool
        Whether to save logs to a file.
    log_to_console : bool
        Whether to log to console.
    """
    def __init__(self, settings: Settings):
        """
        Initialize the logger with the given settings.

        Parameters
        ----------
        settings : Settings
            The settings object containing logging configuration.
        """
        self.settings = settings
        self.log_level = self.get_log_level()
        self.save_to_file = self.get_save_to_file()
        self.log_to_console = self.get_log_to_console()

    def get_log_level(self) -> str:
        try:
            return self.settings.logs.log_level
        except AttributeError:
            return "INFO"

    def get_save_to_file(self) -> bool:
        try:
            return self.settings.logs.save_to_file
        except AttributeError:
            return True

    def get_log_to_console(self) -> bool:
        try:
            return self.settings.logs.log_to_console
        except AttributeError:
            return False

    def setup(self):
        """
        Set up logging configuration for the package.
        """

        log_handlers = []
        if self.log_to_console:
            log_handlers.append(logging.StreamHandler(sys.stdout))

        if self.save_to_file:
            logs_folder = Path(__file__).parents[2] / "logs"
            if not logs_folder.exists():
                raise FileNotFoundError(f"Logs folder not found: '{logs_folder}'.")
            log_file = logs_folder / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_oxytcmri.log"
            log_handlers.append(logging.FileHandler(log_file))
            print(f"To follow the logs in real-time, use the command: tail -f '{log_file}'")

        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=log_handlers
        )
