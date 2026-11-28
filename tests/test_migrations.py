"""Tests for the migrations of the metadata store."""

from __future__ import annotations

from pathlib import Path

from sqlmodel import select

from itu_t_documents.config.settings import Settings
from itu_t_documents.models.documents import DocumentRef
from itu_t_documents.models.metadata import DocumentFile, DocumentMetadata
from itu_t_documents.storage.database import MetadataStore
from itu_t_documents.storage.migrations import SCHEMA_VERSION
from itu_t_documents.storage.tables import DocumentFileRow


def test_a_database_of_an_older_release_gains_the_missing_column(tmp_path: Path) -> None:
    """A store written by an older release is brought up to the schema of the code."""
    store = _older_store(tmp_path)
    ref = DocumentRef.parse("T25-SG12-C-0192")

    store.store_detail(DocumentMetadata(ref=ref, files=[DocumentFile(format_code="MSW", language_code="E", url="https://www.itu.int/a.docx")]))

    with store.session() as session:
        rows = session.exec(select(DocumentFileRow)).all()

    assert [row.url for row in rows] == ["https://www.itu.int/a.docx"]
    assert [row.revision for row in rows] == [None]
    store.close()


def test_the_version_of_the_schema_is_recorded(tmp_path: Path) -> None:
    """The store records the version of the schema it wrote."""
    store = MetadataStore(Settings(cache_dir=tmp_path))

    with store.engine.connect() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar()

    assert version == SCHEMA_VERSION


def test_a_database_of_a_newer_release_is_left_alone(tmp_path: Path) -> None:
    """A database that a newer release wrote is not touched."""
    store = MetadataStore(Settings(cache_dir=tmp_path))
    with store.engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA user_version = 99")
    store.close()

    reopened = MetadataStore(Settings(cache_dir=tmp_path))

    with reopened.engine.connect() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar()

    assert version == 99


def _older_store(tmp_path: Path) -> MetadataStore:
    """Return a store whose database was written by the release before the migrations.

    The column ``document_file.revision`` was added in 2026.11.3; a database of
    an older release does not have it, and SQLite cannot add a column to a
    table that exists.
    """
    store = MetadataStore(Settings(cache_dir=tmp_path))
    with store.engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE document_file DROP COLUMN revision")
        connection.exec_driver_sql("PRAGMA user_version = 0")
    store.close()

    return MetadataStore(Settings(cache_dir=tmp_path))
