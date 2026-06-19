package com.example.guidewirehomesecurityapp.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.rememberDatePickerState
import com.example.guidewirehomesecurityapp.api.EventService
import com.example.guidewirehomesecurityapp.api.SensorEvent
import com.example.guidewirehomesecurityapp.ui.components.ScreenTitleWithLogo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun SensorHistoryScreen(
    modifier: Modifier = Modifier,
    events: List<SensorEvent> = emptyList()
) {
    val context = LocalContext.current
    var sensorLabels by remember { mutableStateOf<List<String>>(emptyList()) }
    LaunchedEffect(Unit) {
        sensorLabels = withContext(Dispatchers.IO) { EventService.getSensorLabels(context) }
        while (isActive) {
            delay(5000)
            sensorLabels = withContext(Dispatchers.IO) { EventService.getSensorLabels(context) }
        }
    }

    val dateFormatter = remember { SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()) }
    val todayString = remember { dateFormatter.format(Date()) }

    var selectedType by remember { mutableStateOf("all") }
    var fromDateText by remember { mutableStateOf(todayString) }
    var toDateText by remember { mutableStateOf(todayString) }

    var showFromPicker by remember { mutableStateOf(false) }
    var showToPicker by remember { mutableStateOf(false) }

    val fromDateState = rememberDatePickerState()
    val toDateState = rememberDatePickerState()

    fun parseDateToEpoch(dateStr: String): Double? =
        try {
            val trimmed = dateStr.trim()
            if (trimmed.isEmpty()) null
            else {
                val d = dateFormatter.parse(trimmed)
                d?.time?.div(1000.0)
            }
        } catch (_: Exception) {
            null
        }

    val startEpoch = parseDateToEpoch(fromDateText)
    // Treat "to" as inclusive for the whole day
    val endEpochExclusive = parseDateToEpoch(toDateText)?.let { it + 24 * 60 * 60 }

    val filteredEvents = events
        .asSequence()
        .filter { it.event_type != "current_power_usage" }
        .filter { event ->
            when (selectedType) {
                "all" -> true
                "alarm" -> event.event_type == "alarm_enabled" || event.event_type == "alarm_disabled"
                "door_open" ->
                    event.event_type == "door_open" || event.event_type == "door_open_2"
                "door_closed" ->
                    event.event_type == "door_closed" || event.event_type == "door_closed_2"
                else -> event.event_type == selectedType
            }
        }
        .filter { event ->
            (startEpoch == null || event.timestamp >= startEpoch) &&
                (endEpochExclusive == null || event.timestamp < endEpochExclusive)
        }
        .sortedByDescending { it.timestamp }
        .toList()

    Box(
        modifier = modifier
            .fillMaxSize()
            .padding(20.dp)
    ) {
        if (showFromPicker) {
            DatePickerDialog(
                onDismissRequest = { showFromPicker = false },
                confirmButton = {
                    androidx.compose.material3.TextButton(
                        onClick = {
                            val millis = fromDateState.selectedDateMillis
                            if (millis != null) {
                                fromDateText = dateFormatter.format(Date(millis))
                            }
                            showFromPicker = false
                        }
                    ) {
                        Text("OK")
                    }
                },
                dismissButton = {
                    androidx.compose.material3.TextButton(onClick = { showFromPicker = false }) {
                        Text("Cancel")
                    }
                }
            ) {
                DatePicker(state = fromDateState)
            }
        }

        if (showToPicker) {
            DatePickerDialog(
                onDismissRequest = { showToPicker = false },
                confirmButton = {
                    androidx.compose.material3.TextButton(
                        onClick = {
                            val millis = toDateState.selectedDateMillis
                            if (millis != null) {
                                toDateText = dateFormatter.format(Date(millis))
                            }
                            showToPicker = false
                        }
                    ) {
                        Text("OK")
                    }
                },
                dismissButton = {
                    androidx.compose.material3.TextButton(onClick = { showToPicker = false }) {
                        Text("Cancel")
                    }
                }
            ) {
                DatePicker(state = toDateState)
            }
        }

        if (events.isEmpty()) {
            Text(
                text = "No sensor events yet. Open or close a door on your ESP32 to see history here.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                modifier = Modifier.align(Alignment.Center)
            )
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                item {
                    Column(
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        ScreenTitleWithLogo(
                            title = "Sensor activation history",
                            modifier = Modifier.padding(bottom = 4.dp)
                        )
                        Text(
                            text = "Review all past door and sensor events. Filter by type or date range.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                            modifier = Modifier.padding(bottom = 12.dp)
                        )

                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            HistoryTypeChip(
                                label = "All",
                                value = "all",
                                selectedType = selectedType,
                                onSelected = { selectedType = it }
                            )
                            HistoryTypeChip(
                                label = "Opened",
                                value = "door_open",
                                selectedType = selectedType,
                                onSelected = { selectedType = it }
                            )
                            HistoryTypeChip(
                                label = "Closed",
                                value = "door_closed",
                                selectedType = selectedType,
                                onSelected = { selectedType = it }
                            )
                            HistoryTypeChip(
                                label = "Armed/Disarmed",
                                value = "alarm",
                                selectedType = selectedType,
                                onSelected = { selectedType = it }
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            OutlinedTextField(
                                value = fromDateText,
                                onValueChange = { },
                                label = { Text("From (YYYY-MM-DD)") },
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable { showFromPicker = true },
                                readOnly = true,
                                singleLine = true
                            )
                            OutlinedTextField(
                                value = toDateText,
                                onValueChange = { },
                                label = { Text("To (YYYY-MM-DD)") },
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable { showToPicker = true },
                                readOnly = true,
                                singleLine = true
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        Text(
                            text = "Showing ${filteredEvents.size} event(s)",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                items(filteredEvents) { event ->
                    SensorHistoryEventCard(event = event, sensorLabels = sensorLabels)
                }
            }
        }
    }
}

@Composable
private fun HistoryTypeChip(
    label: String,
    value: String,
    selectedType: String,
    onSelected: (String) -> Unit
) {
    FilterChip(
        selected = selectedType == value,
        onClick = { onSelected(value) },
        label = { Text(label) },
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
            selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
        )
    )
}

@Composable
private fun SensorHistoryEventCard(event: SensorEvent, sensorLabels: List<String>) {
    val timeStr = try {
        val date = Date((event.timestamp * 1000).toLong())
        SimpleDateFormat("MMM d, HH:mm:ss", Locale.getDefault()).format(date)
    } catch (_: Exception) {
        "—"
    }
    val openedOrClosed = when (event.event_type) {
        "door_open", "door_open_2" -> "Opened"
        "door_closed", "door_closed_2" -> "Closed"
        else -> event.displayType(sensorLabels)
    }
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            text = event.displayType(sensorLabels),
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 12.dp, top = 12.dp, end = 12.dp, bottom = 4.dp)
        )
        Text(
            text = "${event.device_id} · $openedOrClosed · $timeStr",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(start = 12.dp, top = 0.dp, end = 12.dp, bottom = 12.dp),
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
