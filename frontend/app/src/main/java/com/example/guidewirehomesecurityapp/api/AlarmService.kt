package com.example.guidewirehomesecurityapp.api

import android.content.Context
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Get and set armed state for the logged-in user's alarm system.
 * Backend: GET /api/alarm, PUT /api/alarm with JWT.
 */
object AlarmService {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private fun serverBaseUrl(context: Context): String =
        BackendEndpointResolver.apiBaseUrl(context)

    data class SetArmedResult(
        val success: Boolean,
        val armed: Boolean?,
        val pendingDisarm: Boolean,
        val requestId: String?,
    )

    /**
     * GET /api/alarm — current armed state. Call from background thread (e.g. Dispatchers.IO).
     * @return true = armed, false = disarmed, null = error or not linked
     */
    fun getArmedStatus(context: Context): Boolean? {
        val url = "${serverBaseUrl(context)}/api/alarm"
        val token = BackendAuthService.getToken(context) ?: return null
        val request = Request.Builder()
            .url(url)
            .get()
            .addHeader("Authorization", "Bearer $token")
            .build()
        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return null
                val body = response.body?.string() ?: return null
                val obj = JSONObject(body)
                obj.optBoolean("armed", false)
            }
        } catch (_: Exception) {
            null
        }
    }

    /**
     * PUT /api/alarm — set armed state. Trusted users may get pending_disarm instead of immediate disarm.
     */
    fun setArmedStatus(context: Context, armed: Boolean): SetArmedResult {
        val url = "${serverBaseUrl(context)}/api/alarm"
        val token = BackendAuthService.getToken(context) ?: return SetArmedResult(false, null, false, null)
        val body = JSONObject().apply { put("armed", armed) }
            .toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(url)
            .put(body)
            .addHeader("Authorization", "Bearer $token")
            .addHeader("Content-Type", "application/json")
            .build()
        return try {
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string() ?: ""
                if (!response.isSuccessful) {
                    return SetArmedResult(false, null, false, null)
                }
                val obj = JSONObject(responseBody)
                val pending = obj.optBoolean("pending_disarm", false)
                val rid = obj.optString("request_id", "").takeIf { it.isNotBlank() }
                val armedOut = if (obj.has("armed")) obj.optBoolean("armed", false) else null
                SetArmedResult(true, armedOut, pending, rid)
            }
        } catch (_: Exception) {
            SetArmedResult(false, null, false, null)
        }
    }
}
