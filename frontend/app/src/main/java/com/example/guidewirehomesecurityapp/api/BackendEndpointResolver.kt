package com.example.guidewirehomesecurityapp.api

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.util.Log
import com.example.guidewirehomesecurityapp.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import java.net.Inet4Address
import java.net.NetworkInterface
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Resolves backend URL dynamically on local Wi-Fi/hotspot networks.
 *
 * Behavior:
 * - **Emulator + backend on this PC:** if API_BASE_URL host is localhost/127.0.0.1, uses `10.0.2.2`
 *   (AVD alias for the host) with the same port.
 * - **Emulator + backend elsewhere:** tries API_BASE_URL first; if `/health` fails (common when the
 *   PC is not on the Pi/hotspot LAN), tries `10.0.2.2:PORT` so the API can be reached via the dev PC
 *   (backend or proxy listening on that port on the host).
 * - **API_BASE_URL_ALT** (optional in local.properties): second base URL tried in order (e.g. mDNS
 *   `http://sweng-pi.local:8000/api/` vs a DHCP IP). Same LAN for demo: Pi can advertise
 *   `.local` via Avahi; keep primary IP as backup.
 * - Uses API_BASE_URL from local.properties as fallback.
 * - Tries previously discovered host first (per subnet).
 * - If unreachable, scans current /24 subnet for /health on same port (skipped on emulator when URL is remote).
 */
object BackendEndpointResolver {
    private const val TAG = "BackendEndpointResolver"
    private const val PREFS_NAME = "backend_endpoint_prefs"
    private const val KEY_HOST = "host"
    private const val KEY_SUBNET = "subnet"
    private const val SCAN_THREADS = 48

    @Volatile private var cachedApiBase: String? = null

    private val probeClient = OkHttpClient.Builder()
        .connectTimeout(3000, TimeUnit.MILLISECONDS)
        .readTimeout(3000, TimeUnit.MILLISECONDS)
        .writeTimeout(3000, TimeUnit.MILLISECONDS)
        .build()

    fun apiBaseUrl(context: Context): String {
        cachedApiBase?.let {
            if (isHealthy(it)) return it
            cachedApiBase = null
        }

        val candidates = apiBaseCandidates()
        val primaryBase = candidates.firstOrNull()
            ?: normalizeApiBase(BuildConfig.API_BASE_URL)
        val fallbackHttp = primaryBase.toHttpUrlOrNull() ?: return primaryBase

        // AVD: 10.0.2.2 reaches the *development machine* only — not a Pi/phone on another network.
        if (isAndroidEmulator() && isLocalBackendHost(fallbackHttp.host)) {
            val emulatorBase = buildBase(fallbackHttp, "10.0.2.2")
            if (isHealthy(emulatorBase)) {
                cachedApiBase = emulatorBase
                Log.d(TAG, "Emulator: backend at host loopback $emulatorBase (same port as API_BASE_URL)")
                return emulatorBase
            }
            Log.w(
                TAG,
                "Emulator: cannot reach $emulatorBase/health — run backend on this PC or fix port; trying normal fallback"
            )
        }

        // Emulator virtual network is 10.0.2.0/24; scanning it never finds a remote server.
        val subnetPrefixes = if (isAndroidEmulator() && !isLocalBackendHost(fallbackHttp.host)) {
            Log.d(
                TAG,
                "Emulator: remote API host ${fallbackHttp.host}; skipping LAN subnet scan (use BuildConfig URL or same-network routing)"
            )
            emptyList()
        } else {
            candidateSubnetPrefixes(context)
        }
        val primarySubnet = subnetPrefixes.firstOrNull()

        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val rememberedHost = prefs.getString(KEY_HOST, null)
        val rememberedSubnet = prefs.getString(KEY_SUBNET, null)

        if (!primarySubnet.isNullOrBlank() && rememberedHost != null && rememberedSubnet == primarySubnet) {
            val rememberedBase = buildBase(fallbackHttp, rememberedHost)
            if (isHealthy(rememberedBase)) {
                cachedApiBase = rememberedBase
                Log.d(TAG, "Using remembered backend host: $rememberedBase")
                return rememberedBase
            }
        }

        // Try each configured URL (API_BASE_URL, then optional API_BASE_URL_ALT)
        for (base in candidates) {
            if (isHealthy(base)) {
                cachedApiBase = base
                Log.d(TAG, "Using backend base from BuildConfig: $base")
                return base
            }
        }

        // AVD often cannot route to a LAN/hotspot IP (PC not on that network). Same port on 10.0.2.2
        // reaches the dev machine — use if the API is bound there or proxied (e.g. ssh -L, socat).
        if (isAndroidEmulator() && !isLocalBackendHost(fallbackHttp.host)) {
            val viaDevHost = buildBase(fallbackHttp, "10.0.2.2")
            if (isHealthy(viaDevHost)) {
                cachedApiBase = viaDevHost
                Log.d(
                    TAG,
                    "Emulator: BuildConfig host unreachable; using dev host $viaDevHost " +
                        "(run API on this PC that port, or forward host:${fallbackHttp.port} → server)"
                )
                return viaDevHost
            }
            Log.w(
                TAG,
                "Emulator: cannot reach $candidates or $viaDevHost (/health). " +
                    "Put this PC on the same Wi‑Fi/hotspot as the server, or listen on host:${fallbackHttp.port} " +
                    "and retry (10.0.2.2 maps emulator → this PC). Or test on a physical phone on the server LAN."
            )
        }

        for (subnetPrefix in subnetPrefixes) {
            discoverInSubnet(context, subnetPrefix, fallbackHttp)?.let { discoveredBase ->
                val host = discoveredBase.toHttpUrlOrNull()?.host
                if (!host.isNullOrBlank()) {
                    prefs.edit()
                        .putString(KEY_HOST, host)
                        .putString(KEY_SUBNET, subnetPrefix)
                        .apply()
                }
                cachedApiBase = discoveredBase
                Log.d(TAG, "Discovered backend host dynamically on $subnetPrefix: $discoveredBase")
                return discoveredBase
            }
        }

        val fallbackReturn = candidates.firstOrNull() ?: primaryBase
        cachedApiBase = fallbackReturn
        Log.w(TAG, "Backend discovery failed; falling back to BuildConfig host: $fallbackReturn")
        return fallbackReturn
    }

    fun imageBaseUrl(context: Context): String {
        val fallbackImage = BuildConfig.IMAGE_BASE_URL.trimEnd('/')
        val imageHttp = fallbackImage.toHttpUrlOrNull() ?: return fallbackImage
        val apiHttp = apiBaseUrl(context).toHttpUrlOrNull() ?: return fallbackImage
        return imageHttp.newBuilder()
            .scheme(apiHttp.scheme)
            .host(apiHttp.host)
            .port(apiHttp.port)
            .build()
            .toString()
            .trimEnd('/')
    }

    private fun normalizeApiBase(raw: String): String =
        raw.trim().trimEnd('/').removeSuffix("/api")

    /** Ordered list: primary [API_BASE_URL], optional [API_BASE_URL_ALT]. */
    private fun apiBaseCandidates(): List<String> {
        val primary = normalizeApiBase(BuildConfig.API_BASE_URL)
        val alt = normalizeApiBase(BuildConfig.API_BASE_URL_ALT)
        return buildList {
            if (primary.isNotBlank()) add(primary)
            if (alt.isNotBlank() && alt != primary) add(alt)
        }
    }

    private fun discoverInSubnet(
        context: Context,
        subnetPrefix: String,
        fallbackHttp: okhttp3.HttpUrl
    ): String? {
        val ownLastOctet: Int? = null

        val pool = Executors.newFixedThreadPool(SCAN_THREADS)
        return try {
            val completion = java.util.concurrent.ExecutorCompletionService<String?>(pool)
            var taskCount = 0
            for (hostOctet in 1..254) {
                if (hostOctet == ownLastOctet) continue
                val host = "$subnetPrefix.$hostOctet"
                completion.submit(Callable {
                    val candidateBase = buildBase(fallbackHttp, host)
                    if (isHealthy(candidateBase)) candidateBase else null
                })
                taskCount++
            }

            repeat(taskCount) {
                val found = completion.take().get()
                if (found != null) return found
            }
            null
        } catch (_: Exception) {
            null
        } finally {
            pool.shutdownNow()
        }
    }

    private fun isHealthy(base: String): Boolean {
        val request = Request.Builder()
            .url("${base.trimEnd('/')}/health")
            .get()
            .build()
        return try {
            probeClient.newCall(request).execute().use { response -> response.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    private fun buildBase(fallbackHttp: okhttp3.HttpUrl, host: String): String =
        fallbackHttp.newBuilder()
            .host(host)
            .build()
            .toString()
            .trimEnd('/')
            .removeSuffix("/api")

    private fun candidateSubnetPrefixes(context: Context): List<String> {
        val ips = linkedSetOf<String>()

        val fromActiveNetwork = try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val active = cm.activeNetwork
            val props = active?.let { cm.getLinkProperties(it) }
            if (props == null) {
                null
            } else {
                props.linkAddresses
                    .asSequence()
                    .mapNotNull { it.address as? Inet4Address }
                    .map { it.hostAddress }
                    .firstOrNull { ip ->
                        ip != null &&
                            !ip.startsWith("127.") &&
                            !ip.startsWith("169.254.")
                    }
            }
        } catch (_: Exception) {
            null
        }
        fromActiveNetwork?.let { ips += it }

        // If active network points elsewhere (e.g. cellular), prefer any Wi-Fi transport network.
        val fromWifiNetworks = try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            cm.allNetworks
                .asSequence()
                .filter { network ->
                    cm.getNetworkCapabilities(network)
                        ?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true
                }
                .mapNotNull { network ->
                    cm.getLinkProperties(network)
                        ?.linkAddresses
                        ?.asSequence()
                        ?.mapNotNull { it.address as? Inet4Address }
                        ?.map { it.hostAddress }
                        ?.firstOrNull { ip ->
                            ip != null &&
                                !ip.startsWith("127.") &&
                                !ip.startsWith("169.254.")
                        }
                }
                .toList()
        } catch (_: Exception) {
            emptyList()
        }
        ips += fromWifiNetworks

        // Add every private IPv4 seen on interfaces (helps hotspot host mode).
        ips += fallbackIpv4Addresses()

        val subnets = ips
            .mapNotNull { ip ->
                ip.split('.')
                    .takeIf { it.size == 4 }
                    ?.take(3)
                    ?.joinToString(".")
            }
            .distinct()

        Log.d(TAG, "Candidate subnets for backend discovery: $subnets")
        return subnets
    }

    private fun fallbackIpv4Address(): String? {
        return try {
            val interfaces = NetworkInterface.getNetworkInterfaces()?.toList().orEmpty()
            interfaces
                .asSequence()
                .filter { !it.isLoopback && it.isUp }
                .flatMap { it.inetAddresses.toList().asSequence() }
                .filterIsInstance<Inet4Address>()
                .map { it.hostAddress }
                .firstOrNull { ip ->
                    ip != null &&
                        !ip.startsWith("127.") &&
                        !ip.startsWith("169.254.")
                }
        } catch (_: Exception) {
            null
        }
    }

    private fun fallbackIpv4Addresses(): List<String> {
        return try {
            val interfaces = NetworkInterface.getNetworkInterfaces()?.toList().orEmpty()
            interfaces
                .asSequence()
                .filter { !it.isLoopback && it.isUp }
                .flatMap { it.inetAddresses.toList().asSequence() }
                .filterIsInstance<Inet4Address>()
                .mapNotNull { it.hostAddress }
                .filter { ip ->
                    !ip.startsWith("127.") &&
                        !ip.startsWith("169.254.") &&
                        isPrivateIpv4(ip)
                }
                .distinct()
                .toList()
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun isPrivateIpv4(ip: String): Boolean {
        val parts = ip.split('.')
        if (parts.size != 4) return false
        val first = parts[0].toIntOrNull() ?: return false
        val second = parts[1].toIntOrNull() ?: return false
        return when {
            first == 10 -> true
            first == 172 && second in 16..31 -> true
            first == 192 && second == 168 -> true
            else -> false
        }
    }

    /** True when API_BASE_URL points at "this machine" for emulator → 10.0.2.2 mapping. */
    private fun isLocalBackendHost(host: String?): Boolean {
        if (host.isNullOrBlank()) return true
        val h = host.lowercase()
        return h == "localhost" || h == "127.0.0.1" || h == "::1" || h == "10.0.2.2"
    }

    /** Official AVD / common emulator images (not 100% of third-party emulators). */
    private fun isAndroidEmulator(): Boolean {
        return Build.FINGERPRINT.startsWith("generic")
            || Build.FINGERPRINT.startsWith("unknown")
            || Build.MODEL.contains("google_sdk")
            || Build.MODEL.lowercase().contains("droid4x")
            || Build.MODEL.contains("Emulator")
            || Build.MODEL.contains("Android SDK built for x86")
            || Build.MANUFACTURER.contains("Genymotion")
            || Build.HARDWARE.contains("goldfish")
            || Build.HARDWARE.contains("ranchu")
            || Build.PRODUCT.contains("sdk_google")
            || Build.PRODUCT.contains("google_sdk")
            || Build.PRODUCT.contains("sdk_gphone")
            || Build.PRODUCT.contains("emulator")
            || Build.PRODUCT.contains("simulator")
    }
}
