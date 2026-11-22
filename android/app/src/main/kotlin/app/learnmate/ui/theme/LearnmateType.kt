package app.learnmate.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** The design's type scale. [compact] is a phone-width screen, where H1 drops to 28. Score = displayLarge, H1 = headlineLarge, H2 = titleLarge, body = bodyLarge, small = bodyMedium/bodySmall. */
fun learnmateTypography(compact: Boolean): Typography =
    Typography().copy(
        displayLarge = TextStyle(fontSize = 96.sp, lineHeight = 96.sp, fontWeight = FontWeight.Black, letterSpacing = (-0.3).sp),
        headlineLarge =
            TextStyle(
                fontSize = if (compact) 28.sp else 32.sp,
                lineHeight = if (compact) 33.sp else 37.sp,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = (-0.8).sp,
            ),
        titleLarge = TextStyle(fontSize = 20.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.3).sp),
        titleMedium = TextStyle(fontSize = 16.sp, lineHeight = 22.sp, fontWeight = FontWeight.SemiBold, letterSpacing = (-0.3).sp),
        bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp, fontWeight = FontWeight.Normal, letterSpacing = 0.sp),
        bodyMedium = TextStyle(fontSize = 15.sp, lineHeight = 22.sp, fontWeight = FontWeight.Normal, letterSpacing = 0.sp),
        bodySmall = TextStyle(fontSize = 13.sp, lineHeight = 18.sp, fontWeight = FontWeight.Normal, letterSpacing = 0.sp),
        labelLarge = TextStyle(fontSize = 16.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 0.sp),
        labelMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp, fontWeight = FontWeight.Medium, letterSpacing = 0.sp),
        labelSmall = TextStyle(fontSize = 13.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium, letterSpacing = 0.sp),
    )
