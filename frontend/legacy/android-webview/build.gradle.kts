// [Input] Gradle 9.6.0 and the Android Gradle Plugin artifact.
// [Output] Shared plugin version for the Android application module.
// [Pos] Android Gradle build root.
// [Sync] 2026-10-24: pin Android Gradle Plugin 9.4.1.

plugins {
    id("com.android.application") version "9.4.1" apply false
}

