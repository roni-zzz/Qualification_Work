package com.example.guidewirehomesecurityapp.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

private val ROLES = listOf("admin", "supervisor", "contractor", "worker")

private fun roleLabel(role: String): String =
    when (role.lowercase()) {
        "admin" -> "Admin"
        "supervisor" -> "Supervisor"
        "contractor" -> "Contractor"
        "worker" -> "Worker"
        else -> role.replaceFirstChar { it.uppercase() }
    }

/**
 * Two rows of role chips (2+2) so labels are not squished on narrow dialogs.
 */
@Composable
fun WarehouseRoleChipSelector(
    selectedRole: String,
    onRoleSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            ROLES.take(2).forEach { r ->
                FilterChip(
                    selected = selectedRole.equals(r, ignoreCase = true),
                    onClick = { onRoleSelected(r) },
                    label = { Text(roleLabel(r)) },
                    modifier = Modifier.weight(1f),
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    ),
                )
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            ROLES.drop(2).forEach { r ->
                FilterChip(
                    selected = selectedRole.equals(r, ignoreCase = true),
                    onClick = { onRoleSelected(r) },
                    label = { Text(roleLabel(r)) },
                    modifier = Modifier.weight(1f),
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    ),
                )
            }
        }
    }
}
