# [Sync] 2026-10-06: read selected canonical index first; only today-updated metadata may be verified.
# [Input] Actor canonical index, selected-date timezone and explicit metadata API/URL policy.
# [Output] Snapshot-first selected-day projection; remote verification only of snapshot-today updates.
# [Pos] Calendar read-only projection in backend/notion; synchronization owns index persistence.
# [Sync] 2026-10-05: implement the accepted Search scope and exclude all URL userinfo, including empty fields.
from __future__ import annotations

import asyncio
import json
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import config
from .errors import NotionOperationError, NotionPermissionError
from .operations import NotionOperationClient, _extract_title


class NotionTodayError(NotionOperationError):
    def __init__(self, code: str, status: int = 502, *, retry_after: int | None = None,
                 context: dict | None = None):
        super().__init__(code)
        self.code, self.status = code, status
        self.retry_after, self.context = retry_after, context or {}


def remote_error(stdout: str, stderr: str) -> NotionTodayError:
    """Classify only safe status/code/header facts; never publish CLI messages."""
    payload: dict = {}
    for raw in (stdout, stderr):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed.get("error", parsed)
                if not isinstance(payload, dict):
                    payload = parsed
                break
        except (ValueError, TypeError):
            pass
    text = (stdout + "\n" + stderr).lower()
    code = str(payload.get("code", ""))
    status = payload.get("status")
    if code == "unauthorized" or status == 401 or re.search(r"(?:status|http)\s*:?\s*401", text) or "unauthorized" in text:
        return NotionTodayError("NOTION_AUTH_EXPIRED", 401)
    if code == "restricted_resource" or status == 403 or "forbidden" in text or re.search(r"(?:status|http)\s*:?\s*403", text):
        return NotionTodayError("NOTION_PERMISSION_DENIED", 403)
    if code == "object_not_found" or status == 404 or re.search(r"(?:status|http)\s*:?\s*404", text):
        return NotionTodayError("NOTION_RESOURCE_UNAVAILABLE", 404)
    if code == "rate_limited" or status in (429, 529) or re.search(r"\b(?:429|529)\b", text):
        headers = payload.get("headers")
        retry = payload.get("retry_after")
        if isinstance(headers, dict):
            retry = next((v for k, v in headers.items() if k.lower() == "retry-after"), retry)
        match = re.search(r"retry[-_ ]after\s*[:=]\s*(\d+)", text)
        try:
            seconds = float(retry if retry is not None else match.group(1) if match else 0)
            wait = math.ceil(seconds) if math.isfinite(seconds) and seconds > 0 else None
        except (ValueError, TypeError):
            wait = None
        return NotionTodayError("NOTION_RATE_LIMITED", 429, retry_after=wait)
    return NotionTodayError("NOTION_UPSTREAM_UNAVAILABLE", 502)


def timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def day_context(time_zone: str, date_key: str, now: datetime) -> dict:
    try:
        zone = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise NotionTodayError("NOTION_TIMEZONE_UNAVAILABLE", 503) from None
    try:
        day = date.fromisoformat(date_key)
        if day.isoformat() != date_key:
            raise ValueError
        next_day = day + timedelta(days=1)
    except (TypeError, ValueError, OverflowError):
        raise NotionTodayError("NOTION_DATE_INVALID", 400) from None
    return {"dateKey": day.isoformat(), "todayKey": now.astimezone(zone).date().isoformat(), "timeZone": time_zone,
            "intervalStart": datetime.combine(day, time.min, zone).astimezone(timezone.utc).isoformat(),
            "intervalEnd": datetime.combine(next_day, time.min, zone).astimezone(timezone.utc).isoformat(),
            "observedAt": now.isoformat()}


def api_version() -> str:
    value = config.NOTION_TODAY_API_VERSION
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise NotionTodayError("NOTION_API_VERSION_UNCONFIGURED", 503) from None
    return value


def safe_url(value: Any) -> str | None:
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme == "https" and parsed.hostname in config.NOTION_ALLOWED_URL_HOSTS
                and parsed.port in (None, 443) and parsed.username is None and parsed.password is None):
            return value
    except ValueError:
        pass
    return None


def page_identity(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return ""
    try:
        return str(UUID(value))
    except ValueError:
        return value


def snapshot_records(snapshot: dict | None) -> tuple[dict[str, dict], set[str]]:
    records: dict[str, dict] = {}
    reasons: set[str] = set()
    if snapshot is None:
        return records, {"snapshot_unavailable"}
    for raw in snapshot.get("index") or []:
        key = page_identity(raw.get("page_id")) if isinstance(raw, dict) else ""
        if not key:
            reasons.add("metadata_missing")
            continue
        raw = dict(raw, page_id=key)
        previous = records.get(key)
        if previous is not None and previous != raw:
            reasons.add("snapshot_duplicate")
            old, new = timestamp(previous.get("last_edited_time")), timestamp(raw.get("last_edited_time"))
            if new is None or (old is not None and new <= old):
                continue
        records[key] = raw
    return records, reasons


def project_documents(records: dict[str, dict], connector_id: str, context: dict,
                      snapshot: dict | None, reasons: set[str], verification: str,
                      retry_after: int | None = None) -> dict:
    start, end = timestamp(context["intervalStart"]), timestamp(context["intervalEnd"])
    today = context["dateKey"] == context["todayKey"]
    items: list[dict] = []
    for key, raw in records.items():
        if raw.get("archived") or raw.get("in_trash"):
            continue
        created, edited = timestamp(raw.get("created_time")), timestamp(raw.get("last_edited_time"))
        if created is None or edited is None:
            reasons.add("metadata_missing")
        created_on_date = created is not None and start <= created < end
        edited_on_date = edited is not None and start <= edited < end
        if not created_on_date and not (today and edited_on_date):
            continue
        icon = raw.get("icon")
        emoji = icon.get("emoji") if isinstance(icon, dict) and icon.get("type") == "emoji" else None
        items.append({"pageId": key, "title": _extract_title(raw, fallback="未命名文档"), "url": safe_url(raw.get("url")),
                      "createdTime": created.isoformat() if created else None,
                      "lastEditedTime": edited.isoformat() if edited else None,
                      "emoji": emoji if isinstance(emoji, str) and emoji.isprintable() else None,
                      "group": "created" if created_on_date else "edited", "createdOnDate": created_on_date,
                      "editedOnDate": edited_on_date})
    items.sort(key=lambda item: item["pageId"])
    items.sort(key=lambda item: item["createdTime"] if item["group"] == "created" else item["lastEditedTime"], reverse=True)
    items.sort(key=lambda item: 0 if item["group"] == "created" else 1)
    metadata = snapshot.get("metadata", {}) if snapshot else {}
    fetched = timestamp(metadata.get("fetched_at"))
    return {**context, "connectorId": connector_id, "items": items, "candidateCount": len(records),
            "coverage": "connector_snapshot", "paginationState": "partial" if reasons else "complete",
            "partialReasons": sorted(reasons), "retryAfter": retry_after,
            "snapshotVersion": metadata.get("snapshot_version"),
            "snapshotFetchedAt": fetched.isoformat() if fetched else None, "verificationState": verification,
            "counts": {"created": sum(item["createdOnDate"] for item in items),
                       "edited": sum(not item["createdOnDate"] for item in items), "total": len(items)}}


async def read_documents(client: NotionOperationClient | None, connector_id: str, context: dict,
                         snapshot: dict | None) -> dict:
    records, reasons = snapshot_records(snapshot)
    start, end = timestamp(context["intervalStart"]), timestamp(context["intervalEnd"])
    candidates = [key for key, raw in records.items()
                  if context["dateKey"] == context["todayKey"]
                  and (edited := timestamp(raw.get("last_edited_time"))) is not None and start <= edited < end]
    verification = "pending" if candidates else "not_required"
    retry_after = None
    if client is not None and candidates:
        verification = "complete"
        try:
            async with asyncio.timeout(client._timeout_seconds()):
                for key in candidates:
                    try:
                        raw = await client.get_page_metadata(key)
                        if page_identity(raw.get("id")) != key or raw.get("object") != "page":
                            reasons.add("metadata_identity_mismatch")
                            verification = "partial"
                            continue
                        records[key] = {**raw, "page_id": key, "title": _extract_title(raw, fallback="未命名文档")}
                    except NotionTodayError as exc:
                        if exc.code == "NOTION_AUTH_EXPIRED":
                            raise
                        verification = "partial"
                        reasons.add(exc.code)
                        if exc.code in {"NOTION_PERMISSION_DENIED", "NOTION_RESOURCE_UNAVAILABLE"}:
                            records.pop(key, None)
                            continue
                        retry_after = exc.retry_after
                        break
        except (NotionOperationError, TimeoutError) as exc:
            if isinstance(exc, NotionTodayError) and exc.code == "NOTION_AUTH_EXPIRED":
                raise
            if isinstance(exc, NotionPermissionError):
                raise
            verification = "partial"
            reasons.add(exc.code if isinstance(exc, NotionTodayError) else "NOTION_UPSTREAM_UNAVAILABLE")
            retry_after = exc.retry_after if isinstance(exc, NotionTodayError) else None
    return project_documents(records, connector_id, context, snapshot, reasons, verification, retry_after)
