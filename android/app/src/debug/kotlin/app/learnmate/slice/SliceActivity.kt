package app.learnmate.slice

import android.os.Bundle
import android.provider.OpenableColumns
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import app.learnmate.LearnmateApplication
import app.learnmate.data.api.ApiError
import app.learnmate.data.materials.UploadFile
import app.learnmate.data.mentor.MentorRepository
import app.learnmate.ui.mentor.MentorRoute
import app.learnmate.ui.theme.LearnmateTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "SliceRun"
private val FILE_TYPES =
    arrayOf(
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
    )

/** Debug-only launcher for the first end-to-end slice: upload one chapter, then teach it in the real S05. */
class SliceActivity : ComponentActivity() {
    private val container by lazy { (application as LearnmateApplication).container }
    private val log = SliceLog()
    private val mentorRepository by lazy { MentorRepository(TimedLearnmateApi(container.api, log)) }
    private val runner by lazy {
        SliceRunner(
            container.familyRepository,
            container.subjectRepository,
            container.materialRepository,
            container.sessionRepository,
            container.budgetRepository,
            log,
        )
    }

    // Plain fields on purpose: the run log lives only in memory.
    private var state by mutableStateOf(SliceState())
    private var inMentor by mutableStateOf(false)
    private var file: UploadFile? = null

    private val picker =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            if (uri == null) return@registerForActivityResult
            lifecycleScope.launch {
                try {
                    val picked =
                        withContext(Dispatchers.IO) {
                            val name =
                                contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
                                    if (it.moveToFirst()) it.getString(0) else null
                                } ?: "chapter"
                            val mime = contentResolver.getType(uri) ?: "application/octet-stream"
                            UploadFile(name, mime, contentResolver.openInputStream(uri)!!.use { it.readBytes() })
                        }
                    file = picked
                    state = state.copy(fileName = picked.name)
                } catch (e: Exception) {
                    addStatus("Failed: could not read the file (${e.message})")
                }
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        lifecycleScope.launch {
            try {
                state = state.copy(canResume = container.sessionRepository.refresh()?.state == "running")
            } catch (e: ApiError) {
                addStatus("Failed: ${e.message}")
            }
        }
        setContent {
            LearnmateTheme {
                BackHandler(inMentor) { leaveMentor() }
                if (inMentor) {
                    MentorRoute(
                        container,
                        onBack = ::leaveMentor,
                        onReadyForTest = ::leaveMentor,
                        mentorRepository = mentorRepository,
                    )
                } else {
                    SliceScreen(
                        state,
                        onSubjectChange = { state = state.copy(subject = it) },
                        onPickFile = { picker.launch(FILE_TYPES) },
                        onRun = ::run,
                        onResume = { inMentor = true },
                        onEndCurrent = ::endCurrent,
                        onRefreshCost = ::recordCost,
                    )
                }
            }
        }
    }

    private fun run() {
        val upload = file ?: return
        state = state.copy(busy = true)
        lifecycleScope.launch {
            try {
                runner.run(state.subject, upload, ::addStatus)
                state = state.copy(canResume = true)
                inMentor = true
            } catch (e: SliceError) {
                addStatus("Failed: ${e.message}")
            } catch (e: ApiError) {
                addStatus("Failed: ${e.message}")
            } finally {
                state = state.copy(busy = false)
                refreshLog()
            }
        }
    }

    private fun endCurrent() {
        lifecycleScope.launch {
            try {
                addStatus(if (runner.endCurrent()) "Ended session" else "No active session")
                state = state.copy(canResume = false)
            } catch (e: ApiError) {
                addStatus("Failed: ${e.message}")
            }
        }
    }

    private fun recordCost() {
        lifecycleScope.launch {
            try {
                log.spentAfter = container.budgetRepository.current().spentUsd
                refreshLog()
            } catch (e: ApiError) {
                addStatus("Failed: ${e.message}")
            }
        }
    }

    private fun leaveMentor() {
        inMentor = false
        refreshLog()
    }

    private fun addStatus(line: String) {
        Log.i(TAG, line)
        state = state.copy(status = state.status + line)
    }

    private fun refreshLog() {
        val markdown = log.toMarkdown()
        Log.i(TAG, markdown)
        state = state.copy(log = markdown)
    }
}
