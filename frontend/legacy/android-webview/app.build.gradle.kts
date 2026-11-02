// [Input] Canonical Dream React source, Android host source, and pinned Android toolchain.
// [Output] One Android application whose APK/AAB contains generated local WebView resources.
// [Pos] Android application build definition.
// [Sync] 2026-10-24: add the capability-gated Android host build.

plugins {
    id("com.android.application")
}

android {
    namespace = "com.inkmemory.mobile"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.inkmemory.mobile"
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        aidl = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

kotlin {
    jvmToolchain(17)
}

val frontendDirectory = rootProject.layout.projectDirectory.dir("../../frontend")
val generatedWebAssets = layout.buildDirectory.dir("generated/mobileWebAssets")
val generatedWebApplication = generatedWebAssets.map { it.dir("app") }

val buildMobileWebAssets by tasks.registering(Exec::class) {
    description = "Builds the canonical Dream React source for the Android WebView host."
    group = "build"
    workingDir(frontendDirectory)
    commandLine(
        "corepack", "pnpm", "exec", "node", "scripts/build-mobile-assets.mjs",
        "--outdir", generatedWebApplication.get().asFile.absolutePath,
    )
    inputs.file(frontendDirectory.file("package.json"))
    inputs.file(frontendDirectory.file("pnpm-lock.yaml"))
    inputs.file(frontendDirectory.file("scripts/build-mobile-assets.mjs"))
    inputs.dir(frontendDirectory.dir("mobile"))
    inputs.dir(frontendDirectory.dir("app/_dream"))
    inputs.dir(frontendDirectory.dir("public"))
    outputs.dir(generatedWebApplication)
}

val verifyMobileWebAssets by tasks.registering(Exec::class) {
    description = "Verifies the generated Dream React resource manifest before Android packaging."
    group = "verification"
    dependsOn(buildMobileWebAssets)
    val repositoryDirectory = rootProject.layout.projectDirectory.dir("../..")
    workingDir(repositoryDirectory)
    commandLine(
        "node", "mobile/scripts/check-web-assets.mjs",
        generatedWebApplication.get().asFile.absolutePath,
    )
    inputs.file(repositoryDirectory.file("mobile/scripts/check-web-assets.mjs"))
    inputs.dir(generatedWebApplication)
}

android.sourceSets.getByName("main").assets.srcDir(generatedWebAssets)
tasks.named("preBuild").configure { dependsOn(verifyMobileWebAssets) }

dependencies {
    implementation("androidx.activity:activity-ktx:1.13.0")
    implementation("androidx.core:core-ktx:1.19.1")
    implementation("androidx.webkit:webkit:1.18.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
}

