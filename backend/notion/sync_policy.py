# [Input] Connector config JSON, last-success timestamps, and user-selected automatic-sync preferences.
# [Output] Validated default/desired/effective policy snapshots, monotonic revisions, due decisions, and safe status transitions.
# [Pos] Notion snapshot synchronization policy model in backend/notion
# [Sync] 2026-08-28: define the Settings strategy contract without adding a database table or environment-specific path.
# [Sync] 2026-08-29: add a cleared transition for a connected actor with an explicit empty resource scope.

"""Notion canonical snapshot synchronization policy."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .errors import NotionConnectorError

SYNC_POLICY_SCHEMA_VERSION = 1
SYNC_POLICY_CONFIG_KEY = "snapshot_sync_policy"
SYNC_POLICY_ALLOWED_INTERVAL_MINUTES = (15, 60, 360, 1440)
SYNC_POLICY_DEFAULT_ENABLED = True
SYNC_POLICY_DEFAULT_INTERVAL_MINUTES = 15
SYNC_POLICY_DEFAULT_REVISION = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _time_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _default_rule() -> dict[str, Any]:
    return {
        "enabled": SYNC_POLICY_DEFAULT_ENABLED,
        "interval_minutes": SYNC_POLICY_DEFAULT_INTERVAL_MINUTES,
        "revision": SYNC_POLICY_DEFAULT_REVISION,
    }


def _valid_rule(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    enabled = value.get("enabled")
    interval = value.get("interval_minutes")
    revision = value.get("revision")
    if not isinstance(enabled, bool):
        return None
    if isinstance(interval, bool) or interval not in SYNC_POLICY_ALLOWED_INTERVAL_MINUTES:
        return None
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        return None
    return {
        "enabled": enabled,
        "interval_minutes": interval,
        "revision": revision,
    }


def resolve_sync_policy(
    raw: Any,
    *,
    last_synced_at: Any = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Project a complete public policy while retaining safe LKG defaults."""

    current_time = now or _utcnow()
    default = _default_rule()
    stored = dict(raw) if isinstance(raw, Mapping) else {}
    schema_version = stored.get("schema_version")
    desired = _valid_rule(stored.get("desired"))
    effective = _valid_rule(stored.get("effective"))
    structurally_valid = (
        schema_version == SYNC_POLICY_SCHEMA_VERSION
        and desired is not None
        and effective is not None
        and desired["revision"] == effective["revision"]
        and desired["enabled"] == effective["enabled"]
        and desired["interval_minutes"] == effective["interval_minutes"]
    )
    if not structurally_valid:
        desired = dict(default)
        effective = dict(default)
    status = str(stored.get("status") or "applied")
    if status not in {"applied", "syncing", "error", "disabled"}:
        status = "error"
    if not effective["enabled"]:
        status = "disabled"
    last_success = _parse_time(stored.get("last_success_at")) or _parse_time(last_synced_at)
    last_attempt = _parse_time(stored.get("last_attempt_at"))
    next_sync = (
        last_success + timedelta(minutes=int(effective["interval_minutes"]))
        if effective["enabled"] and last_success is not None
        else current_time
        if effective["enabled"]
        else None
    )
    return {
        "schema_version": SYNC_POLICY_SCHEMA_VERSION,
        "default": default,
        "desired": desired,
        "effective": effective,
        "status": status,
        "last_attempt_at": _time_text(last_attempt),
        "last_success_at": _time_text(last_success),
        "next_sync_at": _time_text(next_sync),
        "last_error_code": (
            str(stored.get("last_error_code"))
            if status == "error" and stored.get("last_error_code")
            else None
        ),
        "allowed_interval_minutes": list(SYNC_POLICY_ALLOWED_INTERVAL_MINUTES),
    }


def update_sync_policy(
    raw: Any,
    *,
    enabled: bool,
    interval_minutes: int,
    last_synced_at: Any = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(enabled, bool):
        raise NotionConnectorError("Sync policy enabled must be boolean.")
    if isinstance(interval_minutes, bool) or interval_minutes not in SYNC_POLICY_ALLOWED_INTERVAL_MINUTES:
        raise NotionConnectorError("Sync policy interval is not supported.")
    current = resolve_sync_policy(raw, last_synced_at=last_synced_at, now=now)
    revision = int(current["desired"]["revision"]) + 1
    rule = {
        "enabled": enabled,
        "interval_minutes": interval_minutes,
        "revision": revision,
    }
    current.update(
        {
            "desired": dict(rule),
            "effective": dict(rule),
            "status": "applied" if enabled else "disabled",
            "last_error_code": None,
        }
    )
    current.pop("next_sync_at", None)
    current.pop("allowed_interval_minutes", None)
    current.pop("default", None)
    return current


def transition_sync_policy(
    raw: Any,
    transition: str,
    *,
    last_synced_at: Any = None,
    error_code: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or _utcnow()
    current = resolve_sync_policy(raw, last_synced_at=last_synced_at, now=current_time)
    if transition == "started":
        current["status"] = "syncing"
        current["last_attempt_at"] = _time_text(current_time)
        current["last_error_code"] = None
    elif transition == "succeeded":
        current["status"] = "applied" if current["effective"]["enabled"] else "disabled"
        current["last_attempt_at"] = _time_text(current_time)
        current["last_success_at"] = _time_text(current_time)
        current["last_error_code"] = None
    elif transition == "failed":
        current["status"] = "error"
        current["last_attempt_at"] = _time_text(current_time)
        current["last_error_code"] = str(error_code or "SYNC_FAILED")
    elif transition == "cleared":
        current["status"] = (
            "applied" if current["effective"]["enabled"] else "disabled"
        )
        current["last_attempt_at"] = None
        current["last_success_at"] = None
        current["last_error_code"] = None
    else:
        raise NotionConnectorError("Sync policy transition is invalid.")
    for key in ("default", "allowed_interval_minutes", "next_sync_at"):
        current.pop(key, None)
    return current


def sync_policy_is_due(
    raw: Any,
    *,
    last_synced_at: Any = None,
    now: datetime | None = None,
) -> bool:
    current_time = now or _utcnow()
    policy = resolve_sync_policy(raw, last_synced_at=last_synced_at, now=current_time)
    if not policy["effective"]["enabled"] or policy["status"] == "syncing":
        return False
    next_sync = _parse_time(policy.get("next_sync_at"))
    return next_sync is None or next_sync <= current_time


__all__ = [
    "SYNC_POLICY_ALLOWED_INTERVAL_MINUTES",
    "SYNC_POLICY_CONFIG_KEY",
    "SYNC_POLICY_DEFAULT_ENABLED",
    "SYNC_POLICY_DEFAULT_INTERVAL_MINUTES",
    "SYNC_POLICY_SCHEMA_VERSION",
    "resolve_sync_policy",
    "sync_policy_is_due",
    "transition_sync_policy",
    "update_sync_policy",
]
