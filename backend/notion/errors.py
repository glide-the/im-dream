# [Sync] 2026-10-07: add domain-only busy retry and confirmed-selection first-sync failure types.
# [Input] Shared Notion connector backend modules.
# [Output] Provide typed connector/auth/operation/snapshot exceptions.
# [Pos] error node in backend/notion
# [Sync] 2026-07-04: initial connector error hierarchy for auth, discovery,
#                    persistence, and workspace snapshot materialization.
# [Sync] 2026-08-28: add safe credential, reauthorization, and permission error
#                    categories for agentdata homes and Runtime tool feedback.

"""Notion connector backend exceptions."""
from __future__ import annotations


class NotionConnectorError(Exception):
    """Base exception for Notion connector backend failures."""


class NotionConfigError(NotionConnectorError):
    """Invalid connector configuration or missing runtime settings."""


class NotionCredentialError(NotionConnectorError):
    """Server-owned credential home or thread projection is unavailable."""


class NotionAuthError(NotionConnectorError):
    """Authentication flow failed."""


class NotionAuthRequiredError(NotionAuthError):
    """Authorization is missing or expired and requires user action."""


class NotionAuthTimeoutError(NotionAuthError):
    """Authentication polling timed out before confirmation."""


class NotionCLIUnavailableError(NotionAuthError):
    """The `ntn` CLI was not found on PATH."""


class NotionOperationError(NotionConnectorError):
    """A read-only Notion CLI operation failed."""


class NotionPermissionError(NotionOperationError):
    """Notion denied access to a requested resource."""


class NotionSnapshotError(NotionConnectorError):
    """Snapshot persistence or materialization failed."""


class NotionSnapshotNotReadyError(NotionSnapshotError):
    """A current canonical snapshot is not yet available."""


class NotionSyncBusyError(NotionConnectorError):
    """A server-owned active lease prevents another manual sync."""

    def __init__(self, retry_after: int | None = None):
        super().__init__("Connector sync has not completed. Retry later.")
        self.retry_after = retry_after


class NotionSelectionSyncError(NotionConnectorError):
    """Scope persisted successfully, but its subsequent sync did not complete."""

    def __init__(self, cause: Exception):
        super().__init__("Resource selection was saved; index sync did not complete.")
        self.cause = cause


class NotionConnectorNotFoundError(NotionConnectorError):
    """Requested connector does not exist or does not belong to the user."""
