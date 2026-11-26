package app.learnmate.domain

enum class GradeBand { A, B, C, D, E, F }

/** Bands from the design's "Grades" table: A 90+, B 80+, C 70+, D 60+, E 50+, else F. */
fun gradeBand(pct: Int): GradeBand {
    require(pct in 0..100) { "pct must be 0..100" }
    return when {
        pct >= 90 -> GradeBand.A
        pct >= 80 -> GradeBand.B
        pct >= 70 -> GradeBand.C
        pct >= 60 -> GradeBand.D
        pct >= 50 -> GradeBand.E
        else -> GradeBand.F
    }
}

sealed interface Grade {
    data class Scored(
        val pct: Int,
        val band: GradeBand,
    ) : Grade {
        val label get() = "$pct% ${band.name}"
    }

    data object Missed : Grade {
        const val LABEL = "Missed"
    }
}

/** Missed wins and is never 0%; a known server band is used as is; null when there is no score yet. */
fun gradeOf(
    scorePct: Int?,
    band: String?,
    missed: Boolean,
): Grade? {
    if (missed) return Grade.Missed
    if (scorePct == null) return null
    return Grade.Scored(scorePct, GradeBand.entries.firstOrNull { it.name == band } ?: gradeBand(scorePct))
}
