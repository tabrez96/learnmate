package app.learnmate.ui.firstrun

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.FamilyRequestDto
import app.learnmate.data.family.FamilyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.IOException

/** Holds the S01 first-run logic; the screen only draws [state] and forwards taps. */
class FirstRunController(
    private val family: FamilyRepository,
    private val scope: CoroutineScope,
    private val pollMillis: Long = 3_000,
) {
    private val _state = MutableStateFlow(FirstRunUiState())
    val state: StateFlow<FirstRunUiState> = _state.asStateFlow()

    private var pollJob: Job? = null

    fun load() {
        _state.update { it.copy(loading = true, loadFailed = false, error = null) }
        scope.launch {
            try {
                val f = family.get()
                _state.update {
                    if (f == null) {
                        it.copy(loading = false)
                    } else {
                        it.copy(
                            loading = false,
                            childName = f.childName,
                            grade = f.grade,
                            familySaved = true,
                            telegramConnected = f.telegramConnected,
                            telegramHandle = f.telegramHandle,
                            fallbackSet = f.fallbackSet,
                        )
                    }
                }
                // A code issued before the screen was recreated may still be sent, so keep watching.
                if (f != null && !f.telegramConnected) startPolling()
            } catch (_: ApiError) {
                _state.update { it.copy(loading = false, loadFailed = true, error = NETWORK_ERROR) }
            }
        }
    }

    fun setName(v: String) = _state.update { if (it.busy) it else it.copy(childName = v, error = null) }

    fun setGrade(v: Int) = _state.update { if (it.busy) it else it.copy(grade = v) }

    fun setPassword(v: String) = _state.update { if (it.busy) it else it.copy(password = v) }

    fun setPasswordAgain(v: String) = _state.update { if (it.busy) it else it.copy(passwordAgain = v) }

    fun getLinkCode() {
        val s = _state.value
        if (s.busy || !s.childValid) return
        _state.update { it.copy(busy = true, error = null) }
        scope.launch {
            try {
                family.save(FamilyRequestDto(s.childName.trim(), s.grade!!))
                val code = family.telegramCode()
                _state.update { it.copy(familySaved = true, linkCode = code, busy = false) }
                startPolling()
            } catch (_: ApiError) {
                _state.update { it.copy(busy = false, error = NETWORK_ERROR) }
            }
        }
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob =
            scope.launch {
                while (true) {
                    delay(pollMillis)
                    val f =
                        try {
                            family.get()
                        } catch (_: ApiError) {
                            null
                        }
                    if (f?.telegramConnected == true) {
                        _state.update { it.copy(telegramConnected = true, telegramHandle = f.telegramHandle, linkCode = null) }
                        break
                    }
                }
            }
    }

    fun finish(onDone: () -> Unit) {
        val s = _state.value
        if (!s.canFinish) return
        _state.update { it.copy(busy = true, error = null) }
        scope.launch {
            try {
                family.save(FamilyRequestDto(s.childName.trim(), s.grade!!))
                if (!s.fallbackSet) {
                    try {
                        family.setFallbackPassword(s.password)
                    } catch (_: IOException) {
                        // The server took the password (resending would be refused); only the offline copy failed.
                        _state.update { it.copy(busy = false, fallbackSet = true, error = CACHE_ERROR) }
                        return@launch
                    }
                    _state.update { it.copy(fallbackSet = true, password = "", passwordAgain = "") }
                }
                _state.update { it.copy(busy = false) }
                onDone()
            } catch (_: ApiError) {
                _state.update { it.copy(busy = false, error = NETWORK_ERROR) }
            }
        }
    }
}
