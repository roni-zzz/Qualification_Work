package com.example.guidewirehomesecurityapp.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.guidewirehomesecurityapp.api.EventService
import com.example.guidewirehomesecurityapp.ui.components.ScreenTitleWithLogo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import kotlin.math.max

/**
 * Live ESP power draw (INA219) with a simple scrolling chart. Polls `/api/power/recent`.
 */
@Composable
fun SustainabilityScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var samples by remember { mutableStateOf<List<EventService.PowerSample>>(emptyList()) }
    var nowSec by remember { mutableStateOf(System.currentTimeMillis() / 1000.0) }
    val scrollState = rememberScrollState()
    val offlineAfterSeconds = 300.0

    LaunchedEffect(Unit) {
        while (isActive) {
            samples = withContext(Dispatchers.IO) {
                EventService.getPowerRecent(context)
            }
            nowSec = System.currentTimeMillis() / 1000.0
            delay(2000)
        }
    }

    val latestRaw = samples.lastOrNull()
    val isOfflineByStaleness = latestRaw?.let { (nowSec - it.timestamp) > offlineAfterSeconds } ?: false
    val displaySamples = if (isOfflineByStaleness) emptyList() else samples
    val latest = displaySamples.lastOrNull()
    val maxMa = displaySamples.maxOfOrNull { it.valueMa }?.takeIf { it > 0 } ?: 400.0
    val palette = MaterialTheme.colorScheme

    Column(
        modifier = modifier
            .padding(20.dp)
            .verticalScroll(scrollState)
    ) {
        ScreenTitleWithLogo(
            title = "Energy",
            modifier = Modifier.padding(bottom = 8.dp),
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            text = "Live current draw from your ESP32 nodes (INA219). Updates every few seconds.",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f),
            modifier = Modifier.padding(bottom = 20.dp)
        )

        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            colors = CardDefaults.cardColors(
                containerColor = palette.primaryContainer.copy(alpha = 0.55f)
            ),
            shape = RoundedCornerShape(20.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(modifier = Modifier.padding(24.dp)) {
                Text(
                    text = "Current draw",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = palette.onPrimaryContainer
                )
                if (latest != null) {
                    Text(
                        text = "%.0f mA".format(latest.valueMa),
                        style = MaterialTheme.typography.displaySmall,
                        fontWeight = FontWeight.Bold,
                        color = palette.primary,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                    Text(
                        text = latest.deviceId,
                        style = MaterialTheme.typography.bodySmall,
                        color = palette.onPrimaryContainer.copy(alpha = 0.75f),
                        modifier = Modifier.padding(top = 4.dp)
                    )
                } else {
                    Text(
                        text = "Waiting for data…",
                        style = MaterialTheme.typography.titleLarge,
                        color = palette.onPrimaryContainer.copy(alpha = 0.8f),
                        modifier = Modifier.padding(top = 8.dp)
                    )
                    Text(
                        text = "Power events need a few seconds after the ESP connects.",
                        style = MaterialTheme.typography.bodySmall,
                        color = palette.onPrimaryContainer.copy(alpha = 0.7f),
                        modifier = Modifier.padding(top = 4.dp)
                    )
                    LinearProgressIndicator(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp)
                    )
                }
            }
        }

        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            colors = CardDefaults.cardColors(containerColor = palette.surfaceVariant.copy(alpha = 0.9f)),
            shape = RoundedCornerShape(20.dp)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(
                    text = "Recent activity (mA)",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(Modifier.height(12.dp))
                if (displaySamples.size >= 2) {
                    PowerLineChart(
                        samples = displaySamples,
                        maxMa = max(maxMa, 50.0),
                        lineColor = palette.primary,
                        fillBrush = Brush.verticalGradient(
                            colors = listOf(
                                palette.primary.copy(alpha = 0.35f),
                                Color.Transparent
                            )
                        ),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp)
                    )
                } else {
                    Text(
                        text = "Chart needs a few power samples. Open the Control tab and ensure the alarm system is receiving events.",
                        style = MaterialTheme.typography.bodySmall,
                        color = palette.onSurfaceVariant
                    )
                }
            }
        }

        Text(
            text = "Lower idle current than traditional panels — your ESP32-based nodes report real usage here.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
            modifier = Modifier.padding(top = 16.dp)
        )
    }
}

@Composable
private fun PowerLineChart(
    samples: List<EventService.PowerSample>,
    maxMa: Double,
    lineColor: Color,
    fillBrush: Brush,
    modifier: Modifier = Modifier
) {
    Canvas(modifier = modifier) {
        val w = size.width
        val h = size.height
        val pad = 8f
        if (samples.size < 2) return@Canvas
        val pts = samples.mapIndexed { i, s ->
            val x = pad + (i / (samples.size - 1f).coerceAtLeast(1f)) * (w - 2 * pad)
            val yNorm = (s.valueMa / maxMa).toFloat().coerceIn(0f, 1f)
            val y = h - pad - yNorm * (h - 2 * pad)
            Offset(x, y)
        }
        val fillPath = Path().apply {
            moveTo(pts.first().x, h)
            pts.forEach { lineTo(it.x, it.y) }
            lineTo(pts.last().x, h)
            close()
        }
        drawPath(fillPath, brush = fillBrush)
        val linePath = Path().apply {
            moveTo(pts.first().x, pts.first().y)
            for (i in 1 until pts.size) {
                lineTo(pts[i].x, pts[i].y)
            }
        }
        drawPath(
            linePath,
            color = lineColor,
            style = Stroke(width = 4f, cap = StrokeCap.Round)
        )
    }
}
