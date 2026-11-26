package app.learnmate.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class PlanStepsTest {
    @Test
    fun `test_only has no lesson`() {
        assertEquals(listOf(PlanStep.WarmUp, PlanStep.Test), planSteps("test_only"))
    }

    @Test
    fun `learn and recap have three steps`() {
        val three = listOf(PlanStep.WarmUp, PlanStep.Lesson, PlanStep.Test)
        assertEquals(three, planSteps("learn"))
        assertEquals(three, planSteps("recap"))
    }

    @Test
    fun `states before, at and after completed`() {
        assertEquals(
            listOf(StepState.Done, StepState.Current, StepState.Upcoming),
            stepStates(planSteps("learn"), 1).map { it.second },
        )
    }

    @Test
    fun `completed is clamped`() {
        val steps = planSteps("learn")
        assertEquals(List(3) { StepState.Current }.take(1) + List(2) { StepState.Upcoming }, stepStates(steps, -4).map { it.second })
        assertEquals(List(3) { StepState.Done }, stepStates(steps, 9).map { it.second })
    }
}
