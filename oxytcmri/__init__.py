# __init__.py

from dynaconf import Dynaconf

# Create an instance of Dynaconf for managing settings.
# It loads configuration from 'settings.toml' and '.secrets.toml'.
# The `merge_enabled` option allows merging sections from multiple files.
settings = Dynaconf(
    settings_files=["settings.toml", ".secrets.toml"],
    merge_enabled=True
)
