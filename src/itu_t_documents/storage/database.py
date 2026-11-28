"""SQLite metadata store.

The store keeps the metadata of every document, meeting and question that has
been seen. It lives in the per-user cache directory, so a second run of the
tool answers questions without contacting the ITU-T web site again.

:class:`MetadataStore` opens the database and offers one method per write.
The tables live in ``storage/tables.py``, the code that fills them in
``storage/documents.py`` and ``storage/questions.py``, what the store
answers is asked in ``storage/queries.py``, and the migrations that bring a
database of an older release up to the schema of the code live in
``storage/migrations.py``.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from itu_t_documents.config.settings import Settings
from itu_t_documents.models.metadata import DocumentMetadata
from itu_t_documents.models.questions import Question
from itu_t_documents.storage.documents import write_detail, write_document
from itu_t_documents.storage.migrations import migrate
from itu_t_documents.storage.questions import write_question
from itu_t_documents.storage.tables import DocumentRow

#: Name of the SQLite database inside the cache directory.
DATABASE_FILE = "metadata.db"


class MetadataStore:
    """The SQLite metadata store of the ITU-T documents."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Open the store.

        Args:
            settings: The configuration to use. Defaults to the resolved
                environment and configuration file settings.
        """
        self.settings = settings or Settings()
        self.cache_dir = self.settings.resolved_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.cache_dir / DATABASE_FILE
        self.engine = create_engine(f"sqlite:///{self.database_path}")
        SQLModel.metadata.create_all(self.engine)
        # A database of an older release has the tables but not every column:
        # "create_all" only creates the missing tables. The migrations bring
        # such a database up to the schema of the code.
        migrate(self.engine)

    def session(self) -> Session:
        """Return a new database session."""
        return Session(self.engine)

    def close(self) -> None:
        """Release the database connections held by the store."""
        self.engine.dispose()

    def store_document(self, metadata: DocumentMetadata) -> DocumentRow:
        """Insert or update a document and its links.

        Args:
            metadata: The metadata of the document, as a listing tells it.

        Returns:
            The stored row.
        """
        with self.session() as session:
            return write_document(session, metadata)

    def store_detail(self, detail: DocumentMetadata) -> DocumentRow:
        """Store what the detail page of a document says.

        The detail page gives the title and the renditions of a document. What
        a listing said — the posting date, the revision, the sources, the
        questions and the meeting — is unknown to it, so that is kept. A
        document that no listing told of yet is stored as its detail page
        describes it.

        Args:
            detail: The metadata read from the detail page of the document.

        Returns:
            The stored row.
        """
        with self.session() as session:
            return write_detail(session, detail)

    def store_question(self, question: Question, period_label: str) -> None:
        """Insert or update a question under study and its people.

        Args:
            question: The question to store.
            period_label: The study period the question belongs to.
        """
        with self.session() as session:
            write_question(session, question, period_label)

    def count_documents(self) -> int:
        """Return the number of stored documents."""
        with self.session() as session:
            return len(session.exec(select(DocumentRow)).all())
