"""Configuration and credential resolution.

Settings are resolved from four layers, highest priority first:

1. explicit values passed to :class:`Settings`,
2. environment variables prefixed with ``ITU_`` (``ITU_TIES_USERNAME``,
   ``ITU_TIES_PASSWORD``, ``ITU_CACHE_DIR``, …),
3. the TOML configuration file ``~/.config/itu-t-documents/config.toml``,
4. a `secretspec <https://github.com/cachix/secretspec>`_ provider, when the
   optional ``secretspec`` extra is installed — see
   :mod:`itu_t_documents.config.secretspec_source`.

The configuration file may hold credentials as well as globally stored
values:

.. code-block:: toml

    [credentials]
    username = "you@example.org"
    password = "secret"

    [general]
    cache_dir = "~/.cache/itu-t-documents"
    timeout = 30
    secretspec_manifest = "~/.config/itu-t-documents/secretspec.toml"

The manifest that declares the secretspec providers is a setting of its own:
``secretspec_manifest``, read from ``ITU_SECRETSPEC_MANIFEST`` or from the
``general.secretspec_manifest`` key of the configuration file. When it is
unset, the package looks for a ``secretspec.toml`` in its configuration
directory and leaves the rest to secretspec, which discovers the manifest in
the current directory and its parents.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any, cast

from pydantic import Field, SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from itu_t_documents.config.secretspec_source import (
    SECRETSPEC_MANIFEST_NAME,
    SecretspecConfigSource,
)

#: Default directory holding the configuration file.
DEFAULT_CONFIG_DIR = Path("~/.config/itu-t-documents")

#: Default directory holding cached documents and the metadata database.
DEFAULT_CACHE_DIR = Path("~/.cache/itu-t-documents")

#: Name of the configuration file inside :data:`DEFAULT_CONFIG_DIR`.
CONFIG_FILE_NAME = "config.toml"

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


class Settings(BaseSettings):
    """Runtime configuration of the ITU-T documents."""

    model_config = SettingsConfigDict(
        env_prefix="ITU_",
        extra="ignore",
    )

    ties_username: str | None = Field(
        default=None,
        description="TIES account name or e-mail address used to authenticate against the ITU-T DMS.",
    )
    ties_password: SecretStr | None = Field(
        default=None,
        description="TIES account password.",
    )
    cache_dir: Path = Field(
        default=DEFAULT_CACHE_DIR,
        description="Directory holding cached documents and the metadata database.",
    )
    config_dir: Path = Field(
        default=DEFAULT_CONFIG_DIR,
        description="Directory holding the configuration file.",
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        description="HTTP request timeout in seconds.",
    )
    max_concurrency: int = Field(
        default=4,
        ge=1,
        description="Maximum number of concurrent HTTP requests.",
    )
    user_agent: str = Field(
        default=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        description="User agent sent with every request.",
    )
    verify_tls: bool = Field(
        default=True,
        description="Whether TLS certificates are verified.",
    )
    secretspec_manifest: Path | None = Field(
        default=None,
        description=(
            "Manifest that declares the secretspec providers; unset leaves the manifest to secretspec, "
            "which discovers it in the current directory and its parents."
        ),
    )

    @property
    def config_file(self) -> Path:
        """Path of the TOML configuration file."""
        return self.config_dir.expanduser() / CONFIG_FILE_NAME

    @property
    def resolved_cache_dir(self) -> Path:
        """The cache directory with ``~`` expanded."""
        return self.cache_dir.expanduser()

    def has_credentials(self) -> bool:
        """Whether both a TIES user name and a password are available."""
        return bool(self.ties_username) and self.ties_password is not None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Order the setting sources: manifest, explicit values, environment, TOML file, secretspec."""
        explicit = cast(InitSettingsSource, init_settings).init_kwargs.get("secretspec_manifest")
        manifest = resolve_secretspec_manifest(explicit)
        return (
            SecretspecManifestSource(settings_cls, manifest),
            init_settings,
            env_settings,
            TomlConfigSource(settings_cls, default_config_file()),
            file_secret_settings,
            SecretspecConfigSource(settings_cls, manifest=manifest),
        )


def resolve_secretspec_manifest(explicit: str | Path | None = None) -> Path | None:
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
    configured = TomlConfigSource(Settings, default_config_file())().get("secretspec_manifest")
    if configured:
        return Path(str(configured)).expanduser()
    manifest = default_config_dir() / SECRETSPEC_MANIFEST_NAME
    return manifest if manifest.is_file() else None


def default_config_file() -> Path:
    """Return the path of the configuration file in the user's config directory."""
    return default_config_dir() / CONFIG_FILE_NAME


def default_config_dir() -> Path:
    """Return the directory holding the configuration file.

    The directory can be moved with the ``ITU_CONFIG_DIR`` environment
    variable, which is read here because the setting sources are built before
    the settings themselves are resolved.
    """
    config_dir = os.environ.get("ITU_CONFIG_DIR")
    return Path(config_dir).expanduser() if config_dir else DEFAULT_CONFIG_DIR.expanduser()
