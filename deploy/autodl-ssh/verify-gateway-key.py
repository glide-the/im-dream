#!/usr/bin/env python3
# [Input] A private Dream runtime env and the loopback Admin Gateway endpoint it configures.
# [Output] A redacted pass/fail receipt proving the configured service key is currently active.
# [Pos] AutoDL deployment gate; it never prints the key, bearer, response body, or private env values.
# [Sync] 2026-09-19: block sync/qualification when Dream carries an inactive Gateway service key.
# [Sync] 2026-09-19: parse the two required env values with the Python standard library on minimal hosts.

from __future__ import annotations

import json
from pathlib import Path
import shlex
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EXPECTED_CODE = "GATEWAY_SUBJECT_TOKEN_INVALID"
REQUIRED_KEYS = {"INK_GATEWAY_BASE_URL", "INK_GATEWAY_SERVICE_KEY"}


def fail(message: str) -> None:
    print(f"[gateway-key-check] {message}", file=sys.stderr)
    raise SystemExit(1)


def read_required_environment(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        fail("private Dream env cannot be read")
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or key not in REQUIRED_KEYS:
            continue
        try:
            parsed = shlex.split(raw_value, comments=True, posix=True)
        except ValueError:
            fail(f"invalid {key} entry in private Dream env")
        if len(parsed) > 1:
            fail(f"invalid {key} entry in private Dream env")
        values[key] = parsed[0] if parsed else ""
    return values


if len(sys.argv) != 2:
    fail("usage: verify-gateway-key.py <private-dream-env>")

environment = read_required_environment(Path(sys.argv[1]))
base_url = (environment.get("INK_GATEWAY_BASE_URL") or "").rstrip("/")
service_key = environment.get("INK_GATEWAY_SERVICE_KEY") or ""
if not base_url.startswith("http://127.0.0.1:") or not service_key.startswith("gw_"):
    fail("Gateway configuration is missing or invalid")

request = Request(
    f"{base_url}/v1/models",
    headers={
        "authorization": "Bearer diagnostic.invalid.token",
        "x-api-key": service_key,
        "accept": "application/json",
    },
)
try:
    with urlopen(request, timeout=10) as response:
        status = response.status
        payload = json.load(response)
except HTTPError as error:
    status = error.code
    try:
        payload = json.load(error)
    except (json.JSONDecodeError, UnicodeError):
        fail(f"Gateway returned status {status} without a safe error contract")
except (OSError, URLError, TimeoutError):
    fail("Gateway is unavailable")

code = payload.get("error", {}).get("code") if isinstance(payload, dict) else None
if status != 401 or code != EXPECTED_CODE:
    safe_code = code if isinstance(code, str) and code.startswith("GATEWAY_") else "unavailable"
    fail(f"service key rejected: status={status} code={safe_code}")

print(f"[gateway-key-check] active service key confirmed: status={status} code={code}")
