package app.learnmate.ui.components

import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.drawOutline
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.unit.dp

val FocusRingWidth = 3.dp
val FocusRingGap = 2.dp

/** Draws the focus ring outside the bounds: 3 dp outline, 2 dp away from the shape. Put it before clip/background. */
fun Modifier.focusRing(
    focused: Boolean,
    color: Color,
    shape: Shape,
): Modifier =
    drawWithContent {
        drawContent()
        if (!focused) return@drawWithContent
        val stroke = FocusRingWidth.toPx()
        val grow = FocusRingGap.toPx() + stroke / 2
        val outline = shape.createOutline(Size(size.width + grow * 2, size.height + grow * 2), layoutDirection, this)
        translate(-grow, -grow) { drawOutline(outline, color, style = Stroke(stroke)) }
    }
