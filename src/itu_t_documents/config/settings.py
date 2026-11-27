"""The runtime configuration of the ITU-T documents.

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

from pathlib import Path
from typing import cast

from pydantic import Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from itu_t_documents.config.paths import (
    CONFIG_FILE_NAME,
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG_DIR,
    default_config_dir,
    default_config_file,
    resolve_config_dir,
)
from itu_t_documents.config.secretspec_source import SecretspecConfigSource
from itu_t_documents.config.sources import (
    SecretspecManifestSource,
    TomlConfigSource,
    resolve_secretspec_manifest,
)

__all__ = [
    "CONFIG_FILE_NAME",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_CONFIG_DIR",
    "Settings",
    "TomlConfigSource",
    "default_config_dir",
    "default_config_file",
    "resolve_config_dir",
    "resolve_secretspec_manifest",
]


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
        explicit_values = cast(InitSettingsSource, init_settings).init_kwargs
        config_dir = resolve_config_dir(explicit_values.get("config_dir"))
        manifest = resolve_secretspec_manifest(explicit_values.get("secretspec_manifest"), config_dir=config_dir, settings_cls=settings_cls)
        return (
            SecretspecManifestSource(settings_cls, manifest),
            init_settings,
            env_settings,
            TomlConfigSource(settings_cls, config_dir / CONFIG_FILE_NAME),
            file_secret_settings,
            SecretspecConfigSource(settings_cls, manifest=manifest),
        )
