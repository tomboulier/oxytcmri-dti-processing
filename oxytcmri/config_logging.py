import logging


def config_logging() -> None:
    """Configure logging.
    """
    # Create a custom logger
    logging.basicConfig(level=logging.INFO)

    # Create handlers
    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(logging.INFO)

    logging.getLogger().addHandler(file_handler)
