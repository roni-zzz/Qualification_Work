package com.example.guidewirehomesecurityapp.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.google.firebase.messaging.FirebaseMessaging
import com.google.android.gms.tasks.Tasks
import kotlin.concurrent.thread
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import com.example.guidewirehomesecurityapp.api.BackendEndpointResolver
import com.example.guidewirehomesecurityapp.auth.BackendAuthService

class AlarmFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d("FCM", "New token received: ...${token.takeLast(10)}")
        registerTokenWithBackend(applicationContext, token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val title = message.notification?.title
            ?: message.data["title"]
            ?: "Sensor event"

        val body = message.notification?.body
            ?: message.data["body"]
            ?: ""

        Log.d("FCM", "Message received: $title - $body")

        showNotification(title, body)
    }

    private fun showNotification(title: String, body: String) {
        val channelId = "alarm_channel"

        val notificationManager =
            getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Alarm Notifications",
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(this)
            .notify(System.currentTimeMillis().toInt(), notification)
    }

    companion object {

        private const val TAG = "FCM_REGISTER"
        private const val PREFS_NAME = "fcm_prefs"
        private const val KEY_LAST_FCM_TOKEN = "last_fcm_token"

        private val client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .writeTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .build()

        /**
         * CALL THIS AFTER LOGIN
         */
        fun registerTokenAfterLogin(context: android.content.Context) {
            val appContext = context.applicationContext

            FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
                Log.d(TAG, "Fetched token: ...${token.takeLast(10)}")
                registerTokenWithBackend(appContext, token)
            }.addOnFailureListener {
                Log.e(TAG, "Token fetch failed", it)
            }
        }

        /**
         * Sends token to backend
         */
        fun registerTokenWithBackend(context: android.content.Context, token: String) {
            if (token.length < 20) {
                Log.e(TAG, "Token looks invalid/too short (${token.length}), skipping register")
                return
            }

            val jwt = BackendAuthService.getToken(context)
            Log.d(
                TAG,
                "JWT exists = ${!jwt.isNullOrBlank()}"
            )

            Log.d(
            TAG,
            "Registering token ending ${token.takeLast(10)}"
            )
            if (jwt.isNullOrBlank()) {
                Log.e(TAG, "No JWT - cannot register token")
                return
            }

            context.applicationContext
                .getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_LAST_FCM_TOKEN, token)
                .apply()

            thread {
                try {
                    val url = "${BackendEndpointResolver.apiBaseUrl(context)}/api/notifications/register"

                    val bodyJson = JSONObject()
                        .put("token", token)
                        .toString()
                        .toRequestBody("application/json".toMediaType())

                    val request = Request.Builder()
                        .url(url)
                        .post(bodyJson)
                        .addHeader("Authorization", "Bearer $jwt")
                        .addHeader("Content-Type", "application/json")
                        .build()

                    val response = client.newCall(request).execute()
                    val responseBody = response.body?.string()

                    if (response.isSuccessful) {
                        Log.d(TAG, "Token registered OK")
                    } else {
                        Log.e(TAG, "Register failed: ${response.code} $responseBody")
                    }

                } catch (e: Exception) {
                    Log.e(TAG, "Token register exception", e)
                }
            }
        }

        fun getCachedToken(context: android.content.Context): String? {
            return context.applicationContext
                .getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)
                .getString(KEY_LAST_FCM_TOKEN, null)
                ?.trim()
                ?.takeIf { it.isNotEmpty() }
        }

        fun getOrFetchTokenBlocking(
            context: android.content.Context,
            timeoutSeconds: Long = 25,
        ): String? {
            val appContext = context.applicationContext
            try {
                val task = FirebaseMessaging.getInstance().token
                val fetched = Tasks.await(task, timeoutSeconds, TimeUnit.SECONDS)
                    ?.trim()
                    ?.takeIf { it.isNotEmpty() }
                if (!fetched.isNullOrBlank()) {
                    Log.d(TAG, "Blocking token fetched: ...${fetched.takeLast(10)}")
                    registerTokenWithBackend(appContext, fetched)
                    return fetched
                }
            } catch (e: Exception) {
                Log.e(TAG, "Blocking token fetch failed", e)
            }

            val cached = getCachedToken(appContext)
            if (!cached.isNullOrBlank()) {
                Log.d(TAG, "Using cached token fallback: ...${cached.takeLast(10)}")
            }
            return cached
        }
    }
}