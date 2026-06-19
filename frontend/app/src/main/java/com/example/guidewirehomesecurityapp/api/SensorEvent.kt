package com.example.guidewirehomesecurityapp.api

/**
 * Processed sensor event from the backend (ESP32 → backend → app).
 * Backend validates: device_id (esp32_xxxx), event_type, count, timestamp.
 */
data class SensorEvent(
    val device_id: String,
    val event_type: String,
    val count: Int,
    val timestamp: Double,
    /** mA for [current_power_usage] events when backend stores it */
    val value: Double? = null,
) {
    /**
     * Human-readable label for [event_type].
     * When [sensorLabels] is provided (from admin), door events use those names; otherwise legacy defaults.
     */
    fun displayType(sensorLabels: List<String> = emptyList()): String {
        val n1 = sensorLabels.getOrNull(0)?.takeIf { it.isNotBlank() }
        val n2 = sensorLabels.getOrNull(1)?.takeIf { it.isNotBlank() }
        return when (event_type) {
            "door_open" -> if (n1 != null) "$n1 opened" else "Door opened"
            "door_closed" -> if (n1 != null) "$n1 closed" else "Door closed"
            "door_open_2" -> if (n2 != null) "$n2 opened" else "Sensor 2 opened"
            "door_closed_2" -> if (n2 != null) "$n2 closed" else "Sensor 2 closed"
            "alarm_enabled" -> "Alarm armed"
            "alarm_disabled" -> "Alarm disarmed"
            "led_toggle" -> "Sensor toggled"
            else -> event_type
        }
    }
}

/** Latest open/closed state for reed 1 and reed 2 from events (newest timestamp wins). */
fun deriveDoorOpenStates(events: List<SensorEvent>): Pair<Boolean?, Boolean?> {
    var s1: Boolean? = null
    var s2: Boolean? = null
    for (e in events.sortedByDescending { it.timestamp }) {
        when (e.event_type) {
            "door_open" -> if (s1 == null) s1 = true
            "door_closed" -> if (s1 == null) s1 = false
            "door_open_2" -> if (s2 == null) s2 = true
            "door_closed_2" -> if (s2 == null) s2 = false
        }
        if (s1 != null && s2 != null) break
    }
    return Pair(s1, s2)
}
