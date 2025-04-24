"""
This module provides classes for managing application settings.

The `Settings` class encapsulates the Dynaconf settings object and provides a clear interface for accessing and
modifying settings. It allows for easy access and modification of settings using attribute-style access.

The `ModuleSettings` class is a helper class within `Settings`. It handles the settings of individual modules, providing
 attribute-style access to the module's settings.

# Example

Suppose you have a settings file `tests-data/test_settings.toml` with the following content:

```toml
[database]
url = "sqlite:///test-data/test.db"
```

You can then use the `Settings` class to access the settings as follows:

    >>> settings = Settings("tests-data/test_settings.toml")
    >>> print(settings.database.url)
    sqlite:///test-data/test.db

"""

from pathlib import Path

import toml
from dynaconf import Dynaconf  # type: ignore[import-untyped]
from dynaconf.utils.boxing import DynaBox  # type: ignore[import-untyped]


class Settings:
    """
    A class to manage application settings.

    This class encapsulates the Dynaconf settings object and provides a clear interface for accessing and modifying
    settings.

    Attributes
    ----------
    filepath : Path
        The path to the settings file.
    _dynaconf_settings : Dynaconf
        The Dynaconf settings object.

    Methods
    -------
    __getattr__(name: str)
        Retrieve the value of the attribute with the given name.
    __setattr__(name: str, value)
        Set the value of the attribute with the given name.

    Examples
    --------
    >>> settings = Settings("tests-data/test_settings.toml")
    >>> print(settings.database.url)
    sqlite:///test-data/test.db
    """

    def __init__(self, filename: str):
        """
        Constructs all the necessary attributes for the Settings object.

        Parameters
        ----------
        filename : str
            The path to the settings file.

        Raises
        ------
        FileNotFoundError
            If the settings file does not exist.
        """
        filepath = Path(filename).resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"Settings file not found: '{filename}'.")
        self.filepath = filepath
        self._dynaconf_settings = Dynaconf(settings_file=filepath)
        self.base_dir = filepath.parent

    def __getattr__(self, name: str):
        """
        Retrieve the value of the attribute with the given name.

        Parameters
        ----------
        name : str
            The name of the attribute.

        Returns
        -------
        response
            The value of the attribute.

        Raises
        ------
        AttributeError
            If the attribute does not exist.
        """
        try:
            response = self._dynaconf_settings.__getattr__(name)
            if isinstance(response, DynaBox):
                return ModuleSettings(name, response, self.filepath)
            return response
        except AttributeError:
            raise AttributeError(
                f"No module '{name}' in settings file '{self.filepath}'."
            )

    def __setattr__(self, name: str, value):
        """
        Set the value of the attribute with the given name.

        Parameters
        ----------
        name : str
            The name of the attribute.
        value
            The new value of the attribute.
        """
        if name in ["filepath", "_dynaconf_settings", "base_dir"]:
            super().__setattr__(name, value)
        else:
            setattr(self._dynaconf_settings, name, value)

    def to_toml(self, filepath: str):
        """
        Convert the settings to a string in TOML format and save it to a file.

        Returns
        -------
        str
            The settings as a TOML string.
        """
        # convert dynaconf settings as dict
        settings_dict = self._dynaconf_settings.as_dict()

        # export to toml
        with open(filepath, "w") as file:
            toml.dump(settings_dict, file)

    def __repr__(self):
        return f"Settings(filename='{self.filepath}')"

    def __str__(self):
        """
        User-friendly representation of the Settings object.
        """
        # Header
        settings_str = f"Settings(filename='{self.filepath}')\n"
        settings_str += (
            "------------------------------------------------------------------------\n"
        )

        # Convert dynaconf settings to dict
        settings_dict = self._dynaconf_settings.as_dict()

        # Convert dict to TOML string
        settings_str += toml.dumps(settings_dict).replace('"', "'")

        return settings_str


class ModuleSettings:
    """
    A helper class to handle the settings of individual modules.

    This class encapsulates the settings of a specific module and provides attribute-style access to the module's settings.

    Attributes
    ----------
    module_name : str
        The name of the module.
    _dynabox : DynaBox
        The DynaBox object that holds the actual settings.
    filepath : Path
        The path to the settings file.

    Methods
    -------
    __getattr__(name: str)
        Retrieve the value of the attribute with the given name.
    __setattr__(name: str, value)
        Set the value of the attribute with the given name.
    """

    def __init__(self, module_name: str, dynabox: DynaBox, filepath: Path):
        """
        Constructs all the necessary attributes for the ModuleSettings object.

        Parameters
        ----------
        module_name : str
            The name of the module.
        dynabox : DynaBox
            The DynaBox object that holds the actual settings.
        filepath : Path
            The path to the settings file.
        """
        self.module_name = module_name
        self._dynabox = dynabox
        self.filepath = filepath

    def __getattr__(self, name: str):
        """
        Retrieve the value of the attribute with the given name.

        Parameters
        ----------
        name : str
            The name of the attribute.

        Returns
        -------
        response
            The value of the attribute.
        """
        try:
            return self._dynabox.__getattr__(name)
        except AttributeError:
            raise AttributeError(
                f"No attribute '{name}' for module '{self.module_name}' "
                f"in settings file '{self.filepath}'."
            )

    def __setattr__(self, name: str, value):
        """
        Set the value of the attribute with the given name.

        Parameters
        ----------
        name : str
            The name of the attribute.
        value
            The new value of the attribute.
        """
        if name in ["module_name", "_dynabox", "filename"]:
            super().__setattr__(name, value)
        else:
            self._dynabox[name] = value

    def list_attributes(self):
        """
        List all the attributes of the module.

        Returns
        -------
        list
            A list of all the attributes of the module.
        """
        return list(self._dynabox.keys())
