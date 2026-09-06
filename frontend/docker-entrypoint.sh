#!/bin/sh
# [Input] BACKEND_URL, API_BASE_URL, WS_BASE_URL env vars and the public runtime config template.
# [Output] Render frontend runtime config before starting the standalone Next server.
# [Pos] canonical frontend Node container entrypoint
# [Sync] 2026-06-12: generate runtime-config.js so deployed frontend can call backend by cross-origin URL.
# [Sync] 2026-06-15: render runtime-config.js at frontend root after removing /ink-and-memory/ prefix.
# [Sync] 2026-09-05: replace the Nginx/Vite process with the root standalone Next server.
set -eu

# API_BASE_URL is the browser-facing backend origin. BACKEND_URL remains available
# to server-owned Route Handlers and explicit internal proxy configuration.
API_BASE_URL="${API_BASE_URL:-${BACKEND_URL:-}}"
WS_BASE_URL="${WS_BASE_URL:-}"
INK_BACKEND_INTERNAL_URL="${INK_BACKEND_INTERNAL_URL:-${BACKEND_URL:-}}"
export API_BASE_URL WS_BASE_URL BACKEND_URL INK_BACKEND_INTERNAL_URL

if [ -f /app/public/runtime-config.template.js ]; then
  envsubst '${API_BASE_URL} ${WS_BASE_URL}' \
    < /app/public/runtime-config.template.js \
    > /app/public/runtime-config.js
fi

exec node server.js
