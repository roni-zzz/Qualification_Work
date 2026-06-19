package com.example.guidewirehomesecurityapp.ui.screens

import android.Manifest
import android.os.Build
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.compose.material.icons.filled.AdminPanelSettings
import com.example.guidewirehomesecurityapp.api.EventService
import com.example.guidewirehomesecurityapp.api.SensorEvent
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import com.example.guidewirehomesecurityapp.notifications.AlarmFirebaseMessagingService
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext


/* ---------------- TABS ---------------- */

sealed class HomeTab(val title: String, val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    data object Home : HomeTab("Home", Icons.Filled.Home)
    data object Control : HomeTab("Control", Icons.Filled.Lock)
    data object History : HomeTab("History", Icons.Filled.History)
    data object Eco : HomeTab("Eco", Icons.Filled.Eco)
    data object Admin : HomeTab("Admin", Icons.Filled.AdminPanelSettings)
    data object Settings : HomeTab("Settings", Icons.Filled.Settings)
}

/* ---------------- SCREEN ---------------- */

@Composable
fun HomeScreen(
    modifier: Modifier = Modifier,
    onSignOut: () -> Unit = {}
) {
    var selectedIndex by rememberSaveable { mutableIntStateOf(0) }
    var events by remember { mutableStateOf<List<SensorEvent>>(emptyList()) }

    val context = LocalContext.current
    
    // Normalize roles: handle literal "null" string
    val globalRole = (BackendAuthService.getRole(context) ?: "user").lowercase().trim()
        .takeUnless { it == "null" } ?: "user"
    val warehouseRole = (BackendAuthService.getWarehouseRole(context) ?: "").lowercase().trim()
        .takeUnless { it == "null" } ?: ""

    val tabs = remember(globalRole, warehouseRole) {
        val isAdmin = globalRole == "admin" || globalRole == "manager" || 
                     warehouseRole == "admin" || warehouseRole == "manager"

        if (isAdmin) {
            listOf(
                HomeTab.Home,
                HomeTab.Control,
                HomeTab.History,
                HomeTab.Eco,
                HomeTab.Admin,
                HomeTab.Settings
            )
        } else if (warehouseRole == "worker" || warehouseRole == "contractor") {
            listOf(
                HomeTab.Home,
                HomeTab.Control,
                HomeTab.Eco,
                HomeTab.Settings
            )
        } else {
            listOf(
                HomeTab.Home,
                HomeTab.Control,
                HomeTab.History,
                HomeTab.Eco,
                HomeTab.Settings
            )
        }
    }

    LaunchedEffect(tabs.size, warehouseRole) {
        if (selectedIndex >= tabs.size) selectedIndex = 0
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) {}

    /* ---------------- NOTIFICATION PERMISSION + TOKEN ---------------- */

    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= 33) {
            when (
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS
                )
            ) {
                android.content.pm.PackageManager.PERMISSION_GRANTED -> {}
                else -> permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

            FirebaseMessaging.getInstance().token
            .addOnCompleteListener { task ->

            Log.d("FCM_DEBUG", "Token task finished")

            if (!task.isSuccessful) {
                Log.e(
                    "FCM_DEBUG",
                    "TOKEN FETCH FAILED",
                    task.exception
                )
                return@addOnCompleteListener
            }

            val token = task.result

            Log.d(
                "FCM_DEBUG",
                "TOKEN=${token?.takeLast(15)}"
            )

            AlarmFirebaseMessagingService
                .registerTokenWithBackend(
                    context,
                    token
                )
        }
    }

    /* ---------------- POLL EVENTS ---------------- */

    LaunchedEffect(Unit) {
        var tick = 0
        while (true) {
            events = withContext(Dispatchers.IO) {
                EventService.getEvents(context)
            }

            delay(3000)
            tick++

            if (tick % 10 == 0) {
                FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
                    if (task.isSuccessful) {
                        task.result?.let {
                            AlarmFirebaseMessagingService.registerTokenWithBackend(context, it)
                        }
                    }
                }
            }
        }
    }

    /* ---------------- UI ---------------- */

    Scaffold(
        modifier = modifier.fillMaxSize(),
        bottomBar = {
            NavigationBar {
                tabs.forEachIndexed { index, tab ->
                    NavigationBarItem(
                        selected = selectedIndex == index,
                        onClick = { selectedIndex = index },
                        icon = {
                            Icon(
                                imageVector = tab.icon,
                                contentDescription = tab.title
                            )
                        },
                        label = { Text(tab.title) }
                    )
                }
            }
        }
    ) { innerPadding ->

        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f),
                            MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.35f),
                            MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.25f)
                        ),
                        start = Offset(0f, 0f),
                        end = Offset(1000f, 1200f)
                    )
                )
        ) {

            AnimatedContent(
                targetState = selectedIndex,
                transitionSpec = {
                    fadeIn(animationSpec = tween(220)) togetherWith
                            fadeOut(animationSpec = tween(220))
                },
                label = "tab_transition"
            ) { index ->

                when (tabs[index]) {

                    HomeTab.Home -> HomeDashboardScreen(
                        modifier = Modifier.padding(innerPadding),
                        recentEvents = events,
                        onNavigateToControl = {
                            selectedIndex = tabs.indexOf(HomeTab.Control).coerceAtLeast(0)
                        },
                        onNavigateToHistory = {
                            val i = tabs.indexOf(HomeTab.History)
                            selectedIndex = if (i >= 0) i else 0
                        },
                        onNavigateToSustainability = {
                            selectedIndex = tabs.indexOf(HomeTab.Eco).coerceAtLeast(0)
                        },
                        onNavigateToSettings = {
                            selectedIndex = tabs.indexOf(HomeTab.Settings).coerceAtLeast(0)
                        }
                    )

                    HomeTab.Control -> ControlSecurityScreen(
                        modifier = Modifier.padding(innerPadding),
                        events = events
                    )

                    HomeTab.History -> SensorHistoryScreen(
                        modifier = Modifier.padding(innerPadding),
                        events = events
                    )

                    HomeTab.Eco -> SustainabilityScreen(
                        modifier = Modifier.padding(innerPadding)
                    )

                    HomeTab.Admin -> AdminDashboardScreen(
                        modifier = Modifier.padding(innerPadding),
                        onSignOut = onSignOut
                    )

                    HomeTab.Settings -> SettingsScreen(
                        modifier = Modifier.padding(innerPadding),
                        onSignOut = onSignOut
                    )
                }
            }
        }
    }
}
