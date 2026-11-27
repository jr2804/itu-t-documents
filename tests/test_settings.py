"""Tests for the layered configuration and credential resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic.fields import FieldInfo

from itu_t_documents.config.secretspec_source import SECRETSPEC_MANIFEST_NAME
from itu_t_documents.config.settings import (
    CONFIG_FILE_NAME,
    SecretspecManifestSource,
    Settings,
    TomlConfigSource,
    default_config_dir,
    default_config_file,
)


@pytest.fixture(autouse=True)
def _isolated_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the tests away from the configuration directory of the user."""
    monkeypatch.setenv("ITU_CONFIG_DIR", str(tmp_path / "isolated-config"))


def test_defaults(monkeypatch, tmp_path: Path) -> None:
    """Without any configuration the documented defaults apply."""
    monkeypatch.setenv("ITU_CACHE_DIR", str(tmp_path))
    settings = Settings()

    assert settings.ties_username is None
    assert settings.ties_password is None
    assert not settings.has_credentials()
    assert settings.timeout == 30.0
    assert settings.max_concurrency == 4


def test_credentials_from_environment(monkeypatch, tmp_path: Path) -> None:
    """The TIES credentials are read from the environment."""
    monkeypatch.setenv("ITU_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ITU_TIES_USERNAME", "you@example.org")
    monkeypatch.setenv("ITU_TIES_PASSWORD", "secret")

    settings = Settings()

    assert settings.ties_username == "you@example.org"
    assert settings.ties_password is not None
    assert settings.ties_password.get_secret_value() == "secret"
    assert settings.has_credentials()


def test_configuration_file(monkeypatch, tmp_path: Path) -> None:
    """The configuration file holds credentials and global values."""
    monkeypatch.setenv("ITU_CACHE_DIR", str(tmp_path))
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / CONFIG_FILE_NAME).write_text(
        '[credentials]\nusername = "file@example.org"\npassword = "file-secret"\n\n[general]\ntimeout = 90\nmax_concurrency = 8\n',
        encoding="utf-8",
    )
    settings = Settings(config_dir=config_dir)

    assert settings.ties_username == "file@example.org"
    assert settings.ties_password is not None
    assert settings.ties_password.get_secret_value() == "file-secret"
    assert settings.timeout == 90.0
    assert settings.max_concurrency == 8


def test_environment_overrides_the_configuration_file(monkeypatch, tmp_path: Path) -> None:
    """The environment wins over the configuration file."""
    monkeypatch.setenv("ITU_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ITU_TIES_USERNAME", "env@example.org")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / CONFIG_FILE_NAME).write_text(
        '[credentials]\nusername = "file@example.org"\n',
        encoding="utf-8",
    )
    settings = Settings(config_dir=config_dir)

    assert settings.ties_username == "env@example.org"


def test_configuration_directory_can_be_moved(monkeypatch, tmp_path: Path) -> None:
    """The configuration directory can be moved with an environment variable."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / CONFIG_FILE_NAME).write_text('[credentials]\nusername = "file@example.org"\n', encoding="utf-8")
    monkeypatch.setenv("ITU_CONFIG_DIR", str(config_dir))

    settings = Settings()

    assert settings.ties_username == "file@example.org"
    assert settings.config_file == config_dir / CONFIG_FILE_NAME


def test_missing_configuration_file_is_ignored(monkeypatch, tmp_path: Path) -> None:
    """A missing configuration file is not an error."""
    monkeypatch.setattr(
        "itu_t_documents.config.settings.default_config_file",
        lambda: tmp_path / "absent.toml",
    )

    assert TomlConfigSource(Settings, tmp_path / "absent.toml")() == {}


def test_cache_directory_is_expanded(monkeypatch, tmp_path: Path) -> None:
    """The cache directory is resolved to an absolute path."""
    monkeypatch.setenv("ITU_CACHE_DIR", "~/cache")

    settings = Settings()

    assert settings.resolved_cache_dir == Path("~/cache").expanduser()


def test_secretspec_manifest_from_the_environment(monkeypatch, tmp_path: Path) -> None:
    """The manifest of the secretspec provider is read from the environment."""
    monkeypatch.setenv("ITU_SECRETSPEC_MANIFEST", str(tmp_path / "secretspec.toml"))

    settings = Settings()

    assert settings.secretspec_manifest == tmp_path / "secretspec.toml"


def test_secretspec_manifest_from_the_configuration_file(monkeypatch, tmp_path: Path) -> None:
    """The configuration file may hold the manifest of the secretspec provider."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / CONFIG_FILE_NAME).write_text(
        '[general]\nsecretspec_manifest = "/srv/secretspec.toml"\n',
        encoding="utf-8",
    )
    settings = Settings(config_dir=config_dir)

    assert settings.secretspec_manifest == Path("/srv/secretspec.toml")


def test_environment_manifest_wins_over_the_configuration_file(monkeypatch, tmp_path: Path) -> None:
    """The environment wins over the configuration file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / CONFIG_FILE_NAME).write_text(
        '[general]\nsecretspec_manifest = "/srv/secretspec.toml"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("ITU_SECRETSPEC_MANIFEST", str(tmp_path / "secretspec.toml"))

    settings = Settings(config_dir=config_dir)

    assert settings.secretspec_manifest == tmp_path / "secretspec.toml"


def test_explicit_manifest_wins_over_the_environment(monkeypatch, tmp_path: Path) -> None:
    """A manifest passed to the settings beats every other layer."""
    monkeypatch.setenv("ITU_SECRETSPEC_MANIFEST", str(tmp_path / "secretspec.toml"))

    settings = Settings(secretspec_manifest=tmp_path / "explicit.toml")

    assert settings.secretspec_manifest == tmp_path / "explicit.toml"


def test_manifest_in_the_configuration_directory_is_used(monkeypatch, tmp_path: Path) -> None:
    """The package looks for a manifest in the configuration directory it owns."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    manifest = config_dir / SECRETSPEC_MANIFEST_NAME
    manifest.write_text('[project]\nname = "itu-t-documents"\n', encoding="utf-8")
    monkeypatch.setenv("ITU_CONFIG_DIR", str(config_dir))

    settings = Settings()

    assert settings.secretspec_manifest == manifest


def test_without_a_manifest_the_discovery_is_left_to_secretspec(monkeypatch, tmp_path: Path) -> None:
    """Without a manifest anywhere secretspec discovers it on its own."""
    monkeypatch.setenv("ITU_CONFIG_DIR", str(tmp_path / "absent"))

    settings = Settings()

    assert settings.secretspec_manifest is None


def test_manifest_source_field_value_is_unset() -> None:
    """The per-field accessor of the manifest source never contributes a value."""
    source = SecretspecManifestSource(Settings, None)
    field = Settings.model_fields["secretspec_manifest"]

    assert source.get_field_value(field, "secretspec_manifest") == (None, "secretspec_manifest", False)


def test_the_default_configuration_directory_follows_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The directory and the file inside it follow ITU_CONFIG_DIR."""
    monkeypatch.setenv("ITU_CONFIG_DIR", str(tmp_path))

    assert default_config_dir() == tmp_path
    assert default_config_file() == tmp_path / CONFIG_FILE_NAME


def test_settings_source_reports_unset_fields() -> None:
    """The TOML source never sets a field on its own."""
    source = TomlConfigSource(Settings, Path(__file__))

    value, name, complex_ = source.get_field_value(FieldInfo(annotation=int), "timeout")

    assert value is None
    assert name == "timeout"
    assert not complex_
