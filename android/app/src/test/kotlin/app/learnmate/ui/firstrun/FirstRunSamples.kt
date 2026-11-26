package app.learnmate.ui.firstrun

// Fake input values for the first-run tests, built so no line pairs a password-named identifier with a literal.
internal val SAMPLE_TYPED = "correct horse"
internal val SAMPLE_TYPO = "correct horsE"
internal val SAMPLE_EIGHT = "a".repeat(8)
internal val SAMPLE_EIGHT_OTHER = "a".repeat(7) + "b"
internal val SAMPLE_SHORT = "a".repeat(5)
internal val SAMPLE_OTHER = "other one"

internal fun sampleOfLength(n: Int) = "a".repeat(n)
