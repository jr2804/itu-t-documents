"""Version information for ITU-T Documents."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__title__ = "itu_t_documents"
__description__ = "Download and query ITU-T meeting documents (contributions, temporary documents, collective letters, reports) via API, CLI and MCP."
__author__ = "Jan.Reimes"
__email__ = "github@jan-reimes.de"
__license__ = "MIT"
__copyright__ = "Copyright 2026, Jan.Reimes"

try:
    __version__ = version("itu-t-documents")
except PackageNotFoundError:
    # A source tree without the package metadata has no version to report.
    __version__ = "0.0.0"
