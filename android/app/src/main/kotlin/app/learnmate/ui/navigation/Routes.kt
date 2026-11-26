package app.learnmate.ui.navigation

import kotlinx.serialization.Serializable

@Serializable data object ParentGraph

@Serializable data object SessionGraph

// Parent graph
@Serializable data object FirstRun

@Serializable data object ParentHome

@Serializable data object TodaysMaterial

@Serializable data object HandOver

@Serializable data object Settings

// Session graph
@Serializable data object SessionHome

@Serializable data object Mentor

@Serializable data object Test

@Serializable data object TestResult

@Serializable data object EndSession

@Serializable data object SessionLocked
