package app.learnmate.ui.mentor

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.learnmate.AppContainer
import app.learnmate.data.api.ApiError
import app.learnmate.data.mentor.MentorRepository
import app.learnmate.data.settings.Appearance
import app.learnmate.domain.StepState
import app.learnmate.session.mentor.BOOKS_ONLY_FOOTER
import app.learnmate.session.mentor.CONNECTION_LOST
import app.learnmate.session.mentor.ChatItem
import app.learnmate.session.mentor.MentorController
import app.learnmate.session.mentor.MentorUiState
import app.learnmate.session.mentor.READY_FOR_TEST
import app.learnmate.session.mentor.VISUAL_PLACEHOLDER
import app.learnmate.session.mentor.elapsedMinutes
import app.learnmate.ui.components.AlertTone
import app.learnmate.ui.components.ChipTone
import app.learnmate.ui.components.GhostButton
import app.learnmate.ui.components.LearnmateAlert
import app.learnmate.ui.components.LearnmateCard
import app.learnmate.ui.components.LearnmateChip
import app.learnmate.ui.components.LearnmateProgressBar
import app.learnmate.ui.components.LearnmateTopBar
import app.learnmate.ui.components.PrimaryButton
import app.learnmate.ui.components.SecondaryButton
import app.learnmate.ui.components.SessionPill
import app.learnmate.ui.components.SplitSendButton
import app.learnmate.ui.components.StepRow
import app.learnmate.ui.components.ThemeSwitch
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateSpacing
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.cardSurface
import app.learnmate.ui.theme.gradientGlow
import app.learnmate.ui.theme.pageBackground
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private val BubbleShape = RoundedCornerShape(20.dp)
private val BubblePadding = Modifier.padding(horizontal = 16.dp, vertical = 14.dp)

@Composable
fun MentorScreen(
    state: MentorUiState,
    dark: Boolean,
    elapsedMinutes: Int,
    onDarkChange: (Boolean) -> Unit,
    onBack: () -> Unit,
    onAnswer: (stepIndex: Int, option: Int) -> Unit,
    onNextStep: () -> Unit,
    onExplainAgain: () -> Unit,
    onSend: (text: String, outside: Boolean) -> Unit,
    onCheckOutside: (question: String) -> Unit,
    onRetry: (key: String) -> Unit,
    onReadyForTest: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxSize().pageBackground(LearnmateTheme.colors.paper, LearnmateTheme.surfaces)) {
        LearnmateTopBar {
            ThemeSwitch(dark, onDarkChange)
            SessionPill(elapsedMinutes)
        }
        BoxWithConstraints(Modifier.fillMaxSize()) {
            val padding =
                Modifier.padding(
                    vertical = LearnmateSpacing.screenPaddingVertical,
                    horizontal = LearnmateSpacing.screenPaddingHorizontal,
                )
            val compact = maxWidth < 720.dp
            val chat: @Composable (Modifier) -> Unit = {
                ChatCard(state, compact, onAnswer, onNextStep, onExplainAgain, onSend, onCheckOutside, onRetry, onReadyForTest, it)
            }
            // ux.md: screens stack into one column below 720 dp.
            val panelMax = maxHeight * 0.35f
            if (compact) {
                Column(Modifier.fillMaxSize().then(padding), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    // Bounded and scrollable so the chat and composer keep height when the keyboard is open.
                    Box(Modifier.heightIn(max = panelMax).verticalScroll(rememberScrollState())) {
                        StepPanel(state, onBack, Modifier.fillMaxWidth())
                    }
                    chat(Modifier.weight(1f).fillMaxWidth())
                }
            } else {
                Row(Modifier.fillMaxSize().then(padding), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                    StepPanel(state, onBack, Modifier.width(300.dp).align(Alignment.Top))
                    chat(Modifier.weight(1f).fillMaxHeight())
                }
            }
        }
    }
}

@Composable
private fun StepPanel(
    state: MentorUiState,
    onBack: () -> Unit,
    modifier: Modifier,
) {
    val colors = LearnmateTheme.colors
    LearnmateCard(modifier) {
        GhostButton("← Today's plan", onBack)
        Column {
            Text(state.topic, color = colors.ink, style = MaterialTheme.typography.titleLarge)
            if (state.stepTitles.isNotEmpty()) Text(state.stepLabel, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
        }
        LearnmateProgressBar(state.progress)
        Column {
            state.stepTitles.forEachIndexed { i, title ->
                val stepState =
                    when {
                        i < state.stepIndex -> StepState.Done
                        i == state.stepIndex -> StepState.Current
                        else -> StepState.Upcoming
                    }
                StepRow(i + 1, title, "", stepState, compact = true)
            }
        }
        state.teachingFrom?.let { Text(it, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall) }
    }
}

@Composable
private fun ChatCard(
    state: MentorUiState,
    compact: Boolean,
    onAnswer: (Int, Int) -> Unit,
    onNextStep: () -> Unit,
    onExplainAgain: () -> Unit,
    onSend: (String, Boolean) -> Unit,
    onCheckOutside: (String) -> Unit,
    onRetry: (String) -> Unit,
    onReadyForTest: () -> Unit,
    modifier: Modifier,
) {
    val listState = rememberLazyListState()
    val showTyping = state.typing || (state.loading && state.items.isEmpty())
    val count = state.items.size + if (showTyping) 1 else 0
    LaunchedEffect(count) { if (count > 0) listState.animateScrollToItem(count - 1) }
    LearnmateCard(modifier) {
        state.budgetMessage?.let { LearnmateAlert(it, AlertTone.Warning, title = "Lessons are paused") }
        BoxWithConstraints(Modifier.weight(1f).fillMaxWidth()) {
            val bubbleMax = maxWidth * 0.8f
            LazyColumn(
                Modifier.fillMaxSize().testTag("chat").semantics { liveRegion = LiveRegionMode.Polite },
                state = listState,
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(state.items, key = { it.key }) { item ->
                    ChatBubble(item, state, bubbleMax, onAnswer, onCheckOutside, onRetry, onReadyForTest)
                }
                if (showTyping) item(key = "typing") { TypingBubble() }
            }
        }
        Composer(state, compact, onNextStep, onExplainAgain, onSend)
    }
}

@Composable
private fun ChatBubble(
    item: ChatItem,
    state: MentorUiState,
    max: Dp,
    onAnswer: (Int, Int) -> Unit,
    onCheckOutside: (String) -> Unit,
    onRetry: (String) -> Unit,
    onReadyForTest: () -> Unit,
) {
    val colors = LearnmateTheme.colors
    when (item) {
        is ChatItem.Student -> StudentBubble(item.text, max)
        is ChatItem.Mentor ->
            MentorBubble(max) {
                Text(item.text, color = colors.ink, style = MaterialTheme.typography.bodyLarge)
                if (item.hasVisual) VisualPlaceholder(colors.paper)
                item.source?.let { Text(it, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall) }
                val question = item.checkOutsideFor
                if (question != null && state.outsideAllowed) SecondaryButton("Check outside the books", { onCheckOutside(question) })
            }
        is ChatItem.Outside ->
            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) {
                Column(
                    Modifier.widthIn(max = max).background(colors.amberTint, BubbleShape).then(BubblePadding),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    LearnmateChip("Checked outside your books", ChipTone.Warn)
                    Text(item.text, color = colors.amberText, style = MaterialTheme.typography.bodyLarge)
                    if (item.hasVisual) VisualPlaceholder(colors.card)
                    item.source?.let { Text(it, color = colors.amberText, style = MaterialTheme.typography.bodySmall) }
                }
            }
        is ChatItem.Check ->
            MentorBubble(max) {
                Text("Quick check: ${item.prompt}", color = colors.ink, style = MaterialTheme.typography.bodyLarge)
                if (item.answered == null) {
                    @OptIn(ExperimentalLayoutApi::class)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        item.options.forEachIndexed { i, option -> QuickChip(option, true) { onAnswer(item.stepIndex, i) } }
                    }
                }
            }
        is ChatItem.ReadyForTest ->
            MentorBubble(max) {
                Text(READY_FOR_TEST, color = colors.ink, style = MaterialTheme.typography.bodyLarge)
                PrimaryButton("Start the test", onReadyForTest)
            }
        is ChatItem.ConnectionLost ->
            MentorBubble(max) {
                Text(CONNECTION_LOST, color = colors.ink, style = MaterialTheme.typography.bodyLarge)
                SecondaryButton("Try again", { onRetry(item.key) })
            }
    }
}

@Composable
private fun MentorBubble(
    max: Dp,
    content: @Composable () -> Unit,
) {
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) {
        Column(
            Modifier
                .widthIn(max = max)
                .cardSurface(LearnmateTheme.surfaces, LearnmateTheme.colors.card, BubbleShape)
                .then(BubblePadding),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) { content() }
    }
}

@Composable
private fun StudentBubble(
    text: String,
    max: Dp,
) {
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterEnd) {
        Text(
            text,
            color = Color.White,
            style = MaterialTheme.typography.bodyLarge,
            modifier =
                Modifier
                    .widthIn(max = max)
                    .gradientGlow(LearnmateTheme.surfaces, BubbleShape)
                    .background(LearnmateTheme.gradients.brand, BubbleShape)
                    .then(BubblePadding),
        )
    }
}

@Composable
private fun VisualPlaceholder(background: Color) {
    Text(
        VISUAL_PLACEHOLDER,
        color = LearnmateTheme.colors.inkSoft,
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier.fillMaxWidth().background(background, LearnmateShapes.button).padding(14.dp),
    )
}

@Composable
private fun TypingBubble() {
    val soft = LearnmateTheme.colors.inkSoft
    MentorBubble(120.dp) {
        Row(
            Modifier.semantics { contentDescription = "Mentor is typing" },
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            repeat(3) { Box(Modifier.size(8.dp).background(soft, CircleShape)) }
        }
    }
}

/** Quick reply and check option chip. */
@Composable
private fun QuickChip(
    text: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val colors = LearnmateTheme.colors
    val shape = LearnmateShapes.button
    Box(
        Modifier
            .alpha(if (enabled) 1f else 0.4f)
            .defaultMinSize(minHeight = 44.dp)
            .background(colors.blueTint, shape)
            .border(BorderStroke(1.dp, colors.blue.copy(alpha = 0.35f)), shape)
            .clip(shape)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = 16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = colors.blueText, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
private fun Composer(
    state: MentorUiState,
    compact: Boolean,
    onNextStep: () -> Unit,
    onExplainAgain: () -> Unit,
    onSend: (String, Boolean) -> Unit,
) {
    val colors = LearnmateTheme.colors
    var text by rememberSaveable { mutableStateOf("") }
    val canSend = state.ready && !state.typing && state.budgetMessage == null && text.isNotBlank()

    fun submit(outside: Boolean) {
        if (!canSend) return
        onSend(text, outside)
        text = ""
    }
    val chips: @Composable () -> Unit = {
        QuickChip("Next step", state.canGoNext, onNextStep)
        val canExplain = state.ready && !state.typing && state.budgetMessage == null && state.stepTitles.isNotEmpty()
        QuickChip("Explain again", canExplain, onExplainAgain)
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        // On narrow windows the quick replies get their own row so the text field keeps its width.
        if (compact) Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) { chips() }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            if (!compact) chips()
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                modifier =
                    Modifier
                        .weight(1f)
                        .testTag("composer")
                        .onPreviewKeyEvent {
                            val enter = it.key == Key.Enter && it.type == KeyEventType.KeyDown
                            if (enter) submit(false)
                            enter
                        },
                enabled = state.budgetMessage == null,
                placeholder = { Text("Ask your mentor…") },
                singleLine = true,
                shape = LearnmateShapes.input,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { submit(false) }),
            )
            SplitSendButton(
                onSend = { submit(false) },
                onSendOutside = { submit(true) },
                showMenu = state.outsideAllowed,
                enabled = canSend,
            )
        }
        if (!state.outsideAllowed) Text(BOOKS_ONLY_FOOTER, color = colors.inkSoft, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun MentorRoute(
    container: AppContainer,
    onBack: () -> Unit,
    onReadyForTest: () -> Unit,
    mentorRepository: MentorRepository = container.mentorRepository,
) {
    val session by container.sessionRepository.current.collectAsState(initial = null)
    val current = session ?: return
    val scope = rememberCoroutineScope()
    val controller =
        remember(current.id) {
            MentorController(
                current.id,
                current.stepIndex,
                mentorRepository,
                outsideAllowed = {
                    try {
                        container.familyRepository.get()?.outsideBooksAllowed ?: false
                    } catch (_: ApiError) {
                        false
                    }
                },
                saveStep = { i -> container.sessionRepository.saveProgress(i, current.testQuestionIndex, current.testCorrect) },
                scope = scope,
            )
        }
    LaunchedEffect(controller) { controller.load() }
    val state by controller.state.collectAsState()
    val appearance by container.appearanceRepository.appearance.collectAsState(initial = null)
    val systemDark = isSystemInDarkTheme()
    val minutes by produceState(elapsedMinutes(current.startedAt, System.currentTimeMillis()), current.startedAt) {
        while (true) {
            value = elapsedMinutes(current.startedAt, System.currentTimeMillis())
            delay(30_000)
        }
    }
    MentorScreen(
        state = state,
        dark = appearance?.isDark(systemDark) ?: systemDark,
        elapsedMinutes = minutes,
        onDarkChange = { scope.launch { container.appearanceRepository.setAppearance(if (it) Appearance.Dark else Appearance.Light) } },
        onBack = onBack,
        onAnswer = controller::answer,
        onNextStep = controller::nextStep,
        onExplainAgain = controller::explainAgain,
        onSend = controller::send,
        onCheckOutside = controller::checkOutside,
        onRetry = controller::retry,
        onReadyForTest = onReadyForTest,
    )
}
