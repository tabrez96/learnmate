package app.learnmate.ui.navigation

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.FamilyDto
import app.learnmate.data.api.familyDto
import app.learnmate.data.db.CurrentSessionEntity
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
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

    private val complete = familyDto().copy(telegramConnected = true, fallbackSet = true)

    @Test
    fun needsFirstRunRules() {
        assertTrue(needsFirstRun(null))
        assertTrue(needsFirstRun(complete.copy(telegramConnected = false)))
        assertTrue(needsFirstRun(complete.copy(fallbackSet = false)))
        assertFalse(needsFirstRun(complete))
    }

    @Test
    fun runningSessionSkipsTheFamilyCall() =
        runTest {
            val graph = resolveStartGraph(session("running")) { error("must not be called") }
            assertEquals(StartGraph.Session, graph)
        }

    @Test
    fun incompleteFamilyOpensFirstRun() =
        runTest {
            assertEquals(StartGraph.FirstRun, resolveStartGraph(null) { complete.copy(fallbackSet = false) })
            assertEquals(StartGraph.FirstRun, resolveStartGraph(session("set_up")) { null as FamilyDto? })
        }

    @Test
    fun completeFamilyOpensParent() =
        runTest {
            assertEquals(StartGraph.Parent, resolveStartGraph(null) { complete })
        }

    @Test
    fun unreachableServerOpensParent() =
        runTest {
            assertEquals(StartGraph.Parent, resolveStartGraph(null) { throw ApiError.Network("down") })
        }
}
