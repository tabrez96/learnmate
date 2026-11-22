package app.learnmate.ui.components

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

class AnswerStateTest {
    @Test
    fun feedbackLabel_isTextForRightAndWrongOnly() {
        assertEquals("Correct!", AnswerState.Right.feedbackLabel())
        assertEquals("Your answer", AnswerState.Wrong.feedbackLabel())
        assertNull(AnswerState.Default.feedbackLabel())
        assertNull(AnswerState.Selected.feedbackLabel())
    }

    @Test
    fun materialCountLabel_pluralises() {
        assertEquals("0 materials", materialCountLabel(0))
        assertEquals("1 material", materialCountLabel(1))
        assertEquals("3 materials", materialCountLabel(3))
    }
}
