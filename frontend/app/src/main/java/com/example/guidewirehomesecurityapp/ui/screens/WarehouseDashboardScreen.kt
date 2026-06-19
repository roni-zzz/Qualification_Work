package com.example.guidewirehomesecurityapp.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.People
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.guidewirehomesecurityapp.api.AlarmService
import com.example.guidewirehomesecurityapp.api.EventService
import com.example.guidewirehomesecurityapp.api.SensorEvent
import com.example.guidewirehomesecurityapp.api.deriveDoorOpenStates
import com.example.guidewirehomesecurityapp.ui.components.ScreenTitleWithLogo
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext

private const val CARD_HEIGHT_DP = 200
private const val ECO_OFFLINE_SECONDS = 300.0

@Composable
fun HomeDashboardScreen(
    modifier: Modifier = Modifier,
    recentEvents: List<SensorEvent> = emptyList(),
    onNavigateToControl: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onNavigateToSustainability: () -> Unit,
    onNavigateToSettings: () -> Unit
) {
    val context = LocalContext.current
    var systemArmed by remember { mutableStateOf<Boolean?>(null) }
    var sensorLabels by remember { mutableStateOf<List<String>>(emptyList()) }
    var powerSamples by remember { mutableStateOf<List<EventService.PowerSample>>(emptyList()) }

    LaunchedEffect(Unit) {
        while (isActive) {
            val armed = withContext(Dispatchers.IO) { AlarmService.getArmedStatus(context) }
            val labels = withContext(Dispatchers.IO) { EventService.getSensorLabels(context) }
            val power = withContext(Dispatchers.IO) { EventService.getPowerRecent(context) }
            systemArmed = armed
            sensorLabels = labels
            powerSamples = power
            delay(3000)
        }
    }

    val previewEvents = remember(recentEvents) {
        recentEvents
            .asSequence()
            .filter { it.event_type != "current_power_usage" }
            .sortedByDescending { it.timestamp }
            .take(2)
            .toList()
    }

    val (open1, open2) = remember(recentEvents) { deriveDoorOpenStates(recentEvents) }
    val name1 = sensorLabels.getOrNull(0)?.takeIf { it.isNotBlank() } ?: "Sensor 1"
    val name2 = sensorLabels.getOrNull(1)?.takeIf { it.isNotBlank() } ?: "Sensor 2"

    fun sensorLine(which: Int, open: Boolean?): String {
        val label = if (which == 1) name1 else name2
        val state = when (open) {
            null -> "Unknown"
            true -> "Open"
            false -> "Closed"
        }
        return "$label: $state"
    }

    val alarmLine = when (systemArmed) {
        null -> "Alarm: …"
        true -> "Alarm: Armed"
        false -> "Alarm: Disarmed"
    }

    val latestPowerRaw = powerSamples.maxByOrNull { it.timestamp }
    val nowSec = System.currentTimeMillis() / 1000.0
    val ecoDataFresh = latestPowerRaw?.let { nowSec - it.timestamp <= ECO_OFFLINE_SECONDS } ?: false
    val latestPower = if (ecoDataFresh) latestPowerRaw else null
    val peakMa = if (ecoDataFresh) powerSamples.maxOfOrNull { it.valueMa } else null

    val cards = listOf(
        DashboardPreviewItem(
            title = "Control system",
            icon = Icons.Filled.Lock,
            onClick = onNavigateToControl,
            previewContent = {
                Text(
                    alarmLine,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    sensorLine(1, open1),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    sensorLine(2, open2),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        ),
        DashboardPreviewItem(
            title = "Sensor history",
            icon = Icons.Filled.History,
            onClick = onNavigateToHistory,
            previewContent = {
                if (previewEvents.isEmpty()) {
                    Text(
                        "No recent events",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                } else {
                    previewEvents.forEach { event ->
                        val timeStr = try {
                            SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date((event.timestamp * 1000).toLong()))
                        } catch (_: Exception) {
                            "—"
                        }
                        Text(
                            "${event.displayType(sensorLabels)} · $timeStr",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
        ),
        DashboardPreviewItem(
            title = "Eco",
            icon = Icons.Filled.Eco,
            onClick = onNavigateToSustainability,
            previewContent = {
                if (latestPower != null) {
                    Text(
                        "%.0f mA · %s".format(latestPower.valueMa, latestPower.deviceId),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    val peakText = peakMa?.let { p -> "Peak (sample): %.0f mA".format(p) }
                        ?: "Live draw from your nodes"
                    Text(
                        peakText,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                } else {
                    Text(
                        "No power data yet",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        "Open Eco for the live chart",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        ),
        DashboardPreviewItem(
            title = "Manage authorized users",
            icon = Icons.Filled.People,
            onClick = onNavigateToSettings,
            previewContent = {
                Text(
                    "Account & app settings",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    "Sign out and preferences",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        )
    )

    Column(modifier = modifier.padding(20.dp)) {
        ScreenTitleWithLogo(
            title = "Guidewire SafeWarehouse",
            modifier = Modifier.padding(bottom = 6.dp)
        )
        Text(
            text = "Keeping your warehouse safe and secure",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f),
            modifier = Modifier.padding(bottom = 24.dp)
        )
        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            contentPadding = PaddingValues(0.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(cards) { card ->
                DashboardCard(
                    title = card.title,
                    icon = card.icon,
                    previewContent = card.previewContent,
                    onClick = card.onClick
                )
            }
        }
    }
}

private data class DashboardPreviewItem(
    val title: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val previewContent: @Composable () -> Unit,
    val onClick: () -> Unit
)

@Composable
private fun DashboardCard(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    previewContent: @Composable () -> Unit,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .height(CARD_HEIGHT_DP.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f)
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(28.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                previewContent()
            }
        }
    }
}
