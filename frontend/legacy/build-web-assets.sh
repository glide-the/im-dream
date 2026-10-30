#!/bin/sh
# [Input] Xcode target resource directory and the canonical frontend workspace.
# [Output] Generated local WebView resources inside the current application bundle.
# [Pos] iOS build adapter; it delegates compilation to frontend/scripts/build-mobile-assets.mjs.
# [Sync] 2026-10-24: generate one shared React resource set during the iOS build.
# [Sync] 2026-10-25: retained manual resource adapter; the current iOS Xcode target packages original Next instead.

set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: build-web-assets.sh OUTPUT_DIRECTORY" >&2
  exit 64
fi

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
SCRIPT_DIRECTORY=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FRONTEND_DIRECTORY=$(CDPATH= cd -- "$SCRIPT_DIRECTORY/../../../frontend" && pwd)

if ! command -v corepack >/dev/null 2>&1; then
  echo "corepack is required to build the mobile React resources" >&2
  exit 69
fi

cd "$FRONTEND_DIRECTORY"
corepack pnpm mobile:build -- --outdir "$1"
node "$SCRIPT_DIRECTORY/../../scripts/check-web-assets.mjs" "$1"
