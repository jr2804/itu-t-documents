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

from dataclasses import dataclass
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


@dataclass(frozen=True)
class SecretspecCredentials:
    """What a secretspec provider resolved.

    A declared secret can be resolved as an empty value: a ``dotenv``
    provider reads everything behind a leading ``#`` as a comment, so a
    password that begins with one is empty unless it is quoted. The provider
    does not fail — it hands out a value — so the package has to name the
    secret that is empty instead of reporting that no credentials exist.
    """

    username: str
    """The user name of the TIES account, empty when it was not resolved."""

    password: SecretStr
    """The password of the TIES account, empty when it was not resolved."""

    empty_fields: tuple[str, ...] = ()
    """The names of the declared secrets that were resolved as an empty value."""


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

    def __call__(self) -> dict[str, Any]:
        """Return the credentials found in the secretspec provider."""
        credentials = secretspec_credentials(self._provider, self._manifest)
        if credentials is None:
            return {}
        values: dict[str, Any] = {}
        if credentials.username and credentials.password.get_secret_value():
            values["ties_username"] = credentials.username
            values["ties_password"] = credentials.password
        if credentials.empty_fields:
            values["credentials_note"] = _credentials_note(self._provider, credentials.empty_fields)
        return values

    @staticmethod
    def get_field_value(field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Return the value of a single field; always unset for this source."""
        return None, field_name, False


def secretspec_credentials(
    provider: str = DEFAULT_SECRETSPEC_PROVIDER,
    manifest: Path | str | None = None,
) -> SecretspecCredentials | None:
    """Read the TIES credentials from a secretspec provider.

    Args:
        provider: Name or URI of the secretspec provider to resolve.
        manifest: Path of the manifest that declares the providers. When it is
            omitted, secretspec discovers the manifest itself.

    Returns:
        What the provider resolved, or ``None`` when secretspec is not
        installed, the provider is not configured, or it cannot be resolved.
        A resolved value can be empty; the names of the empty ones are in
        :attr:`SecretspecCredentials.empty_fields`.
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
    if username is None or password is None:
        # The provider did not resolve a declared secret at all; there is
        # nothing to report but the missing credentials.
        return None
    empty = tuple(name for name, value in ((_SECRETSPEC_KEYS["username"], username), (_SECRETSPEC_KEYS["password"], password)) if value == "")
    return SecretspecCredentials(username=username, password=SecretStr(password), empty_fields=empty)


def _credentials_note(provider: str, empty_fields: tuple[str, ...]) -> str:
    """Return the note that names the secrets a provider resolved as empty.

    Args:
        provider: The name or URI of the provider.
        empty_fields: The names of the declared secrets that were empty.

    Returns:
        The note.
    """
    names = ", ".join(empty_fields)
    return f"the secretspec provider '{provider}' resolved {names} as an empty value; quote the value in the provider's .env file"


def _secretspec_module() -> Any:
    """Return the optional secretspec SDK, or ``None`` when it is not installed."""
    try:
        return import_module("secretspec")
    except ImportError:
        return None
