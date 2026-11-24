package app.learnmate.session.mentor

import app.learnmate.data.api.ApiError
import app.learnmate.data.api.LessonDto
import app.learnmate.data.api.LessonStepDto
import app.learnmate.data.api.MessageDto
import app.learnmate.data.mentor.MentorRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Holds the S05 logic; the screen only draws [state] and forwards taps. */
class MentorController(
    private val sessionId: Long,
    private val startStep: Int,
    private val mentor: MentorRepository,
    private val outsideAllowed: suspend () -> Boolean,
    private val saveStep: suspend (Int) -> Unit,
    private val scope: CoroutineScope,
) {
    private val _state = MutableStateFlow(MentorUiState())
    val state: StateFlow<MentorUiState> = _state

    private var lesson: LessonDto? = null
    private val failedActions = mutableMapOf<String, suspend () -> Unit>()
    private val failedCheckSteps = mutableMapOf<String, Int>()
    private var counter = 0

    private fun nextKey() = "i${counter++}"

    fun load() {
        scope.launch {
            guarded {
                try {
                    val allowed = outsideAllowed()
                    val loaded = mentor.lesson(sessionId)
                    val history = mentor.messages(sessionId)
                    lesson = loaded
                    val index = startStep.coerceIn(0, maxOf(0, loaded.steps.lastIndex))
                    val items = mutableListOf<ChatItem>()
                    loaded.steps.take(index + 1).forEach { items += stepItems(it, loaded.steps.lastIndex) }
                    var lastStudent: String? = null
                    history.forEach { m ->
                        if (m.role == "student") {
                            lastStudent = m.text
                            items += ChatItem.Student(nextKey(), m.text)
                        } else {
                            items += answerItem(m, lastStudent, allowed)
                        }
                    }
                    _state.update {
                        it.copy(
                            topic = loaded.topic ?: "",
                            stepTitles = loaded.steps.map { s -> s.title },
                            stepIndex = index,
                            teachingFrom = teachingFromLine(loaded),
                            items = items,
                            outsideAllowed = allowed,
                            budgetMessage = null,
                            ready = true,
                        )
                    }
                } finally {
                    _state.update { it.copy(loading = false) }
                }
            }
        }
    }

    fun answer(
        stepIndex: Int,
        option: Int,
    ) {
        val current = _state.value
        val check = current.items.filterIsInstance<ChatItem.Check>().firstOrNull { it.stepIndex == stepIndex }
        if (current.typing || check == null || check.answered != null) return
        scope.launch {
            guarded(checkStep = stepIndex) {
                // A stale retry must not overwrite an answer the server already accepted.
                val open = _state.value.items.firstOrNull { it.key == check.key } as? ChatItem.Check
                if (open == null || open.answered != null) return@guarded
                val studentKey = nextKey()
                _state.update { s ->
                    s.copy(
                        items =
                            s.items.map { if (it.key == check.key) check.copy(answered = option) else it } +
                                ChatItem.Student(studentKey, check.options[option]),
                    )
                }
                val r =
                    try {
                        mentor.answerCheck(sessionId, stepIndex, option)
                    } catch (e: ApiError) {
                        // Not recorded by the server: reopen the check so Next step stays locked until a retry works.
                        _state.update { s ->
                            s.copy(
                                items =
                                    s.items
                                        .filter { it.key != studentKey }
                                        .map { if (it is ChatItem.Check && it.key == check.key) it.copy(answered = null) else it },
                            )
                        }
                        throw e
                    }
                val steps = lesson?.steps.orEmpty()
                val source = steps.getOrNull(stepIndex)?.let { sourceLine(it.sources) }
                val result = ChatItem.Mentor(nextKey(), checkResultText(r.correct, r.pointsAwarded, r.explanation), source)
                val stale = failedCheckSteps.filterValues { it == stepIndex }.keys.toSet()
                stale.forEach {
                    failedCheckSteps.remove(it)
                    failedActions.remove(it)
                }
                _state.update { s ->
                    s.copy(items = s.items.filter { it.key !in stale } + result + readyFor(stepIndex, steps.lastIndex))
                }
            }
        }
    }

    fun nextStep() {
        val current = _state.value
        val steps = lesson?.steps ?: return
        if (!current.canGoNext) return
        val index = current.stepIndex + 1
        _state.update { it.copy(stepIndex = index, items = it.items + stepItems(steps[index], steps.lastIndex)) }
        scope.launch { saveStep(index) }
    }

    fun explainAgain() {
        val s = _state.value
        val title = s.stepTitles.getOrNull(s.stepIndex) ?: return
        send("Can you explain \"$title\" again?", outside = false)
    }

    fun send(
        text: String,
        outside: Boolean,
    ) {
        val question = text.trim()
        val current = _state.value
        if (question.isEmpty() || !current.ready || current.typing || current.budgetMessage != null) return
        if (outside && !current.outsideAllowed) return
        _state.update { it.copy(items = it.items + ChatItem.Student(nextKey(), question)) }
        ask(question, outside)
    }

    fun checkOutside(question: String) {
        val current = _state.value
        if (!current.ready || current.typing || current.budgetMessage != null || !current.outsideAllowed) return
        _state.update { s ->
            s.copy(
                items =
                    s.items.map {
                        if (it is ChatItem.Mentor &&
                            it.checkOutsideFor == question
                        ) {
                            it.copy(checkOutsideFor = null)
                        } else {
                            it
                        }
                    },
            )
        }
        ask(question, outside = true)
    }

    fun retry(key: String) {
        if (_state.value.typing) return
        val action = failedActions.remove(key) ?: return
        val checkStep = failedCheckSteps.remove(key)
        _state.update { s -> s.copy(items = s.items.filter { it.key != key }) }
        scope.launch { guarded(checkStep, action) }
    }

    private fun ask(
        question: String,
        outside: Boolean,
    ) {
        scope.launch {
            guarded {
                val reply = mentor.ask(sessionId, question, outside).answer
                _state.update { it.copy(items = it.items + answerItem(reply, question, it.outsideAllowed)) }
            }
        }
    }

    private suspend fun guarded(
        checkStep: Int? = null,
        action: suspend () -> Unit,
    ) {
        _state.update { it.copy(typing = true) }
        try {
            action()
        } catch (e: ApiError.BudgetReached) {
            _state.update { it.copy(budgetMessage = e.detail) }
        } catch (_: ApiError) {
            val key = nextKey()
            failedActions[key] = action
            checkStep?.let { failedCheckSteps[key] = it }
            _state.update { it.copy(items = it.items + ChatItem.ConnectionLost(key)) }
        } finally {
            _state.update { it.copy(typing = false) }
        }
    }

    private fun answerItem(
        m: MessageDto,
        question: String?,
        allowed: Boolean,
    ): ChatItem =
        if (m.outside) {
            ChatItem.Outside(nextKey(), m.text, outsideSourceLine(m.sourceUrl), m.visual != null)
        } else {
            ChatItem.Mentor(
                nextKey(),
                m.text,
                sourceLine(m.sources),
                m.visual != null,
                question.takeIf { m.canCheckOutside && allowed },
            )
        }

    private fun stepItems(
        step: LessonStepDto,
        lastIndex: Int,
    ): List<ChatItem> {
        val source = sourceLine(step.sources)
        val check = step.check
        val answered = check.answerIndex
        val items = mutableListOf<ChatItem>(ChatItem.Mentor(nextKey(), step.body, source))
        items += ChatItem.Check(nextKey(), step.index, check.prompt, check.options, answered)
        if (answered != null) {
            items += ChatItem.Student(nextKey(), check.options.getOrElse(answered) { "" })
            items += ChatItem.Mentor(nextKey(), checkResultText(answered == check.correctIndex, null, check.explanation ?: ""), source)
            items += readyFor(step.index, lastIndex)
        }
        return items
    }

    private fun readyFor(
        stepIndex: Int,
        lastIndex: Int,
    ): List<ChatItem> = if (stepIndex == lastIndex) listOf(ChatItem.ReadyForTest(nextKey())) else emptyList()
}
