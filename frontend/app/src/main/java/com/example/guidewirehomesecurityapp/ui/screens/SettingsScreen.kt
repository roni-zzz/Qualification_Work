package com.example.guidewirehomesecurityapp.ui.screens

import android.util.Log
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.example.guidewirehomesecurityapp.api.WarehouseService
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import com.example.guidewirehomesecurityapp.ui.components.WarehouseRoleChipSelector
import com.example.guidewirehomesecurityapp.ui.components.ScreenTitleWithLogo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SettingsScreen(
    modifier: Modifier = Modifier,
    onSignOut: () -> Unit = {}
) {
    val scrollState = rememberScrollState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    // Retrieve and normalize roles, filtering out "null" strings
    val globalRole = (BackendAuthService.getRole(context) ?: "user").lowercase().trim()
        .takeUnless { it == "null" } ?: "user"
    val warehouseRole = (BackendAuthService.getWarehouseRole(context) ?: "").lowercase().trim()
        .takeUnless { it == "null" } ?: ""
    
    val isAdminOrManager = globalRole == "admin" || globalRole == "manager" || 
                          warehouseRole == "admin" || warehouseRole == "manager"

    var members by remember { mutableStateOf<List<WarehouseService.WarehouseMember>>(emptyList()) }
    var pending by remember { mutableStateOf<List<WarehouseService.PendingDisarm>>(emptyList()) }
    var editingMember by remember { mutableStateOf<WarehouseService.WarehouseMember?>(null) }
    var rolePick by remember { mutableStateOf("supervisor") }
    var removeMember by remember { mutableStateOf<WarehouseService.WarehouseMember?>(null) }
    var showDeleteAccountConfirm by remember { mutableStateOf(false) }
    var deletingAccount by remember { mutableStateOf(false) }

    fun refreshOwnerData() {
        scope.launch {
            try {
                members = withContext(Dispatchers.IO) { WarehouseService.listMembers(context) }
                pending = withContext(Dispatchers.IO) { WarehouseService.listPendingDisarmRequests(context) }
            } catch (e: Exception) {
                Log.e("SettingsScreen", "Error loading management data", e)
            }
        }
    }

    LaunchedEffect(globalRole, warehouseRole) {
        Log.d("SettingsScreen", "Roles check - Global: '$globalRole', Warehouse: '$warehouseRole'")
        if (isAdminOrManager) {
            Log.d("SettingsScreen", "Access granted to Admin/Manager features")
            refreshOwnerData()
        } else {
            Log.d("SettingsScreen", "Restricted access for role: $warehouseRole")
        }
    }

    Column(
        modifier = modifier
            .padding(20.dp)
            .verticalScroll(scrollState)
    ) {
        ScreenTitleWithLogo(
            title = "Settings",
            modifier = Modifier.padding(bottom = 8.dp),
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            text = "Account and app preferences",
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
            modifier = Modifier.padding(bottom = 24.dp)
        )

        Text(
            text = "Warehouse pairing and ESP32 devices are set up by your administrator.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 16.dp)
        )

        if (isAdminOrManager) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = CardDefaults.elevatedShape
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Pending disarm approvals",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.height(8.dp))
                    if (pending.isEmpty()) {
                        Text(
                            "No pending requests.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        pending.forEach { p ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    "User #${p.requestedByUserId}",
                                    style = MaterialTheme.typography.bodyMedium,
                                    modifier = Modifier.weight(1f)
                                )
                                TextButton(onClick = {
                                    scope.launch {
                                        val ok = withContext(Dispatchers.IO) {
                                            WarehouseService.approveDisarm(context, p.id)
                                        }
                                        Toast.makeText(
                                            context,
                                            if (ok) "Disarm approved" else "Failed",
                                            Toast.LENGTH_SHORT
                                        ).show()
                                        refreshOwnerData()
                                    }
                                }) { Text("Approve") }
                                TextButton(onClick = {
                                    scope.launch {
                                        val ok = withContext(Dispatchers.IO) {
                                            WarehouseService.denyDisarm(context, p.id)
                                        }
                                        Toast.makeText(
                                            context,
                                            if (ok) "Request denied" else "Failed",
                                            Toast.LENGTH_SHORT
                                        ).show()
                                        refreshOwnerData()
                                    }
                                }) { Text("Deny") }
                            }
                        }
                    }
                    OutlinedButton(onClick = { refreshOwnerData() }, modifier = Modifier.fillMaxWidth()) {
                        Text("Refresh pending")
                    }
                }
            }

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = CardDefaults.elevatedShape
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Warehouse members",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Change roles or remove users added by your administrator.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    members.forEach { m ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)
                            ),
                            shape = RoundedCornerShape(14.dp),
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
                                        m.username,
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Medium
                                    )
                                    Text(
                                        m.email,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        maxLines = 2
                                    )
                                    Text(
                                        "Role: ${m.warehouseRole}",
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }
                                TextButton(onClick = {
                                    editingMember = m
                                    rolePick = m.warehouseRole
                                }) { Text("Edit") }
                            }
                        }
                    }
                    OutlinedButton(onClick = { refreshOwnerData() }, modifier = Modifier.fillMaxWidth()) {
                        Text("Refresh list")
                    }
                }
            }
        } else if (warehouseRole == "supervisor") {
            Text(
                "Only the admin can manage members in Settings.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 16.dp)
            )
        }

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            shape = CardDefaults.elevatedShape
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Button(
                    onClick = onSignOut,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                ) {
                    Text("Sign out", fontWeight = FontWeight.SemiBold)
                }
                Spacer(Modifier.height(12.dp))
                OutlinedButton(
                    onClick = { showDeleteAccountConfirm = true },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Delete account", color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }

    if (showDeleteAccountConfirm) {
        AlertDialog(
            onDismissRequest = {
                if (!deletingAccount) showDeleteAccountConfirm = false
            },
            title = { Text("Delete account?") },
            text = {
                Text("This permanently deletes your account. You will be signed out and need to register again to use the app.")
            },
            confirmButton = {
                TextButton(
                    enabled = !deletingAccount,
                    onClick = {
                        scope.launch {
                            deletingAccount = true
                            val (ok, errMsg) = withContext(Dispatchers.IO) {
                                WarehouseService.deleteAccount(context)
                            }
                            deletingAccount = false
                            showDeleteAccountConfirm = false
                            if (ok) {
                                Toast.makeText(context, "Account deleted", Toast.LENGTH_SHORT).show()
                                onSignOut()
                            } else {
                                Toast.makeText(
                                    context,
                                    "Failed to delete account: ${errMsg ?: "Unknown error"}",
                                    Toast.LENGTH_LONG
                                ).show()
                            }
                        }
                    }
                ) {
                    Text(
                        if (deletingAccount) "Deleting..." else "Delete",
                        color = MaterialTheme.colorScheme.error
                    )
                }
            },
            dismissButton = {
                TextButton(
                    enabled = !deletingAccount,
                    onClick = { showDeleteAccountConfirm = false }
                ) {
                    Text("Cancel")
                }
            }
        )
    }

    editingMember?.let { m ->
        Dialog(onDismissRequest = { editingMember = null }) {
            Surface(
                shape = RoundedCornerShape(28.dp),
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 2.dp,
                shadowElevation = 6.dp,
            ) {
                Column(
                    Modifier
                        .widthIn(min = 300.dp, max = 420.dp)
                        .padding(24.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    Text(
                        "Member role",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        m.username,
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                    Text(
                        m.email,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(bottom = 16.dp)
                    )
                    Text("Warehouse role", style = MaterialTheme.typography.labelLarge)
                    Spacer(Modifier.height(8.dp))
                    WarehouseRoleChipSelector(
                        selectedRole = rolePick,
                        onRoleSelected = { rolePick = it }
                    )
                    Spacer(Modifier.height(16.dp))
                    TextButton(
                        onClick = {
                            removeMember = m
                            editingMember = null
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Remove from warehouse", color = MaterialTheme.colorScheme.error)
                    }
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        TextButton(onClick = { editingMember = null }) { Text("Cancel") }
                        TextButton(onClick = {
                            scope.launch {
                                val ok = withContext(Dispatchers.IO) {
                                    WarehouseService.updateMemberWarehouseRole(context, m.id, rolePick)
                                }
                                Toast.makeText(
                                    context,
                                    if (ok) "Role updated" else "Could not update",
                                    Toast.LENGTH_SHORT
                                ).show()
                                editingMember = null
                                refreshOwnerData()
                            }
                        }) { Text("Save") }
                    }
                }
            }
        }
    }

    removeMember?.let { m ->
        AlertDialog(
            onDismissRequest = { removeMember = null },
            title = { Text("Remove ${m.username}?") },
            text = { Text("They will be unlinked from this warehouse; their account stays.") },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        val ok = withContext(Dispatchers.IO) { WarehouseService.removeMember(context, m.id) }
                        Toast.makeText(
                            context,
                            if (ok) "Removed" else "Failed",
                            Toast.LENGTH_SHORT
                        ).show()
                        removeMember = null
                        refreshOwnerData()
                    }
                }) { Text("Remove", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { removeMember = null }) { Text("Cancel") } }
        )
    }
}
