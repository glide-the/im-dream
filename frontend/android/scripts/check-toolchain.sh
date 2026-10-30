#!/bin/sh
# [Input] PATH, JAVA_HOME, and ANDROID_HOME or ANDROID_SDK_ROOT.
# [Output] Read-only Android build prerequisite report and a nonzero status when a prerequisite is missing.
# [Pos] Android host build preflight; it installs and modifies nothing.
# [Sync] 2026-10-24: add the first local Android toolchain check.

set -eu

status=0

if command -v java >/dev/null 2>&1; then
  java -version 2>&1 | sed -n '1p'
else
  echo 'missing: JDK 17 (java)'
  status=1
fi

if command -v gradle >/dev/null 2>&1; then
  gradle --version | sed -n '1,8p'
else
  echo 'missing: Gradle 8.14.3 or a generated Gradle wrapper'
  status=1
fi

android_sdk_root=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}
if [ -z "$android_sdk_root" ] || [ ! -d "$android_sdk_root/platforms/android-36" ]; then
  echo 'missing: Android SDK platform 36 (ANDROID_SDK_ROOT or ANDROID_HOME)'
  status=1
else
  echo "android-sdk: $android_sdk_root"
fi

exit "$status"

