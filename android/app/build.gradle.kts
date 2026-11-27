plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "com.ajusta.app"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.ajusta.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 2
        versionName = "0.2.0"
        val apiBaseUrl = (project.findProperty("AJUSTA_API_BASE_URL") as String?) ?: "https://api.ajusta.example"
        buildConfigField("String", "AJUSTA_API_BASE_URL", "\"$apiBaseUrl\"")
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}
dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2025.11.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.activity:activity-compose:1.12.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.10.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
