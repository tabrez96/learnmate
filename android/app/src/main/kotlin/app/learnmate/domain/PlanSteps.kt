package app.learnmate.domain

enum class StepState { Done, Current, Upcoming }

enum class PlanStep { WarmUp, Lesson, Test }

/** A test-only session skips the lesson. */
fun planSteps(sessionType: String): List<PlanStep> =
    if (sessionType == "test_only") listOf(PlanStep.WarmUp, PlanStep.Test) else listOf(PlanStep.WarmUp, PlanStep.Lesson, PlanStep.Test)

fun stepStates(
    steps: List<PlanStep>,
    completed: Int,
): List<Pair<PlanStep, StepState>> {
    val done = completed.coerceIn(0, steps.size)
    return steps.mapIndexed { i, step ->
        step to
            when {
                i < done -> StepState.Done
                i == done -> StepState.Current
                else -> StepState.Upcoming
            }
    }
}
