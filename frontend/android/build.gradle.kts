// [Input] RN 0.81.5 Gradle plugin dependency versions.
// [Output] Android and Kotlin plugins aligned to the installed RN toolchain.
// [Pos] Native Android build root.
buildscript {
    repositories { google(); mavenCentral() }
    dependencies {
        classpath("com.android.tools.build:gradle:8.11.0")
        classpath("com.facebook.react:react-native-gradle-plugin")
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.1.20")
    }
}
allprojects { repositories { google(); mavenCentral() } }
apply(plugin = "com.facebook.react.rootproject")
