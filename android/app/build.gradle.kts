import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.roborazzi)
    alias(libs.plugins.ksp)
    alias(libs.plugins.kotlin.serialization)
}

val localProperties =
    Properties().apply {
        val file = rootProject.file("local.properties")
        if (file.exists()) file.inputStream().use { load(it) }
    }

android {
    namespace = "app.learnmate"
    compileSdk = 36

    defaultConfig {
        applicationId = "app.learnmate"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"

        // Read from local.properties so the device token never lands in git.
        buildConfigField(
            "String",
            "SERVER_URL",
            "\"${localProperties.getProperty("learnmate.serverUrl", "").ifBlank { "http://127.0.0.1:8000" }}\"",
        )
        buildConfigField("String", "DEVICE_TOKEN", "\"${localProperties.getProperty("learnmate.deviceToken", "")}\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    buildTypes {
        debug {
            // An Android OAuth client id is not a secret; it only identifies the app to Google.
            buildConfigField(
                "String",
                "GOOGLE_ANDROID_CLIENT_ID",
                "\"${localProperties.getProperty("google.androidClientId", "")}\"",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            all { it.useJUnitPlatform() }
        }
    }
}

kotlin {
    jvmToolchain(17)
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
}

ktlint {
    version.set("1.7.1")
}

// Robolectric's own downloader fetches the Android framework jar at test time with no retry, which made CI
// flaky. Gradle resolves and caches it instead, and Robolectric runs offline against that copy.
val robolectricRuntime: Configuration by configurations.creating

val copyRobolectricJars by tasks.registering(Copy::class) {
    from(robolectricRuntime)
    into(layout.buildDirectory.dir("robolectric-jars"))
}

tasks.withType<Test>().configureEach {
    dependsOn(copyRobolectricJars)
    val jarDir = layout.buildDirectory.dir("robolectric-jars")
    inputs.dir(jarDir)
    systemProperty("robolectric.offline", "true")
    systemProperty("robolectric.dependency.dir", jarDir.get().asFile.absolutePath)
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.navigation.compose)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.okhttp)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.retrofit)
    implementation(libs.retrofit.kotlinx.serialization)
    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    implementation(libs.work.runtime.ktx)
    ksp(libs.room.compiler)
    debugImplementation(libs.compose.ui.tooling)
    debugImplementation(libs.compose.ui.test.manifest)
    debugImplementation(libs.play.services.auth)

    testImplementation(platform(libs.junit.bom))
    testImplementation(libs.junit.jupiter)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.junit4)
    // The vintage engine runs the JUnit 4 Robolectric tests on the JUnit 5 platform.
    testRuntimeOnly(libs.junit.platform.launcher)
    testRuntimeOnly(libs.junit.vintage.engine)
    testImplementation(libs.robolectric)
    robolectricRuntime(libs.robolectric.android.all) { isTransitive = false }
    testImplementation(platform(libs.compose.bom))
    testImplementation(libs.compose.ui.test.junit4)
    testImplementation(libs.roborazzi)
    testImplementation(libs.roborazzi.compose)
    testImplementation(libs.roborazzi.junit.rule)
    testImplementation(libs.room.testing)
    testImplementation(libs.work.testing)
    testImplementation(libs.mockwebserver)
    testImplementation(libs.androidx.test.core)
}
