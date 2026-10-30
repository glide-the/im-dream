// [Input] Shared RN entry and pinned native Android dependencies.
// [Output] RN Android APK/AAB configuration; on-device runtime qualification remains required.
// [Pos] Android application; main UI is rendered by React Native.
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.facebook.react")
}
react {
    root.set(file("../.."))
    reactNativeDir.set(file("../../node_modules/react-native"))
    entryFile.set(file("../../index.native.js"))
    autolinkLibrariesWithApp()
}
android {
    namespace = "com.inkmemory.mobile"
    compileSdk = 36
    ndkVersion = "27.1.12297006"
    defaultConfig {
        applicationId = "com.inkmemory.mobile"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildFeatures { aidl = true; buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}
kotlin { jvmToolchain(17) }
dependencies {
    implementation("com.facebook.react:react-android")
    implementation("com.facebook.react:hermes-android")
    implementation("androidx.activity:activity-ktx:1.10.1")
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.webkit:webkit:1.14.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
}
