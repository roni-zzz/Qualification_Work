package com.example.guidewirehomesecurityapp.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// Guidewire SafeWarehouse – green computing & sustainability palette
private val ForestGreen = Color(0xFF2D5A3D)
private val ForestGreenDark = Color(0xFF1E3D2A)
private val ForestGreenDarker = Color(0xFF0F2618)
private val SageGreen = Color(0xFF8FBC8F)
private val SageGreenDark = Color(0xFF6B9B6B)
private val SageGreenDim = Color(0xFF4A7A4A)
private val LeafLight = Color(0xFFC8E6C9)
private val LeafDim = Color(0xFF3D5C3E)
private val EarthBrown = Color(0xFF8D6E63)
private val EarthBrownLight = Color(0xFFBCAAA4)
private val CreamBackground = Color(0xFFF1F8E9)
private val WarmWhite = Color(0xFFFAFAF8)

private val LightColorScheme = lightColorScheme(
    primary = ForestGreen,
    onPrimary = WarmWhite,
    primaryContainer = LeafLight,
    onPrimaryContainer = ForestGreenDark,
    secondary = SageGreenDark,
    onSecondary = WarmWhite,
    secondaryContainer = SageGreen,
    onSecondaryContainer = ForestGreenDark,
    tertiary = EarthBrownLight,
    onTertiary = ForestGreenDark,
    background = CreamBackground,
    onBackground = Color(0xFF1B1C1A),
    surface = WarmWhite,
    onSurface = Color(0xFF1B1C1A),
    surfaceVariant = LeafLight.copy(alpha = 0.6f),
    onSurfaceVariant = Color(0xFF3D4A3E)
)

// App dark theme (follows system)
private val DarkColorScheme = darkColorScheme(
    primary = SageGreen,
    onPrimary = ForestGreenDark,
    primaryContainer = ForestGreen,
    onPrimaryContainer = LeafLight,
    secondary = SageGreen,
    onSecondary = ForestGreenDark,
    secondaryContainer = ForestGreenDark,
    onSecondaryContainer = SageGreen,
    tertiary = EarthBrownLight,
    onTertiary = ForestGreenDark,
    background = Color(0xFF1B1C1A),
    onBackground = Color(0xFFE3E6E1),
    surface = Color(0xFF1E2B21),
    onSurface = Color(0xFFE3E6E1),
    surfaceVariant = ForestGreen.copy(alpha = 0.4f),
    onSurfaceVariant = Color(0xFFC2CFC4)
)

// Admin dashboard only – darker green shades
private val AdminDarkColorScheme = darkColorScheme(
    primary = SageGreenDim,
    onPrimary = Color(0xFFE3E6E1),
    primaryContainer = ForestGreenDark,
    onPrimaryContainer = LeafLight,
    secondary = SageGreenDark,
    onSecondary = ForestGreenDarker,
    secondaryContainer = ForestGreenDarker,
    onSecondaryContainer = SageGreen,
    tertiary = EarthBrownLight,
    onTertiary = ForestGreenDark,
    background = Color(0xFF0D120F),
    onBackground = Color(0xFFE3E6E1),
    surface = Color(0xFF141C17),
    onSurface = Color(0xFFE3E6E1),
    surfaceVariant = LeafDim,
    onSurfaceVariant = Color(0xFFC2CFC4)
)

@Composable
fun LogInTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    val view = LocalView.current

    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.primary.toArgb()
            WindowCompat
                .getInsetsController(window, view)
                .isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}

/** Darker green theme for the Admin dashboard only. Wrap AdminDashboardScreen in this. */
@Composable
fun AdminTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AdminDarkColorScheme,
        content = content
    )
}
