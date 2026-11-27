"""The contracts of the package and the rules that keep them honest."""

from __future__ import annotations

import re
from pathlib import Path

import itu_t_documents
from itu_t_documents.api import ItuDocuments
from itu_t_documents.catalogue import ItuCatalogue
from itu_t_documents.interfaces import CatalogueHost, DocumentHost

GUARDED_IMPORT = re.compile(r"^\s*(from typing import TYPE_CHECKING|if (typing\.)?TYPE_CHECKING:)", re.MULTILINE)


def test_the_package_never_guards_an_import_behind_type_checking() -> None:
    """A guarded import hides a cycle instead of breaking it."""
    offenders = [str(path) for path in _sources() if GUARDED_IMPORT.search(path.read_text(encoding="utf-8"))]
    assert not offenders


def _sources() -> list[Path]:
    """The Python files of the package and of the test suite."""
    package = Path(itu_t_documents.__file__).parent
    project = package.parent.parent
    return sorted(package.rglob("*.py")) + sorted((project / "tests").rglob("*.py"))


def test_the_hosts_implement_every_member_of_their_contract() -> None:
    """A member that is not implemented would return nothing instead of failing."""
    for protocol, host in ((DocumentHost, ItuDocuments), (CatalogueHost, ItuCatalogue)):
        for name, member in vars(protocol).items():
            if name.startswith("_") or not callable(member):
                continue
            assert getattr(host, name, None) is not member, f"{host.__name__} does not implement {name}"


def test_the_contracts_name_the_members_the_operations_need() -> None:
    """The operations read the store and the client and read the ITU-T with them."""
    assert set(DocumentHost.__annotations__) == {"store", "client"}
    assert {"list_meetings", "list_questions", "fetch_documents", "fetch_document_detail"} <= set(vars(DocumentHost))
    assert {"study_groups", "structure", "current_period"} <= set(vars(CatalogueHost))
