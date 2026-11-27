"""The paths of the configuration and the cache.

The directory and file names are resolved before the settings themselves
exist, so they live beside the settings model instead of inside it.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Default directory holding the configuration file.
DEFAULT_CONFIG_DIR = Path("~/.config/itu-t-documents")

#: Default directory holding cached documents and the metadata database.
DEFAULT_CACHE_DIR = Path("~/.cache/itu-t-documents")

#: Name of the configuration file inside :data:`DEFAULT_CONFIG_DIR`.
CONFIG_FILE_NAME = "config.toml"


def default_config_file() -> Path:
    """Return the path of the configuration file in the user's config directory."""
    return default_config_dir() / CONFIG_FILE_NAME


def default_config_dir() -> Path:
    """Return the directory holding the configuration file.

    The directory can be moved with the ``ITU_CONFIG_DIR`` environment
    variable, which is read here because the setting sources are built before
    the settings themselves are resolved.
    """
    return resolve_config_dir()


def resolve_config_dir(explicit: str | Path | None = None) -> Path:
    """Resolve the directory holding the configuration file.

    The directory is looked up in this order: the explicitly passed value and
    the ``ITU_CONFIG_DIR`` environment variable. When neither is set the
    package uses :data:`DEFAULT_CONFIG_DIR`.
    """
    for candidate in (explicit, os.environ.get("ITU_CONFIG_DIR")):
        if candidate:
            return Path(str(candidate)).expanduser()
    return DEFAULT_CONFIG_DIR.expanduser()
