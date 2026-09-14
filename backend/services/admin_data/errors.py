# [Input] Admin transport/protocol outcomes and stable request identifiers.
# [Output] Redacted errors preserving status and unknown-commit recovery semantics.
# [Pos] Shared Admin authentication/data consumer error boundary.
# [Sync] 2026-09-14: introduce value-free failures without database fallback.
"""Safe exceptions: never retain HTTP requests, tokens, URLs or response bodies."""

from dataclasses import dataclass


@dataclass
class AdminDataError(Exception):
    # Exception tracebacks are assigned by context managers; freezing an Exception
    # masks the intended safe failure with FrozenInstanceError during cleanup.
    code: str
    status_code: int
    request_id: str | None = None
    outcome_unknown: bool = False

    def __str__(self) -> str:
        return f"{self.code} ({self.status_code})"


def unavailable(request_id: str | None = None, *, write: bool = False) -> AdminDataError:
    return AdminDataError("ADMIN_UNAVAILABLE", 503, request_id, write)


def invalid_response(request_id: str | None = None, *, write: bool = False) -> AdminDataError:
    return AdminDataError("ADMIN_RESPONSE_INVALID", 503, request_id, write)


def configuration_invalid() -> AdminDataError:
    return AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)


def invalid_access_token() -> AdminDataError:
    return AdminDataError("INVALID_ACCESS_TOKEN", 401)
