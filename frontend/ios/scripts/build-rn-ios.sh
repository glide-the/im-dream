#!/bin/bash
# [Input] Explicit Xcode destination, locked RN/Next dependencies and existing iOS runtime resources.
# [Output] A locally signed standalone iOS application with original on-device services.
# [Pos] Reproducible iOS build entry; installed runtime preparation retains its existing scripts.
set -euo pipefail
if [ "$#" -ne 1 ]; then
  printf '%s\n' 'Usage: bash frontend/ios/scripts/build-rn-ios.sh "id=<device UDID>" (or "platform=iOS Simulator,id=<simulator UUID>")' >&2
  exit 2
fi
IOS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$IOS_ROOT/../.." && pwd)"
RN_ROOT="$IOS_ROOT/.."
export NODE_BINARY="$(command -v node)"
BUILD_SDK=iphoneos
if [[ "$1" == *"platform=iOS Simulator"* ]]; then BUILD_SDK=iphonesimulator; fi
pnpm --dir "$RN_ROOT" install --frozen-lockfile
(cd "$IOS_ROOT" && pod install --deployment)
uv run --no-project --with fonttools==4.60.1 --with brotli==1.2.0 python "$IOS_ROOT/scripts/prepare-fonts.py"
python3 "$IOS_ROOT/scripts/prepare-next.py"
pnpm --dir "$IOS_ROOT/Next/build-source" build
xcodebuild -workspace "$IOS_ROOT/InkMemory.xcworkspace" -scheme InkMemory \
  -configuration "${CONFIGURATION:-Release}" -sdk "$BUILD_SDK" -destination "$1" \
  -derivedDataPath "${INK_IOS_DERIVED_DATA:-$IOS_ROOT/build/ReactNative}" \
  -jobs "${INK_IOS_BUILD_JOBS:-3}" build
