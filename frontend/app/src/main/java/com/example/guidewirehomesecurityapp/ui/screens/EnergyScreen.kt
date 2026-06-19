package com.example.guidewirehomesecurityapp.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import com.example.guidewirehomesecurityapp.api.EventService
import com.example.guidewirehomesecurityapp.api.SensorEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt
import com.example.guidewirehomesecurityapp.ui.components.ScreenTitleWithLogo

@Composable
fun EnergyScreen(
    modifier: Modifier = Modifier,
    onBack: () -> Unit
)
{

    var events by remember { mutableStateOf<List<SensorEvent>>(emptyList()) }
    var firstEventTimestamp by remember { mutableStateOf<Double?>(null) }

    // ---- ENERGY MODEL CONSTANTS ----
    val baseSystemWatts = 5.0          // ESP32 + Raspberry Pi average idle draw
    val energyPerEventWh = 0.002       // Small additional energy per triggered event
    val co2PerKwh = 0.4                // kg CO2 per kWh (average grid estimate)
    val traditionalMonthlyKwh = 35.0   // Average DVR-based system monthly usage
    val context = LocalContext.current
    // Fetch events continuously
    LaunchedEffect(Unit) {
        while (true) {
            events = withContext(Dispatchers.IO) {
                EventService.getEvents(context)  // <-- add context here
            }

            if (events.isNotEmpty() && firstEventTimestamp == null) {
                firstEventTimestamp = events.minOf { it.timestamp }
            }

            delay(3000)
        }
    }

    // ---- CALCULATIONS ----

    val totalEvents = events.sumOf { it.count }

    val hoursRunning = firstEventTimestamp?.let {
        val currentTimeSeconds = System.currentTimeMillis() / 1000.0
        ((currentTimeSeconds - it) / 3600.0).coerceAtLeast(1.0)
    } ?: 1.0

    val baseEnergyWh = baseSystemWatts * hoursRunning
    val eventEnergyWh = totalEvents * energyPerEventWh
    val totalEnergyWh = baseEnergyWh + eventEnergyWh
    val totalEnergyKwh = totalEnergyWh / 1000.0

    val monthlyProjectedKwh = totalEnergyKwh * (720.0 / hoursRunning) // 720h ≈ 30 days

    val co2Produced = totalEnergyKwh * co2PerKwh
    val co2Saved = (traditionalMonthlyKwh - monthlyProjectedKwh).coerceAtLeast(0.0) * co2PerKwh

    val efficiencyPercent =
        ((1 - (monthlyProjectedKwh / traditionalMonthlyKwh)) * 100)
            .coerceIn(0.0, 100.0)
            .roundToInt()

    // ---- UI ----

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Button(
                onClick = onBack,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Back to Warehouse")
            }
        }

        item {
            ScreenTitleWithLogo(
                title = "Energy Usage Overview",
                style = MaterialTheme.typography.titleLarge,
                logoSizeDp = 64
            )
        }

        item {
            StatCard(
                title = "Current Energy Used",
                value = "${"%.3f".format(totalEnergyKwh)} kWh"
            )
        }

        item {
            StatCard(
                title = "Projected Monthly Usage",
                value = "${"%.2f".format(monthlyProjectedKwh)} kWh"
            )
        }

        item {
            StatCard(
                title = "Eco Efficiency Score",
                value = "$efficiencyPercent / 100"
            )
        }

        item {
            StatCard(
                title = "Estimated CO₂ Produced",
                value = "${"%.3f".format(co2Produced)} kg"
            )
        }

        item {
            StatCard(
                title = "CO₂ Saved vs Traditional System",
                value = "${"%.2f".format(co2Saved)} kg"
            )
        }

        item {
            ComparisonSection(
                ourUsage = monthlyProjectedKwh,
                traditionalUsage = traditionalMonthlyKwh
            )
        }
    }
}

@Composable
private fun StatCard(title: String, value: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(text = title, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                style = MaterialTheme.typography.titleMedium,
                fontSize = 20.sp
            )
        }
    }
}

@Composable
private fun ComparisonSection(
    ourUsage: Double,
    traditionalUsage: Double
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {

            Text(
                text = "Energy Comparison (Monthly)",
                style = MaterialTheme.typography.titleMedium
            )

            EnergyBarChart(
                ourUsage = ourUsage,
                traditionalUsage = traditionalUsage
            )
        }
    }
}
@Composable
private fun EnergyBarChart(
    ourUsage: Double,
    traditionalUsage: Double
) {

    val maxValue = maxOf(ourUsage, traditionalUsage)

    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {

        BarRow(
            label = "GuideWire",
            value = ourUsage,
            maxValue = maxValue
        )

        BarRow(
            label = "Traditional DVR",
            value = traditionalUsage,
            maxValue = maxValue
        )
    }
}
@Composable
private fun BarRow(
    label: String,
    value: Double,
    maxValue: Double
) {

    val percentage = if (maxValue == 0.0) 0f
    else (value / maxValue).toFloat()

    Column {
        Text(text = "$label: ${"%.2f".format(value)} kWh")

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(20.dp)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(percentage)
                    .height(20.dp)
                    .padding(end = 4.dp)
            ) {
                Surface(
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.fillMaxSize()
                ) {}
            }
        }
    }
}