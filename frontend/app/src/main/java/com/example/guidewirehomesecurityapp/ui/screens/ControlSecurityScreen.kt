package com.example.guidewirehomesecurityapp.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import android.widget.Toast
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.guidewirehomesecurityapp.api.AlarmService
import com.example.guidewirehomesecurityapp.api.EventService
import com.example.guidewirehomesecurityapp.api.SensorEvent
import com.example.guidewirehomesecurityapp.api.WarehouseService
import com.example.guidewirehomesecurityapp.api.deriveDoorOpenStates
import com.example.guidewirehomesecurityapp.ui.components.ScreenTitleWithLogo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun ControlSecurityScreen(
    modifier: Modifier = Modifier,
    events: List<SensorEvent> = emptyList(),
) {
    val context = LocalContext.current
    var systemArmed by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(true) }
    var labels by remember { mutableStateOf<List<String>>(emptyList()) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        loading = true
        val armed = withContext(Dispatchers.IO) { AlarmService.getArmedStatus(context) }
        if (armed != null) systemArmed = armed
        labels = withContext(Dispatchers.IO) { EventService.getSensorLabels(context) }
        loading = false
        while (isActive) {
            delay(5000)
            labels = withContext(Dispatchers.IO) { EventService.getSensorLabels(context) }
        }
    }

    val (open1, open2) = remember(events) { deriveDoorOpenStates(events) }
    val name1 = labels.getOrNull(0)?.takeIf { it.isNotBlank() } ?: "Sensor 1"
    val name2 = labels.getOrNull(1)?.takeIf { it.isNotBlank() } ?: "Sensor 2"

    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .padding(20.dp)
            .verticalScroll(scrollState)
    ) {
        ScreenTitleWithLogo(
            title = "System control",
            modifier = Modifier.padding(bottom = 8.dp),
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            text = "Arm or disarm the alarm and check sensor status. Names are set by your administrator.",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
            modifier = Modifier.padding(bottom = 24.dp)
        )

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            shape = CardDefaults.elevatedShape
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Alarm system",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Text(
                        text = if (systemArmed) "Armed" else "Disarmed",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                    )
                }
                Switch(
                    checked = systemArmed,
                    onCheckedChange = { newValue ->
                        scope.launch {
                            val result = withContext(Dispatchers.IO) {
                                AlarmService.setArmedStatus(context, newValue)
                            }
                            when {
                                !result.success -> {
                                    Toast.makeText(
                                        context,
                                        "Could not update alarm",
                                        Toast.LENGTH_SHORT
                                    ).show()
                                }
                                result.pendingDisarm -> {
                                    systemArmed = true
                                    Toast.makeText(
                                        context,
                                        "Disarm request sent — the admin must approve.",
                                        Toast.LENGTH_LONG
                                    ).show()
                                }
                                result.armed != null -> systemArmed = result.armed
                            }
                        }
                    },
                    enabled = !loading,
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = MaterialTheme.colorScheme.primary,
                        checkedTrackColor = MaterialTheme.colorScheme.secondaryContainer
                    )
                )
            }

            OutlinedButton(
                onClick = {
                    if (systemArmed) {
                        Toast.makeText(context, "Disarm first, then notify admin", Toast.LENGTH_SHORT).show()
                        return@OutlinedButton
                    }
                    scope.launch {
                        val n = withContext(Dispatchers.IO) {
                            WarehouseService.notifyWarehouse(
                                context,
                                title = "Alarm is off",
                                body = "A team member reported the alarm is currently disarmed."
                            )
                        }
                        Toast.makeText(context, "Sent to $n device(s)", Toast.LENGTH_SHORT).show()
                    }
                },
                enabled = !loading,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 12.dp)
            ) {
                Text("Notify admin")
            }
        }

        Spacer(Modifier.height(24.dp))
        Text(
            text = "Sensors",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.padding(bottom = 12.dp)
        )

        listOf(
            Triple(name1, open1, "First reed (GPIO 4)"),
            Triple(name2, open2, "Second reed (GPIO 14)"),
        ).forEach { (name, isOpen, hint) ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = name,
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = when (isOpen) {
                                true -> "Open"
                                false -> "Closed"
                                null -> "—"
                            },
                            style = MaterialTheme.typography.labelLarge,
                            color = when (isOpen) {
                                true -> MaterialTheme.colorScheme.error
                                false -> MaterialTheme.colorScheme.primary
                                null -> MaterialTheme.colorScheme.onSurfaceVariant
                            }
                        )
                    }
                    Text(
                        text = hint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
            }
        }
    }
}
