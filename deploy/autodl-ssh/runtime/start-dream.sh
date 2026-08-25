#!/usr/bin/env bash
# [Input] Exported launcher paths and the mode-0640 Dream runtime env.
# [Output] One foreground FastAPI/Claude Agent process bound to the mapped local port.
# [Pos] AutoDL screen-session entrypoint for Dream backend only.
# [Sync] 2026-08-26: add direct-host uvicorn supervision without Docker/nginx.
set -euo pipefail

: "${AUTODL_DREAM_ENV_FILE:?AUTODL_DREAM_ENV_FILE is required}"
: "${AUTODL_DREAM_PID_FILE:?AUTODL_DREAM_PID_FILE is required}"
: "${AUTODL_NODE_BIN:?AUTODL_NODE_BIN is required}"
: "${AUTODL_NPM_BIN:?AUTODL_NPM_BIN is required}"

export PATH="${AUTODL_NPM_BIN}:${AUTODL_NODE_BIN}:${PATH}"

release_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${release_root}"
printf '%s\n' "$$" >"${AUTODL_DREAM_PID_FILE}"
exec ./venv/bin/python -c '
import os
from pathlib import Path
from dotenv import dotenv_values

env_file = Path(os.environ["AUTODL_DREAM_ENV_FILE"])
for key, value in dotenv_values(env_file).items():
    if value is not None:
        os.environ[key] = value
os.chdir("app")
python = str(Path.cwd().parent / "venv/bin/python")
os.execvpe(
    python,
    [
        python,
        "-m",
        "uvicorn",
        "server:app",
        "--host",
        os.environ.get("HOST", "127.0.0.1"),
        "--port",
        os.environ.get("PORT", "6006"),
        "--proxy-headers",
        "--forwarded-allow-ips=*",
    ],
    os.environ,
)
'
