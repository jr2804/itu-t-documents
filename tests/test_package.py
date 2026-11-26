"""Smoke tests for the package scaffold and its CLI wiring."""

from __future__ import annotations

import runpy
from importlib.metadata import PackageNotFoundError

import pytest

import itu_doc_downloader
from itu_doc_downloader import __about__
from itu_doc_downloader.cli import app as cli_app
from itu_doc_downloader.cli import commands


def test_package_exposes_version() -> None:
    """Importing the package and its metadata module must work."""
    assert itu_doc_downloader.__version__
    assert __about__.__title__ == "itu_doc_downloader"


def test_package_exports_the_public_api() -> None:
    """The package exports the objects of the public API."""
    assert itu_doc_downloader.ItuDocuments.__name__ == "ItuDocuments"
    assert itu_doc_downloader.DocumentRef.__name__ == "DocumentRef"
    assert itu_doc_downloader.DocType.CONTRIBUTION == "C"


def test_cli_version_uses_metadata() -> None:
    """The CLI version callback reads installed package metadata."""
    assert cli_app._get_version()


def test_cli_version_falls_back_without_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI still reports a version when package metadata is unavailable."""

    def missing(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(cli_app, "version", missing)

    assert cli_app._get_version() == "0.0.0"


def test_cli_main_invokes_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """The console entry point delegates to the Cyclopts app."""
    invoked: list[bool] = []
    monkeypatch.setattr(cli_app, "app", lambda: invoked.append(True))

    cli_app.main()

    assert invoked == [True]


def test_dunder_main_invokes_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """`python -m itu_doc_downloader` runs the CLI entry point."""
    invoked: list[bool] = []
    monkeypatch.setattr(cli_app, "main", lambda: invoked.append(True))

    runpy.run_module("itu_doc_downloader", run_name="__main__")

    assert invoked == [True]


def test_cli_registers_every_command() -> None:
    """Every command of the package is registered with the CLI."""
    registered = set(cli_app.app._registered_commands)

    assert {"auth", "documents", "download", "mcp", "meetings", "questions", "sync"} <= registered


def test_default_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The default command prints the welcome message."""
    commands.default()

    assert "itu-doc-downloader" in capsys.readouterr().out
