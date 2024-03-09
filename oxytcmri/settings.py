from pathlib import Path
from dynaconf import Dynaconf
from dynaconf.utils.boxing import DynaBox


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

    def __setattr__(self, name: str, value):
        if name in ["filepath", "_dynaconf_settings"]:
            super().__setattr__(name, value)
        else:
            setattr(self._dynaconf_settings, name, value)


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

    def __setattr__(self, name: str, value):
        if name in ["module_name", "_dynabox", "filepath"]:
            super().__setattr__(name, value)
        else:
            self._dynabox[name] = value
