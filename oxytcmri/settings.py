from pathlib import Path

from dynaconf import Dynaconf


def load_settings(settings_filepath: str) -> Dynaconf:
    """Import settings from a file."""
    # Verify if the settings file exists
    if not Path(settings_filepath).exists():
        error_message = f"Settings file not found: {settings_filepath}"

    # Create an instance of Dynaconf for managing settings.
    settings = Dynaconf(settings_files=[settings_filepath])

    return settings
