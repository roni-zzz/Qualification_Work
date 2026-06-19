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

/** Admin-only API (requires role=admin JWT). */
object AdminService {

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    private fun baseUrl(context: Context): String =
        BackendEndpointResolver.apiBaseUrl(context)

    private fun authRequest(context: Context, path: String, method: String = "GET", body: String? = null): Request {
        val token = BackendAuthService.getToken(context) ?: ""
        val url = "${baseUrl(context)}/api/admin$path"
        val builder = Request.Builder().url(url).addHeader("Authorization", "Bearer $token")
        when (method) {
            "GET" -> builder.get()
            "POST" -> builder.post((body ?: "{}").toRequestBody("application/json".toMediaType()))
            "PUT" -> builder.put((body ?: "{}").toRequestBody("application/json".toMediaType()))
            "PATCH" -> builder.patch((body ?: "{}").toRequestBody("application/json".toMediaType()))
            "DELETE" -> builder.delete()
            else -> builder.get()
        }
        if (body != null && method != "GET")
            builder.addHeader("Content-Type", "application/json")
        return builder.build()
    }

    fun listWarehouses(context: Context): List<AdminWarehouse> = run {
        val req = authRequest(context, "/warehouses")
        try {
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val arr = JSONArray(response.body?.string() ?: "[]")
                List(arr.length()) { i ->
                    val o = arr.getJSONObject(i)
                    AdminWarehouse(
                        alarmSystemId = o.optInt("alarm_system_id", 0),
                        name = o.optString("name", ""),
                        microcontrollerId = o.optInt("microcontroller_id", 0),
                        deviceId = o.optString("device_id", ""),
                        currentState = o.optString("current_state", ""),
                        lastSeen = if (o.has("last_seen") && !o.isNull("last_seen")) o.optDouble("last_seen", 0.0) else null,
                        offline = o.optBoolean("offline", false),
                        sensorLabels = jsonArrayToStringList(o.optJSONArray("sensor_labels")),
                        userCount = o.optInt("user_count", 0)
                    )
                }
            }
        } catch (e: Exception) {
            Log.e("AdminService", "listWarehouses error", e)
            emptyList()
        }
    }

    private fun jsonArrayToStringList(arr: JSONArray?): List<String> {
        if (arr == null) return emptyList()
        return List(arr.length()) { i -> arr.optString(i, "") }
    }

    fun updateWarehouseName(context: Context, alarmSystemId: Int, name: String): Boolean = run {
        val body = JSONObject().apply { put("name", name) }.toString()
        val req = authRequest(context, "/warehouses/$alarmSystemId", "PATCH", body)
        try {
            client.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) { false }
    }

    fun deleteWarehouse(context: Context, alarmSystemId: Int): Pair<Boolean, String?> = run {
        val req = authRequest(context, "/warehouses/$alarmSystemId", "DELETE")
        try {
            client.newCall(req).execute().use { response ->
                if (response.isSuccessful) return Pair(true, null)
                val body = response.body?.string() ?: ""
                val msg = try { JSONObject(body).optString("detail", "HTTP ${response.code}") } catch (_: Exception) { "HTTP ${response.code}" }
                return Pair(false, msg)
            }
        } catch (e: Exception) { Pair(false, e.message ?: "Network error") }
    }

    data class AddWarehouseResult(val alarmSystemId: Int, val deviceId: String, val microcontrollerId: Int)

    /**
     * Create a warehouse. If [microcontrollerId] is null, we omit the key entirely
     * from the JSON payload so the backend can use its auto-assignment logic.
     */
    fun addWarehouse(context: Context, microcontrollerId: Int? = null): Boolean = run {
        val bodyJson = JSONObject()
        if (microcontrollerId != null) {
            bodyJson.put("microcontroller_id", microcontrollerId)
        }
        val body = bodyJson.toString()
        
        Log.d("AdminService", "Adding warehouse with body: $body")
        
        val req = authRequest(context, "/warehouses", "POST", body)
        client.newCall(req).execute().use { response ->
            if (!response.isSuccessful) {
                Log.e("AdminService", "Failed to add warehouse: ${response.code}")
                return false
            }
            true
        }
    }

    fun setSensorLabels(context: Context, alarmSystemId: Int, labels: List<String>): Boolean = run {
        val body = JSONObject().apply { put("labels", JSONArray(labels)) }.toString()
        val req = authRequest(context, "/warehouses/$alarmSystemId/sensors", "PUT", body)
        try { client.newCall(req).execute().use { it.isSuccessful } } catch (_: Exception) { false }
    }

    data class WarehouseUser(val id: Int, val username: String, val email: String, val phone: String, val role: String, val warehouseRole: String)
    
    fun listUsers(context: Context, alarmSystemId: Int): List<WarehouseUser> = run {
        val req = authRequest(context, "/warehouses/$alarmSystemId/users")
        try {
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val arr = JSONArray(response.body?.string() ?: "[]")
                List(arr.length()) { i ->
                    val o = arr.getJSONObject(i)
                    WarehouseUser(
                        id = o.optInt("id", 0),
                        username = o.optString("username", ""),
                        email = o.optString("email", ""),
                        phone = o.optString("phone", ""),
                        role = o.optString("role", "user"),
                        warehouseRole = o.optString("warehouse_role", "manager"),
                    )
                }
            }
        } catch (_: Exception) { emptyList() }
    }

    fun linkExistingUser(context: Context, alarmSystemId: Int, email: String, password: String?, warehouseRole: String? = null): Boolean = run {
        val body = JSONObject().apply {
            put("email", email.trim().lowercase())
            password?.trim()?.takeIf { it.isNotEmpty() }?.let { put("password", it) }
            warehouseRole?.lowercase()?.takeIf { it.isNotBlank() }?.let { put("warehouse_role", it) }
        }.toString()
        val req = authRequest(context, "/warehouses/$alarmSystemId/users/link", "POST", body)
        try { client.newCall(req).execute().use { it.isSuccessful } } catch (_: Exception) { false }
    }

    fun addUser(context: Context, alarmSystemId: Int, username: String, email: String, password: String, phone: String?, warehouseRole: String? = null): Boolean = run {
        val body = JSONObject().apply {
            put("username", username); put("email", email); put("password", password); put("phone", phone ?: "")
            warehouseRole?.lowercase()?.takeIf { it.isNotBlank() }?.let { put("warehouse_role", it) }
        }.toString()
        val req = authRequest(context, "/warehouses/$alarmSystemId/users", "POST", body)
        try { client.newCall(req).execute().use { it.isSuccessful } } catch (_: Exception) { false }
    }

    fun updateUser(context: Context, alarmSystemId: Int, userId: Int, username: String?, email: String?, phone: String?, password: String?, warehouseRole: String? = null): Boolean = run {
        val body = JSONObject().apply {
            username?.let { put("username", it) }; email?.let { put("email", it) }
            phone?.let { put("phone", it) }; password?.let { put("password", it) }
            warehouseRole?.let { put("warehouse_role", it.lowercase()) }
        }.toString()
        val req = authRequest(context, "/warehouses/$alarmSystemId/users/$userId", "PUT", body)
        try { client.newCall(req).execute().use { it.isSuccessful } } catch (_: Exception) { false }
    }

    fun removeUser(context: Context, alarmSystemId: Int, userId: Int): Boolean = run {
        val req = authRequest(context, "/warehouses/$alarmSystemId/users/$userId", "DELETE")
        try { client.newCall(req).execute().use { it.isSuccessful } } catch (_: Exception) { false }
    }

    data class OfflineDevice(val microcontrollerId: Int, val alarmSystemId: Int, val lastSeen: Double)
    fun listOffline(context: Context): List<OfflineDevice> = run {
        val req = authRequest(context, "/offline")
        try {
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) return emptyList()
                val arr = JSONArray(response.body?.string() ?: "[]")
                List(arr.length()) { i ->
                    val o = arr.getJSONObject(i)
                    OfflineDevice(microcontrollerId = o.optInt("microcontroller_id", 0), alarmSystemId = o.optInt("alarm_system_id", 0), lastSeen = o.optDouble("last_seen", 0.0))
                }
            }
        } catch (_: Exception) { emptyList() }
    }

    fun notifyAdmin(context: Context, alarmSystemId: Int, title: String, body: String): Int = run {
        val inlineFcmToken = registerCurrentDeviceTokenBestEffort(context)
        if (inlineFcmToken.isNullOrBlank()) {
            Log.w("AdminService", "notifyAdmin aborted: no FCM token available")
            return 0
        }
        val reqBody = JSONObject().apply { put("title", title); put("body", body) }.toString()
        val req = authRequest(context, "/warehouses/$alarmSystemId/notify", "POST", reqBody)
            .newBuilder()
            .apply {
                addHeader("X-FCM-Token", inlineFcmToken)
            }
            .build()
        try {
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) {
                    val errBody = response.body?.string()
                    Log.w("AdminService", "notifyAdmin failed: ${response.code} $errBody")
                    return 0
                }
                JSONObject(response.body?.string() ?: "{}").optInt("sent_to_devices", 0)
            }
        } catch (_: Exception) { 0 }
    }

    private fun registerCurrentDeviceTokenBestEffort(context: Context): String? {
        try {
            val chosenToken = AlarmFirebaseMessagingService.getOrFetchTokenBlocking(context, 25)
            if (chosenToken.isNullOrBlank()) {
                Log.w("AdminService", "No FCM token available for inline notify header")
                return null
            }

            val registerBody = JSONObject().apply { put("token", chosenToken) }.toString()
            val token = BackendAuthService.getToken(context) ?: ""
            val req = Request.Builder()
                .url("${baseUrl(context)}/api/notifications/register")
                .post(registerBody.toRequestBody("application/json".toMediaType()))
                .addHeader("Authorization", "Bearer $token")
                .addHeader("Content-Type", "application/json")
                .build()
            client.newCall(req).execute().use { response ->
                if (!response.isSuccessful) {
                    Log.w("AdminService", "FCM pre-register failed: ${response.code}")
                }
            }
            return chosenToken
        } catch (e: Exception) {
            Log.w("AdminService", "FCM pre-register skipped: ${e.message}")
            return AlarmFirebaseMessagingService.getCachedToken(context)
        }
    }
}

data class AdminWarehouse(val alarmSystemId: Int, val name: String, val microcontrollerId: Int, val deviceId: String, val currentState: String, val lastSeen: Double?, val offline: Boolean, val sensorLabels: List<String>, val userCount: Int)
