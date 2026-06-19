package com.example.guidewirehomesecurityapp.api

import android.content.Context
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Fetches sensor events for the logged-in user's alarm system from the backend.
 * GET /events requires Authorization Bearer token; returns only events for that user's system.
 */
object EventService {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    /** Server base URL without /api (e.g. http://10.0.2.2:5000) */
    fun serverBaseUrl(context: Context): String =
        BackendEndpointResolver.apiBaseUrl(context)

    /**
     * GET /events — returns events for the authenticated user's alarm system only.
     * Requires JWT (from login). Call from a background thread (e.g. Dispatchers.IO).
     */
    fun getEvents(context: Context, serverBaseUrl: String = serverBaseUrl(context)): List<SensorEvent> {
        val url = "$serverBaseUrl/events"
        val token = BackendAuthService.getToken(context)
        val requestBuilder = Request.Builder().url(url).get()
        if (!token.isNullOrBlank()) {
            requestBuilder.addHeader("Authorization", "Bearer $token")
        }
        val request = requestBuilder.build()
        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val body = response.body?.string() ?: return emptyList()
                val arr = JSONArray(body)
                List(arr.length()) { i ->
                    val obj = arr.getJSONObject(i)
                    val v = when {
                        !obj.has("value") || obj.isNull("value") -> null
                        else -> obj.optDouble("value", Double.NaN).takeUnless { it.isNaN() }
                    }
                    SensorEvent(
                        device_id = obj.optString("device_id", ""),
                        event_type = obj.optString("event_type", ""),
                        count = obj.optInt("count", 0),
                        timestamp = obj.optDouble("timestamp", 0.0),
                        value = v,
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    /**
     * POST /api/device/connect — link ESP32 (esp32_001 = microcontroller_id 1) to your account
     * so real hardware sensor events show in the app. Call from background thread (e.g. Dispatchers.IO).
     * @return true if linked successfully, false otherwise.
     */
    /**
     * POST /api/pair — assign the logged-in user to an unpaired alarm warehouse using the system password (min 8 chars).
     * Must succeed before "Link ESP32" if the account was created via Google and has no warehouse yet.
     */
    fun pairWithWarehouse(context: Context, systemPassword: String, serverBaseUrl: String = serverBaseUrl(context)): Boolean {
        val url = "$serverBaseUrl/api/pair"
        val token = BackendAuthService.getToken(context)
        if (token.isNullOrBlank()) return false
        val body = JSONObject().apply { put("system_password", systemPassword) }
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(url)
            .post(body)
            .addHeader("Authorization", "Bearer $token")
            .addHeader("Content-Type", "application/json")
            .build()
        return try {
            client.newCall(request).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    fun connectDevice(context: Context, microcontrollerId: Int = 1, serverBaseUrl: String = serverBaseUrl(context)): Boolean {
        val url = "$serverBaseUrl/api/device/connect"
        val token = BackendAuthService.getToken(context)
        if (token.isNullOrBlank()) return false
        val body = JSONObject().apply { put("microcontroller_id", microcontrollerId) }
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(url)
            .post(body)
            .addHeader("Authorization", "Bearer $token")
            .addHeader("Content-Type", "application/json")
            .build()
        return try {
            client.newCall(request).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    /** Admin-configured names: index 0 = first reed (D4), 1 = second (D14). */
    fun getSensorLabels(context: Context, serverBaseUrl: String = serverBaseUrl(context)): List<String> {
        val url = "$serverBaseUrl/api/sensor-labels"
        val token = BackendAuthService.getToken(context) ?: return emptyList()
        val request = Request.Builder()
            .url(url)
            .get()
            .addHeader("Authorization", "Bearer $token")
            .build()
        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val obj = JSONObject(response.body?.string() ?: "{}")
                val arr = obj.optJSONArray("labels") ?: return emptyList()
                List(arr.length()) { i -> arr.optString(i, "") }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    data class PowerSample(val deviceId: String, val timestamp: Double, val valueMa: Double)

    /** Recent power samples (mA) for the Eco tab chart. */
    fun getPowerRecent(context: Context, serverBaseUrl: String = serverBaseUrl(context)): List<PowerSample> {
        val url = "$serverBaseUrl/api/power/recent"
        val token = BackendAuthService.getToken(context) ?: return emptyList()
        val request = Request.Builder()
            .url(url)
            .get()
            .addHeader("Authorization", "Bearer $token")
            .build()
        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val arr = JSONArray(response.body?.string() ?: "[]")
                List(arr.length()) { i ->
                    val o = arr.getJSONObject(i)
                    PowerSample(
                        deviceId = o.optString("device_id", ""),
                        timestamp = o.optDouble("timestamp", 0.0),
                        valueMa = o.optDouble("value_ma", 0.0),
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }
}
