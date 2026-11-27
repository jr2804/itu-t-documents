"""The setting sources of the configuration.

The TOML file and the secretspec manifest are two sources among the explicit
values and the environment. Their resolution is separate from the settings
model so that each module has one responsibility.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from itu_t_documents.config.paths import CONFIG_FILE_NAME, default_config_dir
from itu_t_documents.config.secretspec_source import SECRETSPEC_MANIFEST_NAME

#: Mapping of TOML sections and keys onto flat setting names.
_TOML_SECTION_MAP: dict[str, dict[str, str]] = {
    "credentials": {"username": "ties_username", "password": "ties_password"},
    "general": {
        "cache_dir": "cache_dir",
        "config_dir": "config_dir",
        "timeout": "timeout",
        "max_concurrency": "max_concurrency",
        "user_agent": "user_agent",
        "verify_tls": "verify_tls",
        "secretspec_manifest": "secretspec_manifest",
    },
}


class TomlConfigSource(PydanticBaseSettingsSource):
    """Reads settings from the TOML configuration file.

    Sections are mapped onto flat setting names by :data:`_TOML_SECTION_MAP`;
    unknown sections and keys are ignored so that the file stays extensible.
    """

    def __init__(self, settings_cls: type[BaseSettings], path: Path) -> None:
        super().__init__(settings_cls)
        self._path = path

    def __call__(self) -> dict[str, Any]:
        """Return the settings found in the configuration file."""
        if not self._path.is_file():
            return {}
        with self._path.open("rb") as handle:
            raw = tomllib.load(handle)
        values: dict[str, Any] = {}
        for section, mapping in _TOML_SECTION_MAP.items():
            section_values = raw.get(section)
            if not isinstance(section_values, dict):
                continue
            for key, setting_name in mapping.items():
                if key in section_values:
                    values[setting_name] = section_values[key]
        return values

    @staticmethod
    def get_field_value(field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Return the value of a single field; always unset for this source."""
        return None, field_name, False


class SecretspecManifestSource(PydanticBaseSettingsSource):
    """Reports the secretspec manifest that is in use.

    The source comes first in the order of the setting sources because it
    resolves the manifest from every layer at once — the explicit value, the
    environment, the configuration file and the configuration directory — and
    no other layer can disagree with the result.
    """

    def __init__(self, settings_cls: type[BaseSettings], manifest: Path | None) -> None:
        super().__init__(settings_cls)
        self._manifest = manifest

    def __call__(self) -> dict[str, Any]:
        """Return the manifest path, if one was found."""
        return {"secretspec_manifest": self._manifest}

    @staticmethod
    def get_field_value(field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Return the value of a single field; always unset for this source."""
        return None, field_name, False


def resolve_secretspec_manifest(
    explicit: str | Path | None = None,
    *,
    config_dir: Path | None = None,
    settings_cls: type[BaseSettings] | None = None,
) -> Path | None:
    """Resolve the manifest that declares the secretspec providers.

    The manifest is looked up in this order: the explicitly passed value, the
    ``ITU_SECRETSPEC_MANIFEST`` environment variable, the
    ``general.secretspec_manifest`` key of the configuration file, and the
    ``secretspec.toml`` file in the configuration directory. The last step is
    the one the package owns, so a project can keep its manifest next to the
    configuration file; secretspec itself only ever looks in the current
    directory and its parents. When nothing is found the manifest is left to
    secretspec, which discovers it on its own.
    """
    for candidate in (explicit, os.environ.get("ITU_SECRETSPEC_MANIFEST")):
        if candidate:
            return Path(str(candidate)).expanduser()
    directory = config_dir or default_config_dir()
    configured = TomlConfigSource(settings_cls or BaseSettings, directory / CONFIG_FILE_NAME)().get("secretspec_manifest")
    if configured:
        return Path(str(configured)).expanduser()
    manifest = directory / SECRETSPEC_MANIFEST_NAME
    return manifest if manifest.is_file() else None
