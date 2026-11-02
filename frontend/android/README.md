<!-- [Input] Android project files and locally installed Android build tools. -->
<!-- [Output] Reproducible commands for prerequisite inspection, source tests, and debug builds. -->
<!-- [Pos] Operator entry point for the Android host scaffold. -->
<!-- [Sync] 2026-10-24: document the first Android host build boundary. -->

# Ink & Memory Android host

The unified frontend uses React Native 0.81.5, Android Gradle Plugin 8.11.0, Kotlin 2.1.20, Gradle 8.14.3, JDK 17, `compileSdk`/`targetSdk` 36 and `minSdk` 29. The application consumes `frontend/index.native.js` and shared `frontend/src/` through the RN Gradle plugin. The former WebView Activity and HTML asset build are archived under `frontend/legacy/android-webview/`.

Run the read-only prerequisite check:

```bash
sh scripts/check-toolchain.sh
```

After Android SDK platform 36, build-tools, NDK 27.1.12297006 and Gradle 8.14.3 are available, generate the standard wrapper JAR once and run the checks:

```bash
gradle wrapper --gradle-version 8.14.3
./gradlew testDebugUnitTest assembleDebug
```

`MainApplication` owns the RN Host and `MainActivity` is a ReactActivity. `InkRuntimePackage` reports `CAPABILITY_UNAVAILABLE` until embedded Python/Claude and HTTP transport are qualified. The original private runtime service and document/share adapters remain available for that integration. Android APK/AAB, signing and real business acceptance are pending; no remote Dream execution fallback is provided.

