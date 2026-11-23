package app.learnmate.data.family

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.DeleteDataRequestDto
import app.learnmate.data.api.FallbackRequestDto
import app.learnmate.data.api.FamilyDto
import app.learnmate.data.api.FamilyRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.apiCall
import app.learnmate.data.settings.FallbackPasswordCache
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.withContext

class FamilyRepository(
    private val api: LearnmateApi,
    private val fallbackCache: FallbackPasswordCache,
) {
    /** Null before first-run setup (the server answers 404). */
    suspend fun get(): FamilyDto? =
        try {
            apiCall { api.family() }
        } catch (_: ApiError.NotFound) {
            null
        }

    suspend fun save(request: FamilyRequestDto): FamilyDto = apiCall { api.putFamily(request) }

    /**
     * Also caches the password's hash so a session can be force-ended offline. Once the server has accepted the
     * password the cache write cannot be cancelled, so the two never disagree because of cancellation. A storage
     * failure still propagates to the caller.
     */
    suspend fun setFallbackPassword(
        password: String,
        currentPassword: String? = null,
    ) {
        apiCall { api.putFallback(FallbackRequestDto(password, currentPassword)) }
        withContext(NonCancellable) { fallbackCache.store(password) }
    }

    suspend fun telegramCode(): String = apiCall { api.telegramCode() }.code

    suspend fun deleteAllData(password: String) = apiCall { api.deleteData(DeleteDataRequestDto(password)) }
}
