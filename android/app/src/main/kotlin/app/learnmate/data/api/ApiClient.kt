package app.learnmate.data.api

import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

val ApiJson =
    Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

class DeviceTokenInterceptor(
    private val token: String,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response =
        chain.proceed(
            chain
                .request()
                .newBuilder()
                .header("Authorization", "Bearer $token")
                .build(),
        )
}

fun apiBaseUrl(serverUrl: String): String = serverUrl.trimEnd('/') + "/api/v1/"

fun createLearnmateApi(
    serverUrl: String,
    deviceToken: String,
): LearnmateApi {
    val client =
        OkHttpClient
            .Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            // Lesson calls are slow.
            .readTimeout(60, TimeUnit.SECONDS)
            .addInterceptor(DeviceTokenInterceptor(deviceToken))
            .build()
    return Retrofit
        .Builder()
        .baseUrl(apiBaseUrl(serverUrl))
        .client(client)
        .addConverterFactory(ApiJson.asConverterFactory("application/json".toMediaType()))
        .build()
        .create(LearnmateApi::class.java)
}
