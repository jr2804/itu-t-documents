"""Smoke tests for the generated package scaffold."""

from __future__ import annotations


import runpy
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
from cyclopts.types import StdioPath


import itu_doc_downloader
from itu_doc_downloader import __about__


from itu_doc_downloader.cli import app as cli_app
from itu_doc_downloader.cli import commands



def test_package_exposes_version() -> None:
    """Importing the package and its metadata module must work."""
    assert itu_doc_downloader.__version__
    assert __about__.__title__ == "itu_doc_downloader"



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


def test_default_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The default command prints the welcome message."""
    commands.default()

    assert "Welcome" in capsys.readouterr().out


def test_greet_command(capsys: pytest.CaptureFixture[str]) -> None:
    """The greet command prints the supplied name."""
    commands.greet("Ada")

    out = capsys.readouterr().out
    assert "Hello, Ada!" in out
    assert "Cache: enabled" in out


def test_greet_command_reads_names_and_writes_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The greet command handles an input file and an output path."""
    names = StdioPath(tmp_path / "names.txt")
    names.write_text("Ada\nBob\n", encoding="utf-8")
    output = tmp_path / "greeting.txt"

    commands.greet("ignored", input_file=names, output_file=str(output), cache=False)

    out = capsys.readouterr().out
    assert "Hello, Ada!" in out
    assert "Hello, Bob!" in out
    assert f"Output file: {output}" in out
    assert "Cache: disabled" in out


def test_add_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The add command prints the sum and can write it to a file."""
    commands.add(1.5, 2.5)

    assert "The sum of 1.5 and 2.5 is 4.0" in capsys.readouterr().out

    output = tmp_path / "sum.txt"
    commands.add(1, 2, output_file=str(output))

    assert output.read_text(encoding="utf-8") == "3"


