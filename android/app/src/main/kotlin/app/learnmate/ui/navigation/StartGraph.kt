package app.learnmate.ui.navigation

import app.learnmate.data.db.CurrentSessionEntity

enum class StartGraph { Parent, Session }

/** Server states in which the child holds the tablet ("set_up" is still with the parent on S03). */
private val SessionStates = setOf("running", "locked")

fun startGraphFor(session: CurrentSessionEntity?): StartGraph =
    if (session?.state in SessionStates) StartGraph.Session else StartGraph.Parent
