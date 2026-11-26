"""Tests for the layered configuration and credential resolution."""

from __future__ import annotations

from pathlib import Path

from itu_doc_downloader.config.settings import CONFIG_FILE_NAME, Settings, TomlConfigSource


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
    monkeypatch.setattr(
        "itu_doc_downloader.config.settings.default_config_file",
        lambda: config_dir / CONFIG_FILE_NAME,
    )

    settings = Settings()

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
    monkeypatch.setattr(
        "itu_doc_downloader.config.settings.default_config_file",
        lambda: config_dir / CONFIG_FILE_NAME,
    )

    settings = Settings()

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
        "itu_doc_downloader.config.settings.default_config_file",
        lambda: tmp_path / "absent.toml",
    )

    assert TomlConfigSource(Settings, tmp_path / "absent.toml")() == {}


def test_cache_directory_is_expanded(monkeypatch, tmp_path: Path) -> None:
    """The cache directory is resolved to an absolute path."""
    monkeypatch.setenv("ITU_CACHE_DIR", "~/cache")

    settings = Settings()

    assert settings.resolved_cache_dir == Path("~/cache").expanduser()
