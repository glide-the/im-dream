#!/usr/bin/env bash
# [Input] Versioned frontend/backend release, launcher paths, and mode-0640 Dream runtime env.
# [Output] One supervised Vite Preview process on 6006 and FastAPI process on 8765.
# [Pos] AutoDL screen-session entrypoint for the complete direct-host Dream stack.
# [Sync] 2026-08-26: supervise same-origin frontend 6006 and private backend 8765 without nginx.
# [Sync] 2026-08-28: bind Agent workspaces and Notion user credentials to the
#                    explicit persistent AutoDL agentdata root.
set -euo pipefail

: "${AUTODL_DREAM_ENV_FILE:?AUTODL_DREAM_ENV_FILE is required}"
: "${AUTODL_DREAM_PID_FILE:?AUTODL_DREAM_PID_FILE is required}"
: "${AUTODL_NODE_BIN:?AUTODL_NODE_BIN is required}"
: "${AUTODL_NPM_BIN:?AUTODL_NPM_BIN is required}"
: "${INK_AUTODL_DATA_ROOT:?INK_AUTODL_DATA_ROOT is required}"
: "${AUTODL_DREAM_FRONTEND_PORT:=6006}"
: "${AUTODL_DREAM_BACKEND_PORT:=8765}"

export PATH="${AUTODL_NPM_BIN}:${AUTODL_NODE_BIN}:${PATH}"

release_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${release_root}"
printf '%s\n' "$$" >"${AUTODL_DREAM_PID_FILE}"

exec ./venv/bin/python -c '
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

release_root = Path.cwd()
env = os.environ.copy()
for key, value in dotenv_values(env["AUTODL_DREAM_ENV_FILE"]).items():
    if value is not None:
        env[key] = value

frontend_port = env.get("AUTODL_DREAM_FRONTEND_PORT", "6006")
backend_port = env.get("AUTODL_DREAM_BACKEND_PORT", "8765")
env["HOST"] = "127.0.0.1"
env["PORT"] = backend_port
env.setdefault("VITE_DEV_API_PROXY_TARGET", f"http://127.0.0.1:{backend_port}")
env.setdefault("NO_COLOR", "1")
agentdata_root = Path(env["INK_AUTODL_DATA_ROOT"]).resolve(strict=True)
env.setdefault("AGENT_CWD", str(agentdata_root / "agent-workspaces"))
env.setdefault("INK_NOTION_RUNTIME_ROOT", str(agentdata_root / "notion-runtime"))

python = str(release_root / "venv/bin/python")
node = str(Path(env["AUTODL_NODE_BIN"]) / "node")
vite = str(release_root / "frontend/node_modules/vite/bin/vite.js")
children: list[subprocess.Popen[bytes]] = []

def stop_children() -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()
    deadline = time.monotonic() + 10
    for child in children:
        while child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        if child.poll() is None:
            child.kill()
    for child in children:
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass

def handle_signal(signum: int, _frame: object) -> None:
    stop_children()
    raise SystemExit(128 + signum)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

backend = subprocess.Popen(
    [
        python,
        "-m",
        "uvicorn",
        "server:app",
        "--host",
        "127.0.0.1",
        "--port",
        backend_port,
        "--proxy-headers",
        "--forwarded-allow-ips=*",
    ],
    cwd=release_root / "app",
    env=env,
)
children.append(backend)

backend_health = f"http://127.0.0.1:{backend_port}/api/health"
for _ in range(120):
    if backend.poll() is not None:
        raise SystemExit(backend.returncode or 1)
    try:
        with urllib.request.urlopen(backend_health, timeout=2) as response:
            if response.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    stop_children()
    raise SystemExit("FastAPI did not become healthy within 120 seconds")

frontend = subprocess.Popen(
    [node, vite, "preview", "--host", "127.0.0.1", "--port", frontend_port, "--strictPort"],
    cwd=release_root / "frontend",
    env=env,
)
children.append(frontend)

try:
    while True:
        for child in children:
            code = child.poll()
            if code is not None:
                stop_children()
                raise SystemExit(code)
        time.sleep(0.5)
finally:
    stop_children()
'
