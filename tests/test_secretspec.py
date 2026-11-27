"""Tests for the optional secretspec credential source."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from itu_t_documents.config.secretspec_source import (
    DEFAULT_SECRETSPEC_PROVIDER,
    SecretspecConfigSource,
    secretspec_credentials,
)
from itu_t_documents.config.settings import CONFIG_FILE_NAME, Settings


class _FakeSecretSpecError(Exception):
    """Stand-in for ``secretspec.SecretSpecError``."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class _FakeResolved:
    """Stand-in for ``secretspec.Resolved``."""

    def __init__(self, secrets: dict[str, str | None]) -> None:
        self.secrets = secrets

    def fields(self) -> dict[str, str | None]:
        """Return the flat secret map."""
        return dict(self.secrets)


class _FakeBuilder:
    """Stand-in for the secretspec builder."""

    def __init__(self, result: _FakeResolved | Exception, calls: dict[str, Any]) -> None:
        self._result = result
        self._calls = calls

    def with_provider(self, provider: str) -> _FakeBuilder:
        """Record the provider."""
        self._calls["provider"] = provider
        return self

    def with_reason(self, reason: str) -> _FakeBuilder:
        """Record the reason."""
        self._calls["reason"] = reason
        return self

    def with_path(self, path: str) -> _FakeBuilder:
        """Record the manifest."""
        self._calls["path"] = path
        return self

    def load(self) -> _FakeResolved:
        """Return the configured result or raise it."""
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _install_fake_secretspec(monkeypatch: pytest.MonkeyPatch, result: _FakeResolved | Exception, calls: dict[str, Any]) -> None:
    """Register a fake ``secretspec`` module for the duration of a test."""
    module = types.ModuleType("secretspec")
    module.__dict__.update(
        {
            "SecretSpecError": _FakeSecretSpecError,
            "SecretSpec": types.SimpleNamespace(builder=lambda: _FakeBuilder(result, calls)),
        },
    )
    monkeypatch.setitem(sys.modules, "secretspec", module)


def _remove_secretspec(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``import secretspec`` fail as if the optional extra is not installed."""
    monkeypatch.setitem(sys.modules, "secretspec", None)


@pytest.fixture(autouse=True)
def _isolated_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the tests away from the configuration directory of the user."""
    monkeypatch.setenv("ITU_CONFIG_DIR", str(tmp_path / "isolated-config"))


def test_secretspec_not_installed_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the optional dependency the source contributes nothing."""
    _remove_secretspec(monkeypatch)

    assert secretspec_credentials() is None


def test_credentials_are_read_from_the_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """The declared secrets are returned as a user name and a password."""
    calls: dict[str, Any] = {}
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        calls,
    )

    credentials = secretspec_credentials()

    assert credentials is not None
    username, password = credentials
    assert username == "spec@example.org"
    assert isinstance(password, SecretStr)
    assert password.get_secret_value() == "spec-secret"
    assert calls["provider"] == DEFAULT_SECRETSPEC_PROVIDER
    assert calls["reason"]


def test_provider_name_is_passed_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """A custom provider name or URI overrides the default."""
    calls: dict[str, Any] = {}
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        calls,
    )

    assert secretspec_credentials("dotenv://.env.local") is not None
    assert calls["provider"] == "dotenv://.env.local"


def test_manifest_is_passed_to_secretspec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An explicit manifest is handed over to secretspec as a string."""
    calls: dict[str, Any] = {}
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        calls,
    )

    assert secretspec_credentials(manifest=tmp_path / "secretspec.toml") is not None
    assert calls["path"] == str(tmp_path / "secretspec.toml")


def test_without_a_manifest_the_discovery_is_left_to_secretspec(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a manifest secretspec looks for one on its own."""
    calls: dict[str, Any] = {}
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        calls,
    )

    assert secretspec_credentials() is not None
    assert "path" not in calls


def test_missing_manifest_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A manifest that does not exist disables the source."""
    _install_fake_secretspec(monkeypatch, _FakeSecretSpecError("no_manifest"), {})

    assert secretspec_credentials(manifest=tmp_path / "absent.toml") is None


def test_unreadable_manifest_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A manifest that cannot be read disables the source."""
    _install_fake_secretspec(monkeypatch, OSError("IO error: Is a directory"), {})

    assert secretspec_credentials(manifest=tmp_path) is None


def test_resolution_error_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """A provider that cannot be resolved is not an error for the caller."""
    _install_fake_secretspec(monkeypatch, _FakeSecretSpecError("no_manifest"), {})

    assert secretspec_credentials() is None


def test_missing_password_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both declared secrets must resolve to a non-empty value."""
    _install_fake_secretspec(monkeypatch, _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": None}), {})

    assert secretspec_credentials() is None


def test_missing_username_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """A declared but unset user name disables the source."""
    _install_fake_secretspec(monkeypatch, _FakeResolved({"ITU_TIES_USERNAME": "", "ITU_TIES_PASSWORD": "spec-secret"}), {})

    assert secretspec_credentials() is None


def test_source_returns_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pydantic source maps the credentials onto the setting names."""
    calls: dict[str, Any] = {}
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        calls,
    )

    values = SecretspecConfigSource(Settings)()

    assert values["ties_username"] == "spec@example.org"
    assert isinstance(values["ties_password"], SecretStr)
    assert values["ties_password"].get_secret_value() == "spec-secret"


def test_source_returns_nothing_without_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unconfigured provider contributes no settings at all."""
    _install_fake_secretspec(monkeypatch, _FakeSecretSpecError("provider_not_found"), {})

    assert SecretspecConfigSource(Settings)() == {}


def test_source_hands_the_manifest_to_the_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The pydantic source passes the manifest on to secretspec."""
    calls: dict[str, Any] = {}
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        calls,
    )

    values = SecretspecConfigSource(Settings, manifest=tmp_path / "secretspec.toml")()

    assert values["ties_username"] == "spec@example.org"
    assert calls["path"] == str(tmp_path / "secretspec.toml")


def test_settings_hand_the_manifest_to_the_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The manifest resolved by the settings reaches secretspec."""
    monkeypatch.setenv("ITU_SECRETSPEC_MANIFEST", str(tmp_path / "secretspec.toml"))
    calls: dict[str, Any] = {}
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        calls,
    )

    settings = Settings()

    assert settings.secretspec_manifest == tmp_path / "secretspec.toml"
    assert settings.ties_username == "spec@example.org"
    assert calls["path"] == str(tmp_path / "secretspec.toml")


def test_source_field_value_is_unset() -> None:
    """The per-field accessor never contributes a value."""
    source = SecretspecConfigSource(Settings)
    field = Settings.model_fields["ties_username"]

    assert source.get_field_value(field, "ties_username") == (None, "ties_username", False)


def test_settings_falls_back_to_secretspec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Without environment or file credentials the secretspec provider applies."""
    monkeypatch.setenv("ITU_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "itu_t_documents.config.settings.default_config_file",
        lambda: tmp_path / "absent.toml",
    )
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        {},
    )

    settings = Settings()

    assert settings.ties_username == "spec@example.org"
    assert settings.ties_password is not None
    assert settings.ties_password.get_secret_value() == "spec-secret"
    assert settings.has_credentials()


def test_environment_wins_over_secretspec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The environment variables keep the highest priority."""
    monkeypatch.setenv("ITU_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ITU_TIES_USERNAME", "env@example.org")
    monkeypatch.setenv("ITU_TIES_PASSWORD", "env-secret")
    monkeypatch.setattr(
        "itu_t_documents.config.settings.default_config_file",
        lambda: tmp_path / "absent.toml",
    )
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        {},
    )

    settings = Settings()

    assert settings.ties_username == "env@example.org"
    assert settings.ties_password is not None
    assert settings.ties_password.get_secret_value() == "env-secret"


def test_configuration_file_wins_over_secretspec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The TOML file sits between the environment and secretspec."""
    monkeypatch.setenv("ITU_CACHE_DIR", str(tmp_path))
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / CONFIG_FILE_NAME).write_text(
        '[credentials]\nusername = "file@example.org"\npassword = "file-secret"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "itu_t_documents.config.settings.default_config_file",
        lambda: config_dir / CONFIG_FILE_NAME,
    )
    _install_fake_secretspec(
        monkeypatch,
        _FakeResolved({"ITU_TIES_USERNAME": "spec@example.org", "ITU_TIES_PASSWORD": "spec-secret"}),
        {},
    )

    settings = Settings()

    assert settings.ties_username == "file@example.org"
    assert settings.ties_password is not None
    assert settings.ties_password.get_secret_value() == "file-secret"
