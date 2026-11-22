package app.learnmate.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathOperation
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlin.math.cos
import kotlin.math.sin

@Composable
internal fun SunGlyph(
    color: Color,
    size: Dp = 18.dp,
    modifier: Modifier = Modifier,
) = Canvas(modifier.size(size)) {
    val w = this.size.width
    val c = center
    drawCircle(color, radius = 0.22f * w, center = c)
    for (i in 0 until 8) {
        val a = Math.toRadians(i * 45.0)
        val dir = Offset(cos(a).toFloat(), sin(a).toFloat())
        drawLine(color, c + dir * (0.34f * w), c + dir * (0.46f * w), strokeWidth = 0.09f * w, cap = StrokeCap.Round)
    }
}

@Composable
internal fun MoonGlyph(
    color: Color,
    size: Dp = 18.dp,
    modifier: Modifier = Modifier,
) = Canvas(modifier.size(size)) {
    val w = this.size.width
    val outer = Path().apply { addOval(Rect(center, 0.38f * w)) }
    val bite = Path().apply { addOval(Rect(center + Offset(0.22f * w, -0.18f * w), 0.32f * w)) }
    val crescent = Path.combine(PathOperation.Difference, outer, bite)
    drawPath(crescent, color)
}

@Composable
internal fun CheckGlyph(
    color: Color,
    size: Dp = 14.dp,
    modifier: Modifier = Modifier,
) = Canvas(modifier.size(size)) {
    val w = this.size.width
    val h = this.size.height
    val path =
        Path().apply {
            moveTo(0.2f * w, 0.52f * h)
            lineTo(0.42f * w, 0.72f * h)
            lineTo(0.8f * w, 0.3f * h)
        }
    drawPath(path, color, style = Stroke(0.14f * w, cap = StrokeCap.Round, join = StrokeJoin.Round))
}

@Composable
internal fun LockGlyph(
    color: Color,
    size: Dp = 14.dp,
    modifier: Modifier = Modifier,
) = Canvas(modifier.size(size)) {
    val w = this.size.width
    drawRoundRect(
        color,
        topLeft = Offset(0.18f * w, 0.45f * w),
        size = Size(0.64f * w, 0.47f * w),
        cornerRadius = CornerRadius(0.08f * w),
    )
    drawArc(
        color,
        startAngle = 180f,
        sweepAngle = 180f,
        useCenter = false,
        topLeft = Offset(0.3f * w, 0.12f * w),
        size = Size(0.4f * w, 0.48f * w),
        style = Stroke(0.12f * w),
    )
}

@Composable
internal fun PlaneGlyph(
    color: Color,
    modifier: Modifier = Modifier,
) = Canvas(modifier.size(16.dp)) {
    val w = this.size.width
    val h = this.size.height
    val plane =
        Path().apply {
            moveTo(0.05f * w, 0.45f * h)
            lineTo(0.95f * w, 0.1f * h)
            lineTo(0.6f * w, 0.9f * h)
            close()
        }
    drawPath(plane, color)
    drawLine(Color.Black.copy(alpha = 0.35f), Offset(0.95f * w, 0.1f * h), Offset(0.42f * w, 0.58f * h), strokeWidth = 1.5.dp.toPx())
}
