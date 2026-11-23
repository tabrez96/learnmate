package app.learnmate.ui.navigation

import app.learnmate.data.db.CurrentSessionEntity
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class StartGraphTest {
    private fun session(state: String) =
        CurrentSessionEntity(
            id = 1,
            subjectId = null,
            type = "revision",
            questionCount = 5,
            state = state,
            pinHash = null,
            pinVersion = 1,
            startedAt = null,
            updatedAtMs = 0,
        )

    @Test
    fun noSessionOpensParent() = assertEquals(StartGraph.Parent, startGraphFor(null))

    @Test
    fun setUpOpensParent() = assertEquals(StartGraph.Parent, startGraphFor(session("set_up")))

    @Test
    fun endedOpensParent() = assertEquals(StartGraph.Parent, startGraphFor(session("ended")))

    @Test
    fun runningOpensSession() = assertEquals(StartGraph.Session, startGraphFor(session("running")))

    @Test
    fun lockedOpensSession() = assertEquals(StartGraph.Session, startGraphFor(session("locked")))
}
