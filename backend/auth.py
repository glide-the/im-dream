#!/usr/bin/env python3
# [Input] Historical helper imports; no JWT/password/refresh configuration is read.
# [Output] Explicit retired errors for local authority and pure duration/hash/header compatibility.
# [Pos] Retired authentication utility; Admin JWT verifier/request owner executes actual identity checks.
# [Sync] 2026-09-15: close standalone local signing/password/refresh/sliding authority without a default key.

from datetime import datetime, timedelta
import hashlib
import re
from typing import Optional


class LegacyAuthenticationRetired(RuntimeError):
    """Use the Admin authentication authority; legacy helpers cannot issue credentials."""


def create_access_token(user_id: int, email: str, expires_delta: Optional[timedelta] = None) -> str:
    raise LegacyAuthenticationRetired("Dream local authentication is retired")


def create_refresh_token_value() -> tuple[str, str, datetime]:
    raise LegacyAuthenticationRetired("Dream local authentication is retired")


def hash_password(password: str) -> str:
    raise LegacyAuthenticationRetired("Admin owns password authentication")


def verify_password(password: str, password_hash: str) -> bool:
    raise LegacyAuthenticationRetired("Admin owns password authentication")


def verify_access_token(token: str) -> Optional[dict]:
    return None


def maybe_renew_access_token(user_data: dict) -> Optional[str]:
    return None


def parse_duration(value: Optional[str], default: str = "7d") -> timedelta:
    """Parse compact duration strings such as ``15m`` or ``30d``."""

    raw = (value or default).strip().lower()
    if raw.isdigit():
        return timedelta(seconds=int(raw))

    match = re.fullmatch(r"(\d+)\s*([smhd])", raw)
    if not match:
        match = re.fullmatch(r"(\d+)\s*(seconds?|minutes?|hours?|days?)", raw)
    if not match:
        raise ValueError(f"Invalid duration value: {value!r}")

    amount = int(match.group(1))
    unit = match.group(2)
    if unit.startswith("s"):
        return timedelta(seconds=amount)
    if unit.startswith("m"):
        return timedelta(minutes=amount)
    if unit.startswith("h"):
        return timedelta(hours=amount)
    if unit.startswith("d"):
        return timedelta(days=amount)
    raise ValueError(f"Invalid duration unit: {unit!r}")

def hash_token(token: str) -> str:
    """Return a stable SHA-256 hash for opaque refresh/device tokens."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Token string or None
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
