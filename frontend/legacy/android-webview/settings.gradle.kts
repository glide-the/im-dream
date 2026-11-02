// [Input] Android Gradle Plugin and AndroidX dependency coordinates.
// [Output] A single Android application project with controlled repositories.
// [Pos] Android Gradle settings root.
// [Sync] 2026-10-24: initialize the Android host project.

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "InkMemoryAndroid"
include(":app")

