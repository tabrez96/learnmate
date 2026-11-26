package app.learnmate.ui.navigation

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.FamilyDto
import app.learnmate.data.db.CurrentSessionEntity

enum class StartGraph { FirstRun, Parent, Session }

/** Server states in which the child holds the tablet ("set_up" is still with the parent on S03). */
private val SessionStates = setOf("running", "locked")

fun startGraphFor(session: CurrentSessionEntity?): StartGraph =
    if (session?.state in SessionStates) StartGraph.Session else StartGraph.Parent

/** Setup is complete once the server has the family with Telegram linked and a fallback password. */
fun needsFirstRun(family: FamilyDto?): Boolean = family == null || !family.telegramConnected || !family.fallbackSet

/** A running session wins; a server that can't be reached opens parent home rather than trapping the parent in setup. */
suspend fun resolveStartGraph(
    session: CurrentSessionEntity?,
    family: suspend () -> FamilyDto?,
): StartGraph {
    if (startGraphFor(session) == StartGraph.Session) return StartGraph.Session
    val f =
        try {
            family()
        } catch (_: ApiError) {
            return StartGraph.Parent
        }
    return if (needsFirstRun(f)) StartGraph.FirstRun else StartGraph.Parent
}
