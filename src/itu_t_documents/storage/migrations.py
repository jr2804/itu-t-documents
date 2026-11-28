"""The migrations of the metadata store.

The store is a cache: it may have been written by an older release. A new
release adds a column, and SQLite cannot add a column to a table that
exists — ``SQLModel.metadata.create_all`` only creates the missing tables.
The migrations below bring such a database up to the schema of the code.

The version of the schema is kept in the header of the SQLite file
(``PRAGMA user_version``). A database without that version was written
before the migrations existed; every migration is applied to it and each one
checks itself, so a column that is already there is left alone.

A migration that changes something else than a column — a table that is
renamed, a value that is backfilled — does not fit this shape. It needs a
step of its own that is written for what it does.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Connection, Engine


@dataclass(frozen=True)
class Migration:
    """One step of the schema of the metadata store."""

    version: int
    """The version of the schema the step leads to."""

    table: str
    """The table the step changes."""

    column: str
    """The column the step adds."""

    definition: str
    """The SQL definition of the column, e.g. ``INTEGER``."""

    description: str
    """What the step does, in a sentence."""


#: The migrations of the store, in the order they are applied. The version of
#: a migration is the version of the schema it leads to; a step is only ever
#: applied once.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        table="document_file",
        column="revision",
        definition="INTEGER",
        description="The revision of a rendition, added in 2026.11.3.",
    ),
)

#: The version of the schema the code expects.
SCHEMA_VERSION = len(MIGRATIONS)


def migrate(engine: Engine) -> None:
    """Bring the database of the store up to the schema of the code.

    A database that was written by a newer release is left alone: its schema
    is not known here, and the code does not have to understand it to read
    it.

    Args:
        engine: The engine of the SQLite database of the store.
    """
    with engine.begin() as connection:
        version = _schema_version(connection)
        if version >= SCHEMA_VERSION:
            return
        for migration in MIGRATIONS:
            if migration.version > version:
                _add_column(connection, migration)
        connection.exec_driver_sql(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _schema_version(connection: Connection) -> int:
    """Return the version of the schema the database was written with.

    Args:
        connection: The connection to the database.

    Returns:
        The version, or ``0`` for a database that was written before the
        migrations existed.
    """
    return int(connection.exec_driver_sql("PRAGMA user_version").scalar() or 0)


def _add_column(connection: Connection, migration: Migration) -> None:
    """Add the column of a migration, unless the table already has it.

    Args:
        connection: The connection to the database.
        migration: The migration to apply.
    """
    if _has_column(connection, migration.table, migration.column):
        return
    connection.exec_driver_sql(f"ALTER TABLE {migration.table} ADD COLUMN {migration.column} {migration.definition}")


def _has_column(connection: Connection, table: str, column: str) -> bool:
    """Whether a table of the database has a column.

    Args:
        connection: The connection to the database.
        table: The name of the table.
        column: The name of the column.

    Returns:
        Whether the table has the column.
    """
    rows = connection.exec_driver_sql(f"PRAGMA table_info({table})").all()
    return any(row[1] == column for row in rows)
