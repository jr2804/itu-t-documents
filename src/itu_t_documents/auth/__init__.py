"""Authentication against the ITU-T document management system."""

from __future__ import annotations

from itu_t_documents.auth.ties import AuthenticationError, TiesAuthenticator

__all__ = ["AuthenticationError", "TiesAuthenticator"]
