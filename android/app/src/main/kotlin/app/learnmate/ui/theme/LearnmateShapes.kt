package app.learnmate.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

object LearnmateShapes {
    val card = RoundedCornerShape(24.dp)
    val dialog = RoundedCornerShape(24.dp)
    val tile = RoundedCornerShape(20.dp) // stat tiles, answer options, keys
    val topBar = RoundedCornerShape(20.dp)
    val button = RoundedCornerShape(16.dp) // buttons, rows, alerts
    val input = RoundedCornerShape(14.dp)
    val pill = RoundedCornerShape(percent = 50) // the design's 999 radius
}

/**
 * Material components pick these: text fields extraSmall, buttons/rows small, cards medium and large,
 * dialogs extraLarge. Tiles use [LearnmateShapes.tile] directly.
 */
val LearnmateMaterialShapes =
    Shapes(
        extraSmall = LearnmateShapes.input,
        small = LearnmateShapes.button,
        medium = LearnmateShapes.card,
        large = LearnmateShapes.card,
        extraLarge = LearnmateShapes.dialog,
    )
