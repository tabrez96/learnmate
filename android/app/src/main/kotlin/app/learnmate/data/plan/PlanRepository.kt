package app.learnmate.data.plan

import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.PlanDto
import app.learnmate.data.api.ProgressDto
import app.learnmate.data.api.StepPatchDto
import app.learnmate.data.api.apiCall

class PlanRepository(
    private val api: LearnmateApi,
) {
    suspend fun plan(sessionId: Long): PlanDto = apiCall { api.plan(sessionId) }

    suspend fun complete(
        sessionId: Long,
        key: String,
    ): PlanDto = apiCall { api.patchPlanStep(sessionId, key, StepPatchDto("done")) }

    suspend fun skip(
        sessionId: Long,
        key: String,
    ): PlanDto = apiCall { api.patchPlanStep(sessionId, key, StepPatchDto("skipped")) }

    suspend fun progress(): ProgressDto = apiCall { api.progress() }
}
