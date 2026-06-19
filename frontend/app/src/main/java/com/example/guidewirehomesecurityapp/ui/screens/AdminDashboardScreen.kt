package com.example.guidewirehomesecurityapp.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.SensorDoor
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.example.guidewirehomesecurityapp.api.AdminWarehouse
import com.example.guidewirehomesecurityapp.api.AdminService
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import com.example.guidewirehomesecurityapp.notifications.AlarmFirebaseMessagingService
import com.example.guidewirehomesecurityapp.ui.components.WarehouseRoleChipSelector
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminDashboardScreen(
    modifier: Modifier = Modifier,
    onSignOut: () -> Unit = {}
) {
    val context = LocalContext.current
    var warehouses by remember { mutableStateOf<List<AdminWarehouse>>(emptyList()) }
    var offlineCount by remember { mutableStateOf(0) }
    var loading by remember { mutableStateOf(true) }
    var warehouseAdded by remember { mutableStateOf(false) }
    var showAddWarehouseDialog by remember { mutableStateOf(false) }
    var addWarehouseMcIdText by remember { mutableStateOf("") }
    var expandedWarehouseId by remember { mutableStateOf<Int?>(null) }
    var sensorDialogWarehouse by remember { mutableStateOf<AdminWarehouse?>(null) }
    var userDialogWarehouse by remember { mutableStateOf<AdminWarehouse?>(null) }
    var notifyDialogWarehouse by remember { mutableStateOf<AdminWarehouse?>(null) }
    var nameEditWarehouse by remember { mutableStateOf<AdminWarehouse?>(null) }
    var deleteConfirmWarehouse by remember { mutableStateOf<AdminWarehouse?>(null) }
    val scope = rememberCoroutineScope()

    fun loadData() {
        loading = true
        scope.launch {
            val (w, o) = withContext(Dispatchers.IO) {
                AdminService.listWarehouses(context) to AdminService.listOffline(context).size
            }
            warehouses = w
            offlineCount = o
            loading = false
        }
    }

    LaunchedEffect(Unit) {
        loadData()
        AlarmFirebaseMessagingService.registerTokenAfterLogin(context)
    }

    if (showAddWarehouseDialog) {
        AlertDialog(
            onDismissRequest = {
                showAddWarehouseDialog = false
                addWarehouseMcIdText = ""
            },
            title = { Text("Add Warehouse") },
            text = {
                Column {
                    Text(
                        "Optional: enter the ESP board number so it matches firmware DEVICE_ID " +
                            "(e.g. 2 → esp32_2). Leave empty to use the next free id.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = addWarehouseMcIdText,
                        onValueChange = { addWarehouseMcIdText = it.filter { c -> c.isDigit() } },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("Microcontroller id (optional)") },
                        placeholder = { Text("e.g. 2") }
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        val id = addWarehouseMcIdText.trim().toIntOrNull()
                        val success = withContext(Dispatchers.IO) {
                            AdminService.addWarehouse(context, microcontrollerId = id)
                        }
                        if (success) {
                            showAddWarehouseDialog = false
                            addWarehouseMcIdText = ""
                            warehouseAdded = true
                            loadData()
                            Toast.makeText(context, "Warehouse added successfully", Toast.LENGTH_SHORT).show()
                        } else {
                            Toast.makeText(
                                context,
                                "Failed to add warehouse — try another id or leave blank",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    }
                }) { Text("Add") }
            },
            dismissButton = {
                TextButton(onClick = {
                    showAddWarehouseDialog = false
                    addWarehouseMcIdText = ""
                }) { Text("Cancel") }
            }
        )
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Admin", fontWeight = FontWeight.Bold)
                        BackendAuthService.getUsername(context)?.let { un ->
                            Text(
                                " · $un",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
                            )
                        }
                    }
                },
                actions = {
                    TextButton(onClick = onSignOut) {
                        Text("Sign out")
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddWarehouseDialog = true },
                shape = RoundedCornerShape(16.dp),
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add warehouse")
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(
                    brush = Brush.linearGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f),
                            MaterialTheme.colorScheme.surface.copy(alpha = 0.9f)
                        ),
                        start = Offset(0f, 0f),
                        end = Offset(500f, 800f)
                    )
                )
        ) {
            if (loading && warehouses.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    if (offlineCount > 0) {
                        item {
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text(
                                    modifier = Modifier.padding(12.dp),
                                    text = "$offlineCount device(s) offline — consider notifying admin",
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }
                        }
                    }
                    items(warehouses) { warehouse ->
                        AdminWarehouseCard(
                            warehouse = warehouse,
                            expanded = expandedWarehouseId == warehouse.alarmSystemId,
                            onExpand = { expandedWarehouseId = if (expandedWarehouseId == warehouse.alarmSystemId) null else warehouse.alarmSystemId },
                            onEditSensors = { sensorDialogWarehouse = warehouse },
                            onManageUsers = { userDialogWarehouse = warehouse },
                            onNotify = { notifyDialogWarehouse = warehouse },
                            onEditName = { nameEditWarehouse = warehouse },
                            onDelete = { deleteConfirmWarehouse = warehouse }
                        )
                    }
                }
            }
        }
    }

    // Success message is shown as Toast in addWarehouse()
    // Old alert dialog removed since addWarehouse returns Boolean

    if (warehouseAdded) {
        AlertDialog(
            onDismissRequest = { warehouseAdded = false },
            title = { Text("Warehouse Added Successfully") },
            text = {
                Column {
                    Text(
                        "Use the microcontroller ID on the ESP32 firmware (DEVICE_ID) so events go to this warehouse.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(Modifier.height(12.dp))
                    Text(
                        "Next steps:",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        "1. Open this warehouse → Users\n" +
                        "2. Link an existing account (email) or create a new account\n" +
                        "3. The list shows 'Last seen' when the ESP is online and sending events",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            },
            confirmButton = { TextButton(onClick = { warehouseAdded = false }) { Text("OK") } }
        )
    }

    sensorDialogWarehouse?.let { warehouse ->
        SensorLabelsDialog(
            warehouse = warehouse,
            onDismiss = { sensorDialogWarehouse = null },
            onSave = { labels ->
                scope.launch {
                    val ok = withContext(Dispatchers.IO) {
                        AdminService.setSensorLabels(context, warehouse.alarmSystemId, labels)
                    }
                    if (ok) {
                        loadData()
                        sensorDialogWarehouse = null
                        Toast.makeText(context, "Sensor names saved", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        )
    }

    userDialogWarehouse?.let { warehouse ->
        UsersDialog(
            warehouse = warehouse,
            onDismiss = { userDialogWarehouse = null },
            onUserAdded = { loadData() }
        )
    }

    notifyDialogWarehouse?.let { warehouse ->
        NotifyDialog(
            warehouse = warehouse,
            onDismiss = { notifyDialogWarehouse = null },
            onSend = { title, body ->
                scope.launch {
                    val n = withContext(Dispatchers.IO) {
                        AdminService.notifyAdmin(context, warehouse.alarmSystemId, title, body)
                    }
                    notifyDialogWarehouse = null
                    Toast.makeText(context, "Sent to $n device(s)", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    nameEditWarehouse?.let { warehouse ->
        var editName by remember(warehouse.alarmSystemId) { mutableStateOf(warehouse.name.ifBlank { warehouse.deviceId }) }
        AlertDialog(
            onDismissRequest = { nameEditWarehouse = null },
            title = { Text("Edit name") },
            text = {
                OutlinedTextField(
                    value = editName,
                    onValueChange = { editName = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Display name") }
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        val ok = withContext(Dispatchers.IO) {
                            AdminService.updateWarehouseName(context, warehouse.alarmSystemId, editName)
                        }
                        if (ok) { loadData(); nameEditWarehouse = null; Toast.makeText(context, "Saved", Toast.LENGTH_SHORT).show() }
                    }
                }) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { nameEditWarehouse = null }) { Text("Cancel") } }
        )
    }

    deleteConfirmWarehouse?.let { warehouse ->
        AlertDialog(
            onDismissRequest = { deleteConfirmWarehouse = null },
            title = { Text("Delete alarm system?") },
            text = {
                Text("${warehouse.name.ifBlank { warehouse.deviceId }} will be removed. Users will be unlinked (not deleted).")
            },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        val (ok, errMsg) = withContext(Dispatchers.IO) {
                            AdminService.deleteWarehouse(context, warehouse.alarmSystemId)
                        }
                        deleteConfirmWarehouse = null
                        if (ok) {
                            loadData()
                            Toast.makeText(context, "Deleted", Toast.LENGTH_SHORT).show()
                        } else {
                            Toast.makeText(context, "Delete failed: ${errMsg ?: "Unknown"}", Toast.LENGTH_LONG).show()
                        }
                    }
                }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { deleteConfirmWarehouse = null }) { Text("Cancel") } }
        )
    }
}

/** One-line hint: whether the ESP32 for this home has been seen and matches firmware DEVICE_ID. */
private fun espConnectionHint(warehouse: AdminWarehouse): String {
    val id = warehouse.deviceId.ifBlank {
        if (warehouse.microcontrollerId > 0) "esp32_${warehouse.microcontrollerId}" else "—"
    }
    val last = warehouse.lastSeen
    if (last == null || last <= 0.0) {
        return "ESP: set DEVICE_ID to $id in firmware — not seen yet."
    }
    val nowSec = System.currentTimeMillis() / 1000.0
    val sec = (nowSec - last).toLong().coerceAtLeast(0)
    val ago = when {
        sec < 90 -> "${sec}s ago"
        sec < 3600 -> "${sec / 60}m ago"
        sec < 86400 -> "${sec / 3600}h ago"
        else -> "${sec / 86400}d ago"
    }
    return if (warehouse.offline) {
        "ESP $id · Offline (last activity $ago)"
    } else {
        "ESP $id · Online (last seen $ago)"
    }
}

@Composable
private fun AdminWarehouseCard(
    warehouse: AdminWarehouse,
    expanded: Boolean,
    onExpand: () -> Unit,
    onEditSensors: () -> Unit,
    onManageUsers: () -> Unit,
    onNotify: () -> Unit,
    onEditName: () -> Unit,
    onDelete: () -> Unit
) {
    val displayName = warehouse.name.ifBlank { warehouse.deviceId.ifBlank { "System #${warehouse.alarmSystemId}" } }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        onClick = onExpand
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = displayName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "${warehouse.deviceId} · Users: ${warehouse.userCount} · Sensors: ${warehouse.sensorLabels.size}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = espConnectionHint(warehouse),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.9f)
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (warehouse.offline) {
                        OutlinedButton(
                            onClick = onNotify,
                            modifier = Modifier.padding(end = 8.dp)
                        ) {
                            Icon(Icons.Default.Notifications, contentDescription = null, Modifier.padding(end = 4.dp))
                            Text("Notify", maxLines = 1, softWrap = false)
                        }
                        Text(
                            text = "OFFLINE",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                }
            }
            if (expanded) {
                Spacer(Modifier.height(12.dp))
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            onClick = onEditName,
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Edit, null, Modifier.padding(end = 4.dp))
                            Text("Name", style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        OutlinedButton(
                            onClick = onEditSensors,
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.SensorDoor, null, Modifier.padding(end = 4.dp))
                            Text("Sensors", style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        OutlinedButton(
                            onClick = onManageUsers,
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Person, null, Modifier.padding(end = 4.dp))
                            Text("Users", style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            onClick = onNotify,
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Notifications, null, Modifier.padding(end = 4.dp))
                            Text("Notify", style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                        OutlinedButton(
                            onClick = onDelete,
                            modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
                        ) {
                            Icon(Icons.Default.Delete, null, Modifier.padding(end = 4.dp))
                            Text("Delete", style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SensorLabelsDialog(
    warehouse: AdminWarehouse,
    onDismiss: () -> Unit,
    onSave: (List<String>) -> Unit
) {
    var name1 by remember(warehouse.alarmSystemId) {
        mutableStateOf(warehouse.sensorLabels.getOrNull(0) ?: "")
    }
    var name2 by remember(warehouse.alarmSystemId) {
        mutableStateOf(warehouse.sensorLabels.getOrNull(1) ?: "")
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Sensor names — ${warehouse.name.ifBlank { warehouse.deviceId }}") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                Text(
                    "These names appear for the admin on the Control tab. Sensor 1 = first reed (GPIO 4), sensor 2 = second reed (GPIO 14).",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = name1,
                    onValueChange = { name1 = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Sensor 1") },
                    placeholder = { Text("e.g. Front door") }
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = name2,
                    onValueChange = { name2 = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Sensor 2") },
                    placeholder = { Text("e.g. Window, back door") }
                )
            }
        },
        confirmButton = {
            TextButton(onClick = {
                onSave(listOf(name1.trim(), name2.trim()))
            }) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun UsersDialog(
    warehouse: AdminWarehouse,
    onDismiss: () -> Unit,
    onUserAdded: () -> Unit
) {
    var users by remember(warehouse.alarmSystemId) { mutableStateOf<List<AdminService.WarehouseUser>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var showAddForm by remember { mutableStateOf(false) }
    var showLinkForm by remember { mutableStateOf(false) }
    var editUser by remember { mutableStateOf<AdminService.WarehouseUser?>(null) }
    var removeConfirmUser by remember { mutableStateOf<AdminService.WarehouseUser?>(null) }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    LaunchedEffect(warehouse.alarmSystemId) {
        users = withContext(Dispatchers.IO) { AdminService.listUsers(context, warehouse.alarmSystemId) }
        loading = false
    }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(28.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 2.dp,
            shadowElevation = 6.dp,
        ) {
            Column(
                Modifier
                    .widthIn(min = 320.dp, max = 520.dp)
                    .padding(24.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Text(
                    "Users",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    warehouse.name.ifBlank { warehouse.deviceId },
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(16.dp))
                if (loading) {
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .padding(32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator()
                    }
                } else {
                    Text(
                        "Link someone who already has an account (e.g. signed in with Google). Create new is for a fresh email/password user.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(bottom = 12.dp)
                    )
                    users.forEach { u ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 6.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                            ),
                            shape = RoundedCornerShape(16.dp),
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 14.dp, vertical = 12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        u.username,
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Medium
                                    )
                                    Text(
                                        u.email,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                    Text(
                                        "Role: ${u.warehouseRole}",
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }
                                Row {
                                    IconButton(onClick = { editUser = u }) {
                                        Icon(Icons.Default.Edit, contentDescription = "Edit")
                                    }
                                    IconButton(onClick = { removeConfirmUser = u }) {
                                        Icon(Icons.Default.Delete, contentDescription = "Remove")
                                    }
                                }
                            }
                        }
                    }
                    HorizontalDivider(Modifier.padding(vertical = 12.dp))
                    when {
                        showLinkForm -> LinkExistingUserForm(
                            onLink = { email, password, warehouseRole ->
                                scope.launch {
                                    val ok = withContext(Dispatchers.IO) {
                                        AdminService.linkExistingUser(context, warehouse.alarmSystemId, email, password, warehouseRole)
                                    }
                                    if (ok) {
                                        onUserAdded()
                                        showLinkForm = false
                                        users = withContext(Dispatchers.IO) {
                                            AdminService.listUsers(context, warehouse.alarmSystemId)
                                        }
                                        Toast.makeText(context, "Linked to this warehouse", Toast.LENGTH_SHORT).show()
                                    } else {
                                        Toast.makeText(
                                            context,
                                            "Failed — email must exist (user signed up once), not already on another warehouse; password 8+ chars if set",
                                            Toast.LENGTH_LONG
                                        ).show()
                                    }
                                }
                            },
                            onCancel = { showLinkForm = false }
                        )
                        showAddForm -> AddUserForm(
                            onAdd = { username, email, password, phone, warehouseRole ->
                                scope.launch {
                                    val ok = withContext(Dispatchers.IO) {
                                        AdminService.addUser(context, warehouse.alarmSystemId, username, email, password, phone, warehouseRole)
                                    }
                                    if (ok) {
                                        onUserAdded()
                                        showAddForm = false
                                        users = withContext(Dispatchers.IO) { AdminService.listUsers(context, warehouse.alarmSystemId) }
                                        Toast.makeText(context, "User created", Toast.LENGTH_SHORT).show()
                                    } else {
                                        Toast.makeText(context, "Failed (e.g. email already exists)", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            },
                            onCancel = { showAddForm = false }
                        )
                        else -> {
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                TextButton(
                                    modifier = Modifier.weight(1f),
                                    onClick = {
                                        showLinkForm = true
                                        showAddForm = false
                                    }
                                ) { Text("Link existing") }
                                TextButton(
                                    modifier = Modifier.weight(1f),
                                    onClick = {
                                        showAddForm = true
                                        showLinkForm = false
                                    }
                                ) { Text("Create new") }
                            }
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onDismiss) { Text("Close") }
                }
            }
        }
    }

    editUser?.let { u ->
        var username by remember(u.id) { mutableStateOf(u.username) }
        var email by remember(u.id) { mutableStateOf(u.email) }
        var phone by remember(u.id) { mutableStateOf(u.phone) }
        var password by remember(u.id) { mutableStateOf("") }
        var warehouseRoleEdit by remember(u.id) { mutableStateOf(u.warehouseRole) }
        Dialog(onDismissRequest = { editUser = null }) {
            Surface(
                shape = RoundedCornerShape(28.dp),
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 2.dp,
                shadowElevation = 6.dp,
            ) {
                Column(
                    Modifier
                        .widthIn(min = 300.dp, max = 440.dp)
                        .padding(24.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    Text(
                        "Edit user",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        u.email,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 4.dp, bottom = 16.dp)
                    )
                    OutlinedTextField(
                        value = username,
                        onValueChange = { username = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("Username") }
                    )
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = email,
                        onValueChange = { email = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("Email") }
                    )
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = phone,
                        onValueChange = { phone = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("Phone") }
                    )
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("New password (optional)") }
                    )
                    Spacer(Modifier.height(16.dp))
                    Text("Warehouse role", style = MaterialTheme.typography.labelLarge)
                    Spacer(Modifier.height(8.dp))
                    WarehouseRoleChipSelector(
                        selectedRole = warehouseRoleEdit,
                        onRoleSelected = { warehouseRoleEdit = it }
                    )
                    Spacer(Modifier.height(20.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        TextButton(onClick = { editUser = null }) { Text("Cancel") }
                        TextButton(onClick = {
                            scope.launch {
                                val ok = withContext(Dispatchers.IO) {
                                    AdminService.updateUser(
                                        context,
                                        warehouse.alarmSystemId,
                                        u.id,
                                        username,
                                        email,
                                        phone,
                                        password.takeIf { it.isNotBlank() },
                                        warehouseRoleEdit
                                    )
                                }
                                editUser = null
                                if (ok) {
                                    users = withContext(Dispatchers.IO) { AdminService.listUsers(context, warehouse.alarmSystemId) }
                                    onUserAdded()
                                    Toast.makeText(context, "Saved", Toast.LENGTH_SHORT).show()
                                }
                            }
                        }) { Text("Save") }
                    }
                }
            }
        }
    }

    removeConfirmUser?.let { u ->
        AlertDialog(
            onDismissRequest = { removeConfirmUser = null },
            title = { Text("Remove user from warehouse?") },
            text = { Text("${u.username} will be unlinked from this warehouse (account kept).") },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        val ok = withContext(Dispatchers.IO) { AdminService.removeUser(context, warehouse.alarmSystemId, u.id) }
                        removeConfirmUser = null
                        if (ok) {
                            users = withContext(Dispatchers.IO) { AdminService.listUsers(context, warehouse.alarmSystemId) }
                            onUserAdded()
                            Toast.makeText(context, "Removed", Toast.LENGTH_SHORT).show()
                        }
                    }
                }) { Text("Remove", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { removeConfirmUser = null }) { Text("Cancel") } }
        )
    }
}

@Composable
private fun LinkExistingUserForm(
    onLink: (email: String, password: String?, warehouseRole: String) -> Unit,
    onCancel: () -> Unit
) {
    val context = LocalContext.current
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var warehouseRole by remember { mutableStateOf("supervisor") }
    Column {
        Text(
            "They must already exist in the app (e.g. “Create account” with Google). Optional password enables email login too. First user in an empty home becomes admin automatically.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 8.dp)
        )
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Email") }
        )
        Spacer(Modifier.height(4.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Password (optional, 8+ chars)") }
        )
        Spacer(Modifier.height(8.dp))
        Text("Warehouse role", style = MaterialTheme.typography.labelLarge)
        Spacer(Modifier.height(8.dp))
        WarehouseRoleChipSelector(selectedRole = warehouseRole, onRoleSelected = { warehouseRole = it })
        Row(Modifier.padding(top = 12.dp)) {
            TextButton(onClick = {
                if (email.isBlank()) return@TextButton
                val p = password.takeIf { it.isNotBlank() }
                if (p != null && p.length < 8) {
                    Toast.makeText(context, "Password must be at least 8 characters", Toast.LENGTH_SHORT).show()
                    return@TextButton
                }
                onLink(email.trim(), p, warehouseRole)
            }) { Text("Link to this warehouse") }
            TextButton(onClick = onCancel) { Text("Cancel") }
        }
    }
}

@Composable
private fun AddUserForm(
    onAdd: (username: String, email: String, password: String, phone: String?, warehouseRole: String) -> Unit,
    onCancel: () -> Unit
) {
    var username by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var warehouseRole by remember { mutableStateOf("supervisor") }
    Column {
        Text(
            "First user added to an empty warehouse is always the warehouse manager (admin).",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 8.dp)
        )
        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Username") }
        )
        Spacer(Modifier.height(4.dp))
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Email") }
        )
        Spacer(Modifier.height(4.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Password") }
        )
        Spacer(Modifier.height(4.dp))
        OutlinedTextField(
            value = phone,
            onValueChange = { phone = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Phone (optional)") }
        )
        Spacer(Modifier.height(8.dp))
        Text("Warehouse role", style = MaterialTheme.typography.labelLarge)
        Spacer(Modifier.height(8.dp))
        WarehouseRoleChipSelector(selectedRole = warehouseRole, onRoleSelected = { warehouseRole = it })
        Row(Modifier.padding(top = 12.dp)) {
            TextButton(onClick = { onAdd(username, email, password, phone.takeIf { it.isNotBlank() }, warehouseRole) }) { Text("Create") }
            TextButton(onClick = onCancel) { Text("Cancel") }
        }
    }
}

@Composable
private fun NotifyDialog(
    warehouse: AdminWarehouse,
    onDismiss: () -> Unit,
    onSend: (title: String, body: String) -> Unit
) {
    val defaultTitle = if (warehouse.offline) "Sensor offline" else "Update"
    val defaultBody = if (warehouse.offline) "One or more sensors have been offline. Please check your system." else ""
    var title by remember(warehouse.alarmSystemId) { mutableStateOf(defaultTitle) }
    var body by remember(warehouse.alarmSystemId) { mutableStateOf(defaultBody) }
    val dialogBg = Color(0xFF1F2937)
    val whiteText = Color.White
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = dialogBg,
        title = { Text("Notify admin — ${warehouse.name.ifBlank { warehouse.deviceId }}", color = whiteText) },
        text = {
            Column {
                Text("Title", color = whiteText)
                BasicTextField(
                    value = title,
                    onValueChange = { title = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    textStyle = MaterialTheme.typography.bodyMedium.copy(color = whiteText)
                )
                Spacer(Modifier.height(8.dp))
                Text("Message", color = whiteText)
                BasicTextField(
                    value = body,
                    onValueChange = { body = it },
                    modifier = Modifier.fillMaxWidth(),
                    textStyle = MaterialTheme.typography.bodyMedium.copy(color = whiteText)
                )
            }
        },
        confirmButton = { TextButton(onClick = { onSend(title, body) }) { Text("Send") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}
