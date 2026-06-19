package com.example.guidewirehomesecurityapp.auth

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import com.example.guidewirehomesecurityapp.api.BackendEndpointResolver
import kotlin.concurrent.thread
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

private const val PREFS_NAME = "auth_prefs"
private const val KEY_JWT = "jwt"
private const val KEY_ROLE = "role"
private const val KEY_USERNAME = "username"
private const val KEY_WAREHOUSE_ROLE = "warehouse_role"

object BackendAuthService {

    private fun prefs(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    /** Cleans up "null" strings and whitespace. */
    private fun sanitize(value: String?): String? {
        val v = value?.trim() ?: return null
        if (v.isEmpty() || v.lowercase() == "null") return null
        return v
    }

    fun saveToken(
        context: Context,
        token: String,
        role: String? = null,
        username: String? = null,
        warehouseRole: String? = null
    ) {
        val sRole = sanitize(role) ?: "user"
        val sWarehouseRole = sanitize(warehouseRole) ?: ""
        
        Log.d("BackendAuth", "Saving Session - Global: $sRole, Warehouse: $sWarehouseRole")
        
        prefs(context).edit()
            .putString(KEY_JWT, token)
            .putString(KEY_ROLE, sRole)
            .putString(KEY_USERNAME, username ?: "")
            .putString(KEY_WAREHOUSE_ROLE, sWarehouseRole)
            .apply()
    }

    fun getToken(context: Context): String? = sanitize(prefs(context).getString(KEY_JWT, null))
    fun getRole(context: Context): String? = sanitize(prefs(context).getString(KEY_ROLE, null))
    fun getUsername(context: Context): String? = sanitize(prefs(context).getString(KEY_USERNAME, null))
    fun getWarehouseRole(context: Context): String? = sanitize(prefs(context).getString(KEY_WAREHOUSE_ROLE, null))

    fun clearToken(context: Context) {
        prefs(context).edit().clear().apply()
        Log.d("BackendAuth", "Session cleared")
    }

    private fun extractRole(user: JSONObject?): String? {
        if (user == null) return null
        // Check warehouse_role, then global role.
        return sanitize(user.optString("warehouse_role", ""))
            ?: sanitize(user.optString("role", ""))
    }

    private fun processLogin(context: Context, body: String, onSuccess: () -> Unit) {
        try {
            val obj = JSONObject(body)
            val jwt = obj.optString("token", "").takeIf { it.isNotBlank() }
            val user = obj.optJSONObject("user")
            val username = sanitize(user?.optString("name", ""))
            val globalRole = sanitize(user?.optString("role", "user"))
            val warehouseRole = extractRole(user)

            Log.d("BackendAuth", "Login response roles - Global: $globalRole, Warehouse: $warehouseRole")

            Log.d("JWT_DEBUG", "JWT = $jwt")
            if (jwt != null) {
                saveToken(context, jwt, globalRole, username, warehouseRole)
                android.os.Handler(android.os.Looper.getMainLooper()).post { onSuccess() }
            }
        } catch (e: Exception) {
            Log.e("BackendAuth", "Error processing login", e)
        }
    }

    private fun request(context: Context, path: String, idToken: String, onSuccess: () -> Unit, onError: (String) -> Unit) {
        thread {
            try {
                val json = JSONObject().apply { put("idToken", idToken) }
                val body = json.toString().toRequestBody("application/json".toMediaType())
                val url = "${BackendEndpointResolver.apiBaseUrl(context)}/api$path"
                val request = Request.Builder().url(url).post(body).addHeader("Content-Type", "application/json").build()
                val client = OkHttpClient.Builder().connectTimeout(15, java.util.concurrent.TimeUnit.SECONDS).build()
                val response = client.newCall(request).execute()
                val bodyStr = response.body?.string() ?: ""
                if (response.isSuccessful) {
                    processLogin(context, bodyStr, onSuccess)
                } else {
                    onError(try { JSONObject(bodyStr).optString("detail", "Error") } catch (_: Exception) { "HTTP ${response.code}" })
                }
            } catch (e: Exception) {
                onError("Network error: ${e.message}")
            }
        }
    }

    fun signUp(context: Context, idToken: String, onSuccess: () -> Unit, onError: (String) -> Unit) {
        request(context, "/auth/signup", idToken, onSuccess, onError)
    }

    fun signIn(context: Context, idToken: String, onSuccess: () -> Unit, onMfaRequired: (String) -> Unit, onError: (String) -> Unit) {
        thread {
            try {
                val json = JSONObject().apply { put("idToken", idToken) }
                val url = "${BackendEndpointResolver.apiBaseUrl(context)}/api/auth/signin"
                val body = json.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder().url(url).post(body).addHeader("Content-Type", "application/json").build()
                val client = OkHttpClient.Builder().connectTimeout(15, java.util.concurrent.TimeUnit.SECONDS).build()
                val response = client.newCall(request).execute()
                val bodyStr = response.body?.string() ?: ""
                if (response.isSuccessful) {
                    val obj = JSONObject(bodyStr)
                    if (obj.has("token")) {
                        processLogin(context, bodyStr, onSuccess)
                    } else if (obj.optBoolean("mfa_required", false)) {
                        android.os.Handler(android.os.Looper.getMainLooper()).post {
                            onMfaRequired(obj.optString("email"))
                        }
                    }
                } else {
                    val msg = try { JSONObject(bodyStr).optString("detail", "HTTP ${response.code}") } catch (_: Exception) { "HTTP ${response.code}" }
                    android.os.Handler(android.os.Looper.getMainLooper()).post { onError(msg) }
                }
            } catch (e: Exception) {
                android.os.Handler(android.os.Looper.getMainLooper()).post { onError(e.message ?: "Error") }
            }
        }
    }

    fun verifyOtp(context: Context, email: String, code: String, onSuccess: () -> Unit, onError: (String) -> Unit) {
        thread {
            try {
                val json = JSONObject().apply { put("email", email); put("code", code) }
                val url = "${BackendEndpointResolver.apiBaseUrl(context)}/api/auth/verify-otp"
                val body = json.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder().url(url).post(body).addHeader("Content-Type", "application/json").build()
                val response = OkHttpClient().newCall(request).execute()
                val bodyStr = response.body?.string() ?: ""
                if (response.isSuccessful) {
                    processLogin(context, bodyStr, onSuccess)
                } else {
                    android.os.Handler(android.os.Looper.getMainLooper()).post { onError("Invalid code") }
                }
            } catch (e: Exception) {
                android.os.Handler(android.os.Looper.getMainLooper()).post { onError("Network error") }
            }
        }
    }

    fun signInWithEmail(context: Context, email: String, password: String, onSuccess: () -> Unit, onError: (String) -> Unit) {
        thread {
            try {
                val json = JSONObject().apply { put("email", email.trim()); put("password", password) }
                val url = "${BackendEndpointResolver.apiBaseUrl(context)}/api/auth/login"
                val body = json.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder().url(url).post(body).addHeader("Content-Type", "application/json").build()
                val response = OkHttpClient().newCall(request).execute()
                val bodyStr = response.body?.string() ?: ""
                if (response.isSuccessful) {
                    processLogin(context, bodyStr, onSuccess)
                } else {
                    val msg = try { JSONObject(bodyStr).optString("detail", "Login failed") } catch (_: Exception) { "Login failed" }
                    android.os.Handler(android.os.Looper.getMainLooper()).post { onError(msg) }
                }
            } catch (e: Exception) {
                android.os.Handler(android.os.Looper.getMainLooper()).post { onError("Network error") }
            }
        }
    }

    fun clearAuthData(context: Context) {}
}
