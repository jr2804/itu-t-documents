"""Authentication against the ITU-T document management system."""

from __future__ import annotations

from itu_doc_downloader.auth.ties import AuthenticationError, TiesAuthenticator

__all__ = ["AuthenticationError", "TiesAuthenticator"]
