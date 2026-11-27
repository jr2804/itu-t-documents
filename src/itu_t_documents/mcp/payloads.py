"""The JSON payloads of a document and of a source count."""

from __future__ import annotations

from typing import Any

from itu_t_documents.storage.queries import DocumentRecord, SourceCount


def document_payload(record: DocumentRecord) -> dict[str, Any]:
    """Convert a document record into a JSON friendly payload."""
    return {
        "document_id": record.document_id,
        "type": record.doc_type.value,
        "number": record.number,
        "subtype": record.subtype,
        "title": record.title,
        "sources": list(record.sources),
        "questions": list(record.questions),
        "posted": record.posted.isoformat() if record.posted else None,
        "revision": record.revision,
        "study_group": record.study_group,
        "study_period": record.study_period,
        "meeting": record.meeting_code,
        "detail_url": record.detail_url,
    }


def source_payload(count: SourceCount) -> dict[str, Any]:
    """Convert a source count into a JSON friendly payload."""
    return {
        "source": count.source,
        "documents": count.count,
        "contributions": count.contributions,
        "temporary_documents": count.temporary_documents,
        "meetings": list(count.meetings),
    }
