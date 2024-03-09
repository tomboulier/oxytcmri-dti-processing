from pathlib import Path
from dynaconf import Dynaconf
from dynaconf.utils.boxing import DynaBox


def load_settings(settings_filepath: str) -> Dynaconf:
    """Import settings from a file."""
    # Verify if the settings file exists
    if not Path(settings_filepath).exists():
        error_message = f"Settings file not found: '{settings_filepath}'"

    # Create an instance of Dynaconf for managing settings.
    settings = Dynaconf(settings_files=[settings_filepath])

    return settings


class Settings:
    def __init__(self, filepath: str):
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Settings file not found: '{filepath.absolute()}'.")
        self.filepath = filepath
        self._dynaconf_settings = Dynaconf(settings_file=filepath)

    def __getattr__(self, name: str):
        try:
            response = self._dynaconf_settings.__getattr__(name)
            if isinstance(response, DynaBox):
                return ModuleSettings(name, response, self.filepath)
            return response
        except AttributeError:
            raise AttributeError(f"No module '{name}' in settings file '{self.filepath.absolute()}'.")


class ModuleSettings:
    def __init__(self, module_name: str, dynabox: DynaBox, filepath: Path):
        self.module_name = module_name
        self._dynabox = dynabox
        self.filepath = filepath

    def __getattr__(self, name: str):
        try:
            return self._dynabox.__getattr__(name)
        except AttributeError:
            raise AttributeError(f"No attribute '{name}' for module '{self.module_name}' "
                                 f"in settings file '{self.filepath.absolute()}'.")
