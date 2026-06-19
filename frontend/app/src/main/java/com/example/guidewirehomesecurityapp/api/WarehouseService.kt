package com.example.guidewirehomesecurityapp.api

import android.content.Context
import android.util.Log
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import com.example.guidewirehomesecurityapp.notifications.AlarmFirebaseMessagingService
import com.google.android.gms.tasks.Tasks
import com.google.firebase.messaging.FirebaseMessaging
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** Warehouseowner APIs: /api/warehouse/members and alarm disarm approval. */
object WarehouseService {

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private fun base(context: Context) =
        BackendEndpointResolver.apiBaseUrl(context)

    private fun auth(context: Context, path: String, method: String, body: String? = null): Request {
        val token = BackendAuthService.getToken(context) ?: ""
        val b = Request.Builder()
            .url("${base(context)}$path")
            .addHeader("Authorization", "Bearer $token")
        when (method) {
            "GET" -> b.get()
            "POST" -> b.post((body ?: "{}").toRequestBody("application/json".toMediaType()))
            "PATCH" -> b.patch((body ?: "{}").toRequestBody("application/json".toMediaType()))
            "DELETE" -> b.delete()
            else -> b.get()
        }
        if (method == "POST" || method == "PATCH") {
            b.addHeader("Content-Type", "application/json")
        }
        return b.build()
    }

    data class WarehouseMember(
        val id: Int,
        val username: String,
        val email: String,
        val phone: String,
        val warehouseRole: String,
    )

    fun listMembers(context: Context): List<WarehouseMember> {
        val req = auth(context, "/api/warehouse/members", "GET")
        return try {
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val arr = JSONArray(response.body?.string() ?: "[]")
                List(arr.length()) { i ->
                    val o = arr.getJSONObject(i)
                    WarehouseMember(
                        id = o.optInt("id", 0),
                        username = o.optString("username", ""),
                        email = o.optString("email", ""),
                        phone = o.optString("phone", ""),
                        warehouseRole = o.optString("warehouse_role", "admin"),
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun updateMemberWarehouseRole(context: Context, memberId: Int, warehouseRole: String): Boolean {
        val body = JSONObject().apply { put("warehouse_role", warehouseRole) }.toString()
        val req = auth(context, "/api/warehouse/members/$memberId", "PATCH", body)
        return try {
            client.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    fun removeMember(context: Context, memberId: Int): Boolean {
        val req = auth(context, "/api/warehouse/members/$memberId", "DELETE")
        return try {
            client.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    data class PendingDisarm(val id: String, val requestedByUserId: Int, val createdAt: Double)

    fun listPendingDisarmRequests(context: Context): List<PendingDisarm> {
        val req = auth(context, "/api/alarm/pending-disarm-requests", "GET")
        return try {
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val arr = JSONArray(response.body?.string() ?: "[]")
                List(arr.length()) { i ->
                    val o = arr.getJSONObject(i)
                    PendingDisarm(
                        id = o.optString("id", ""),
                        requestedByUserId = o.optInt("requested_by_user_id", 0),
                        createdAt = o.optDouble("created_at", 0.0),
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun approveDisarm(context: Context, requestId: String): Boolean {
        val req = auth(context, "/api/alarm/disarm-requests/$requestId/approve", "POST", "{}")
        return try {
            client.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    fun denyDisarm(context: Context, requestId: String): Boolean {
        val req = auth(context, "/api/alarm/disarm-requests/$requestId/deny", "POST", "{}")
        return try {
            client.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    fun deleteAccount(context: Context): Pair<Boolean, String?> {
        val req = auth(context, "/api/user/account", "DELETE")
        return try {
            client.newCall(req).execute().use { response ->
                if (response.isSuccessful) {
                    // Clear auth data after successful deletion
                    BackendAuthService.clearAuthData(context)
                    Log.d("WarehouseService", "Account deleted successfully")
                    Pair(true, null)
                } else {
                    val rawBody = response.body?.string().orEmpty()
                    val detail = try {
                        JSONObject(rawBody).optString("detail", "").ifBlank { "HTTP ${response.code}" }
                    } catch (_: Exception) {
                        "HTTP ${response.code}"
                    }
                    Log.e("WarehouseService", "Delete account failed: ${response.code} $rawBody")
                    Pair(false, detail)
                }
            }
        } catch (e: Exception) {
            Log.e("WarehouseService", "Delete account error", e)
            Pair(false, e.message ?: "Network error")
        }
    }

    fun notifyWarehouse(context: Context, title: String, body: String): Int {
        val inlineFcmToken = registerCurrentDeviceTokenBestEffort(context)
        if (inlineFcmToken.isNullOrBlank()) {
            Log.w("WarehouseService", "notifyWarehouse aborted: no FCM token available")
            return 0
        }
        val reqBody = JSONObject().apply {
            put("title", title)
            put("body", body)
        }.toString()
        val req = auth(context, "/api/warehouse/notify", "POST", reqBody)
            .newBuilder()
            .apply {
                addHeader("X-FCM-Token", inlineFcmToken)
            }
            .build()
        return try {
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) return 0
                JSONObject(response.body?.string() ?: "{}").optInt("sent_to_devices", 0)
            }
        } catch (_: Exception) {
            0
        }
    }

    private fun registerCurrentDeviceTokenBestEffort(context: Context): String? {
        try {
            val chosenToken = AlarmFirebaseMessagingService.getOrFetchTokenBlocking(context, 25)
            if (chosenToken.isNullOrBlank()) {
                Log.w("WarehouseService", "No FCM token available for inline notify header")
                return null
            }

            val registerBody = JSONObject().apply { put("token", chosenToken) }.toString()
            val registerReq = auth(context, "/api/notifications/register", "POST", registerBody)
            client.newCall(registerReq).execute().use { response ->
                if (!response.isSuccessful) {
                    Log.w("WarehouseService", "FCM pre-register failed: ${response.code}")
                }
            }
            return chosenToken
        } catch (e: Exception) {
            Log.w("WarehouseService", "FCM pre-register skipped: ${e.message}")
            return AlarmFirebaseMessagingService.getCachedToken(context)
        }
    }
}