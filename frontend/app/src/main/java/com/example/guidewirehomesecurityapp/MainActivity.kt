package com.example.guidewirehomesecurityapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.*
import com.example.guidewirehomesecurityapp.auth.BackendAuthService
import com.example.guidewirehomesecurityapp.ui.screens.*
import com.example.guidewirehomesecurityapp.ui.theme.LogInTheme

class MainActivity : ComponentActivity() {

    sealed class AppScreen {
        object Splash : AppScreen()
        object Login : AppScreen()
        object Otp : AppScreen()
        object Main : AppScreen()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            LogInTheme {
                var currentScreen by remember { mutableStateOf<AppScreen>(AppScreen.Splash) }
                var otpEmail by remember { mutableStateOf("") }

                when (currentScreen) {
                    AppScreen.Splash -> {
                        SplashScreen { currentScreen = AppScreen.Login }
                    }
                    AppScreen.Login -> {
                        LoginScreen(
                            onLoginSuccess = {
                                currentScreen = AppScreen.Main
                            },
                            onMfaRequired = { email ->
                                otpEmail = email
                                currentScreen = AppScreen.Otp
                            }
                        )
                    }
                    AppScreen.Otp -> {
                        OtpScreen(
                            email = otpEmail,
                            onVerified = {
                                currentScreen = AppScreen.Main
                            }
                        )
                    }
                    AppScreen.Main -> {
                        HomeScreen(onSignOut = {
                            BackendAuthService.clearToken(this)
                            currentScreen = AppScreen.Login
                        })
                    }
                }
            }
        }
    }
}