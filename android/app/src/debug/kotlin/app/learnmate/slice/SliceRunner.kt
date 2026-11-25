package app.learnmate.slice

import app.learnmate.data.api.FamilyRequestDto
import app.learnmate.data.api.SessionRequestDto
import app.learnmate.data.budget.BudgetRepository
import app.learnmate.data.family.FamilyRepository
import app.learnmate.data.materials.MaterialRepository
import app.learnmate.data.materials.UploadFile
import app.learnmate.data.session.SessionRepository
import app.learnmate.data.subjects.SubjectRepository
import kotlinx.coroutines.delay

class SliceError(
    message: String,
) : Exception(message)

const val POLL_MS = 2_000L
const val MAX_POLLS = 450 // 15 minutes

private val ACTIVE_STATES = setOf("set_up", "running", "locked")

/** The launcher's logic: set up, upload one chapter, wait until it is read, then create and start a learn session. */
class SliceRunner(
    private val family: FamilyRepository,
    private val subjects: SubjectRepository,
    private val materials: MaterialRepository,
    private val sessions: SessionRepository,
    private val budget: BudgetRepository,
    private val log: SliceLog,
    private val pause: suspend (Long) -> Unit = { delay(it) },
    private val now: () -> Long = System::currentTimeMillis,
) {
    private val pins = mutableMapOf<Long, String>()

    /** Returns the started session's id. Throws SliceError or ApiError. */
    suspend fun run(
        subjectName: String,
        file: UploadFile,
        onStatus: (String) -> Unit,
    ): Long {
        val name = subjectName.trim()
        if (name.isEmpty()) throw SliceError("Enter a subject name")
        log.reset()
        onStatus("Reading the AI budget")
        log.spentBefore = budget.current().spentUsd
        if (family.get() == null) {
            onStatus("Creating the family")
            family.save(FamilyRequestDto(childName = "Test student", grade = 7, outsideBooksAllowed = false))
        }
        onStatus("Finding the subject")
        val subject = subjects.list().firstOrNull { it.name.equals(name, ignoreCase = true) } ?: subjects.create(name)
        onStatus("Uploading ${file.name}")
        val started = now()
        var material = materials.upload(subject.id, listOf(file))
        var polls = 0
        while (material.status == "reading") {
            if (polls++ >= MAX_POLLS) throw SliceError("Still reading after 15 minutes")
            pause(POLL_MS)
            material = materials.get(material.id)
            onStatus("Reading: ${material.pagesRead}/${material.pagesTotal ?: "?"} pages")
        }
        if (material.status == "failed") throw SliceError("Reading failed: ${material.error ?: "no detail"}")
        log.material = material.title
        log.pagesTotal = material.pagesTotal
        log.pagesRead = material.pagesRead
        log.chapters = material.chapters.sortedBy { it.position }.map { it.name }
        log.readingMillis = now() - started
        onStatus("Starting the session")
        val created =
            sessions.create(
                SessionRequestDto(subject.id, "learn", listOf(material.id), material.chapters.map { it.id }, 10),
            )
        pins[created.id] = created.pin
        sessions.start(created.id)
        return created.id
    }

    /** Ends any active session so a new run can start. Returns false when there was none. */
    suspend fun endCurrent(): Boolean {
        val current = sessions.refresh() ?: return false
        if (current.state !in ACTIVE_STATES) return false
        val pin = pins[current.id] ?: sessions.replacePin(current.id).pin
        sessions.end(current.id, pin)
        return true
    }
}
