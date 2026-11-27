"""Formatting helpers for the command line output."""

from __future__ import annotations

from collections.abc import Sequence

from itu_t_documents.storage.queries import DocumentRecord


def print_documents(records: Sequence[DocumentRecord]) -> None:
    """Print document records as a table."""
    for record in records:
        questions = ",".join(str(number) for number in record.questions) or "-"
        sources = "; ".join(record.sources) or "-"
        print(f"{record.document_id:<32} {record.doc_type.value:<4} Q{questions:<10} {record.title[:60]:<62} {sources[:40]}")
