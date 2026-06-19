package com.example.guidewirehomesecurityapp.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.guidewirehomesecurityapp.R

/** Large logo centered at the top of the screen to fill the space. */
@Composable
fun TopCenterLogo(
    modifier: Modifier = Modifier,
    sizeDp: Int = 120
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Image(
            painter = painterResource(R.drawable.guidewire_logo),
            contentDescription = null,
            modifier = Modifier.size(sizeDp.dp)
        )
    }
}

@Composable
fun ScreenTitleWithLogo(
    title: String,
    modifier: Modifier = Modifier,
    style: androidx.compose.ui.text.TextStyle = MaterialTheme.typography.headlineSmall,
    logoSizeDp: Int = 72
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Image(
            painter = painterResource(R.drawable.guidewire_logo),
            contentDescription = null,
            modifier = Modifier.size(logoSizeDp.dp)
        )
        Text(
            text = title,
            style = style,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 12.dp)
        )
    }
}
