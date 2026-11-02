// [Input] Pinned RN Gradle plugin in the unified frontend dependency graph.
// [Output] Android native build and RN autolinking.
// [Pos] Android settings; no WebView resource build.
pluginManagement {
    includeBuild("../node_modules/@react-native/gradle-plugin")
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
plugins { id("com.facebook.react.settings") }
extensions.configure<com.facebook.react.ReactSettingsExtension> { autolinkLibrariesFromCommand() }
rootProject.name = "InkMemoryAndroid"
include(":app")
includeBuild("../node_modules/@react-native/gradle-plugin")
