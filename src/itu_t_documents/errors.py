"""The errors the package raises.

Every error of the package derives from :class:`ItuError`, so that a caller
can catch the failures of the ITU-T web site as a group.
"""

from __future__ import annotations


class ItuError(RuntimeError):
    """Base class of the errors the package raises."""


class AuthenticationError(ItuError):
    """Raised when the TIES authentication could not be completed."""


class AccessDeniedError(ItuError):
    """Raised when the TIES account may not see the requested document.

    A TIES account is valid for the whole ITU-T, but its membership covers
    only the study groups the account belongs to. The ITU-T answers a
    document outside the membership with a status of 401 and a page that
    blames invalid credentials, which is not what happened.
    """


class IncompleteListingError(ItuError):
    """Raised when a document listing holds fewer documents than it reports.

    Every page of a listing is read, so a listing that still holds fewer
    documents than it reports means that the site changed and the documents
    of the listing would be lost silently.
    """


class UnknownEntityError(ItuError):
    """Raised when an entity of the ITU-T structure does not exist.

    The study groups of a study period, the working groups of a study group
    and the questions under study are published by the ITU-T and change from
    period to period. The catalogue knows them and refuses the ones that do
    not exist.
    """
