import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_level="INFO", save_to_file=True, log_to_console=False):
    log_handlers = []
    if log_to_console:
        log_handlers.append(logging.StreamHandler(sys.stdout))

    if save_to_file:
        logs_folder = Path(__file__).parents[2] / "logs"
        if not logs_folder.exists():
            raise FileNotFoundError(f"Logs folder not found: '{logs_folder}'.")
        log_file = logs_folder / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_oxytcmri.log"
        log_handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=log_handlers
    )
