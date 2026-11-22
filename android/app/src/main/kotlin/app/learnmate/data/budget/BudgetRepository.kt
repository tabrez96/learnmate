package app.learnmate.data.budget

import app.learnmate.data.api.BudgetDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.apiCall

class BudgetRepository(
    private val api: LearnmateApi,
) {
    suspend fun current(): BudgetDto = apiCall { api.budget() }
}
