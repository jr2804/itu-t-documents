"""Optional TIES credentials from a secretspec provider.

`secretspec <https://github.com/cachix/secretspec>`_ is a declarative secrets
manager: a ``secretspec.toml`` declares which secrets an application needs and
where they are stored (keyring, 1Password, Vault, an ``.env`` file, …).

The package uses it as the *lowest* priority credential source, below the
environment variables and the configuration file. A project opts in by
declaring the two TIES secrets under the provider alias ``itu-ties``:

.. code-block:: toml

    [project]
    name = "itu-t-documents"
    revision = "1.0"

    [providers]
    itu-ties = "keyring://"

    [profiles.default]
    ITU_TIES_USERNAME = { description = "TIES account", providers = ["itu-ties"] }
    ITU_TIES_PASSWORD = { description = "TIES password", providers = ["itu-ties"] }

The secretspec SDK is an optional dependency
(``pip install itu-t-documents[secretspec]``); without it — or without a
matching provider — :func:`secretspec_credentials` returns ``None`` and the
other credential sources apply unchanged.

The manifest that declares the providers is found by secretspec itself: it
looks for a file named ``secretspec.toml`` in the current directory and its
parents. A manifest elsewhere is addressed explicitly — see
:attr:`Settings.secretspec_manifest`.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, Final

from pydantic import SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

#: Provider alias the TIES credentials are read from.
DEFAULT_SECRETSPEC_PROVIDER = "itu-ties"

#: Name of the manifest the package looks for in its configuration directory.
SECRETSPEC_MANIFEST_NAME = "secretspec.toml"

#: Names of the declared secrets, keyed by the field they fill.
_SECRETSPEC_KEYS: Final[dict[str, str]] = {
    "username": "ITU_TIES_USERNAME",
    "password": "ITU_TIES_PASSWORD",
}

#: Reason passed to secretspec so audit logs show why the secrets were read.
_SECRETSPEC_REASON = "authenticate against the ITU-T document management system"


def _secretspec_module() -> Any:
    """Return the optional secretspec SDK, or ``None`` when it is not installed."""
    try:
        return import_module("secretspec")
    except ImportError:
        return None


def secretspec_credentials(
    provider: str = DEFAULT_SECRETSPEC_PROVIDER,
    manifest: Path | str | None = None,
) -> tuple[str, SecretStr] | None:
    """Read the TIES credentials from a secretspec provider.

    Args:
        provider: Name or URI of the secretspec provider to resolve.
        manifest: Path of the manifest that declares the providers. When it is
            omitted, secretspec discovers the manifest itself.

    Returns:
        The user name and the password, or ``None`` when secretspec is not
        installed, the provider is not configured, or either value is missing.
    """
    module = _secretspec_module()
    if module is None:
        return None
    try:
        builder = module.SecretSpec.builder().with_provider(provider).with_reason(_SECRETSPEC_REASON)
        if manifest is not None:
            builder = builder.with_path(str(manifest))
        resolved = builder.load()
    except (module.SecretSpecError, OSError):
        return None
    values = resolved.fields()
    username = values.get(_SECRETSPEC_KEYS["username"])
    password = values.get(_SECRETSPEC_KEYS["password"])
    if not username or not password:
        return None
    return username, SecretStr(password)


class SecretspecConfigSource(PydanticBaseSettingsSource):
    """Reads the TIES credentials from a secretspec provider.

    Contributes only :attr:`Settings.ties_username` and
    :attr:`Settings.ties_password`; every other setting keeps its default or
    comes from a higher priority source.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        provider: str = DEFAULT_SECRETSPEC_PROVIDER,
        manifest: Path | None = None,
    ) -> None:
        super().__init__(settings_cls)
        self._provider = provider
        self._manifest = manifest

    @staticmethod
    def get_field_value(field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Return the value of a single field; always unset for this source."""
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return the credentials found in the secretspec provider."""
        credentials = secretspec_credentials(self._provider, self._manifest)
        if credentials is None:
            return {}
        username, password = credentials
        return {"ties_username": username, "ties_password": password}
