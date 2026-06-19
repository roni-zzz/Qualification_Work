package com.example.guidewirehomesecurityapp.ui.screens

import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import com.example.guidewirehomesecurityapp.auth.GoogleSignInUtils
import com.example.guidewirehomesecurityapp.notifications.AlarmFirebaseMessagingService
import com.example.guidewirehomesecurityapp.ui.components.TopCenterLogo

@Composable
fun LoginScreen(
    modifier: Modifier = Modifier,
    onLoginSuccess: () -> Unit = {},
    onMfaRequired: (String) -> Unit = {}
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val colorScheme = MaterialTheme.colorScheme

    val launcher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) {
        GoogleSignInUtils.doGoogleSignIn(
            context = context,
            scope = scope,
            launcher = null,
            signUp = false,
            onSuccess = {
                AlarmFirebaseMessagingService.registerTokenAfterLogin(context)
                Toast.makeText(context, "Login successful", Toast.LENGTH_SHORT).show()
                onLoginSuccess()
            },
            onError = { msg -> Toast.makeText(context, msg, Toast.LENGTH_LONG).show() }
        )
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(
                brush = Brush.linearGradient(
                    colors = listOf(
                        colorScheme.primaryContainer,
                        colorScheme.secondaryContainer,
                        colorScheme.primaryContainer.copy(alpha = 0.7f)
                    ),
                    start = Offset(0f, 0f),
                    end = Offset(1000f, 1000f)
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            TopCenterLogo(sizeDp = 200)
            Spacer(Modifier.height(24.dp))
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(24.dp))
                    .background(colorScheme.surface.copy(alpha = 0.95f))
                    .padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Welcome to Guidewire SafeWarehouse",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = colorScheme.primary,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    text = "Please create an account or log in to continue.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = colorScheme.onSurface.copy(alpha = 0.9f),
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(32.dp))

                Button(
                    onClick = {
                        GoogleSignInUtils.doGoogleSignIn(
                            context = context,
                            scope = scope,
                            launcher = launcher,
                            signUp = true,
                            onSuccess = {
                                AlarmFirebaseMessagingService.registerTokenAfterLogin(context)
                                Toast.makeText(context, "Account created. You're signed in.", Toast.LENGTH_SHORT).show()
                                onLoginSuccess()
                            },
                            onError = { msg -> Toast.makeText(context, msg, Toast.LENGTH_LONG).show() }
                        )
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = colorScheme.primary,
                        contentColor = colorScheme.onPrimary
                    ),
                    elevation = ButtonDefaults.buttonElevation(
                        defaultElevation = 6.dp,
                        pressedElevation = 8.dp
                    )
                ) {
                    Text(
                        text = "Create account",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                }
                Spacer(Modifier.height(16.dp))
                Button(
                    onClick = {
                        GoogleSignInUtils.doGoogleSignIn(
                            context = context,
                            scope = scope,
                            launcher = launcher,
                            signUp = false,
                            onSuccess = { idToken ->
                                BackendAuthService.signIn(
                                    context = context,
                                    idToken = idToken,
                                    onSuccess = {
                                        AlarmFirebaseMessagingService.registerTokenAfterLogin(context)
                                        Toast.makeText(context, "Login successful", Toast.LENGTH_SHORT).show()
                                        onLoginSuccess()
                                    },
                                    onMfaRequired = { email -> onMfaRequired(email) },
                                    onError = { msg -> Toast.makeText(context, msg, Toast.LENGTH_LONG).show() }
                                )
                            },
                            onError = { msg -> Toast.makeText(context, msg, Toast.LENGTH_LONG).show() }
                        )
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = colorScheme.secondary,
                        contentColor = colorScheme.onSecondary
                    ),
                    elevation = ButtonDefaults.buttonElevation(
                        defaultElevation = 6.dp,
                        pressedElevation = 8.dp
                    )
                ) {
                    Text(
                        text = "Log in with Google",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                }
                Spacer(Modifier.height(20.dp))
                Text(
                    text = "Or sign in with email (account created by admin)",
                    style = MaterialTheme.typography.bodySmall,
                    color = colorScheme.onSurface.copy(alpha = 0.8f)
                )
                Spacer(Modifier.height(8.dp))
                var email by remember { mutableStateOf("") }
                var password by remember { mutableStateOf("") }
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Email") }
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Password") }
                )
                Spacer(Modifier.height(12.dp))
                Button(
                    onClick = {
                        if (email.isBlank() || password.isBlank()) {
                            Toast.makeText(context, "Enter email and password", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        BackendAuthService.signInWithEmail(
                            context = context,
                            email = email,
                            password = password,
                            onSuccess = {
                                AlarmFirebaseMessagingService.registerTokenAfterLogin(context)
                                Toast.makeText(context, "Login successful", Toast.LENGTH_SHORT).show()
                                onLoginSuccess()
                            },
                            onError = { msg -> Toast.makeText(context, msg, Toast.LENGTH_LONG).show() }
                        )
                    },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = colorScheme.tertiary, contentColor = colorScheme.onTertiary)
                ) {
                    Text("Log in with email")
                }
            }
        }
    }
}
