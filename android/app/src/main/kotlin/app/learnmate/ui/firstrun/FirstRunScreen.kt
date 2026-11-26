package app.learnmate.ui.firstrun

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuAnchorType
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import app.learnmate.AppContainer
import app.learnmate.data.settings.Appearance
import app.learnmate.domain.StepState
import app.learnmate.ui.components.AlertTone
import app.learnmate.ui.components.GhostButton
import app.learnmate.ui.components.LearnmateAlert
import app.learnmate.ui.components.LearnmateCard
import app.learnmate.ui.components.LearnmateTopBar
import app.learnmate.ui.components.PasswordField
import app.learnmate.ui.components.PrimaryButton
import app.learnmate.ui.components.SecondaryButton
import app.learnmate.ui.components.StepDot
import app.learnmate.ui.components.TelegramLine
import app.learnmate.ui.components.ThemeSwitch
import app.learnmate.ui.components.description
import app.learnmate.ui.components.learnmateFieldColors
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateSpacing
import app.learnmate.ui.theme.LearnmateTheme
import app.learnmate.ui.theme.pageBackground
import app.learnmate.ui.theme.selectedHalo
import kotlinx.coroutines.launch

private val LockRules =
    listOf(
        "🔒" to "Every session gets its own 4-digit PIN. Only it can end the session.",
        "🔄" to "Make a new PIN any time, before you hand over or from Telegram.",
        "✈️" to "Forgot it? We send the same PIN to Telegram again.",
        "🔑" to "After 3 wrong PINs, the fallback password can force-end the session.",
    )

@Composable
fun FirstRunScreen(
    state: FirstRunUiState,
    dark: Boolean,
    onDarkChange: (Boolean) -> Unit,
    onSettings: () -> Unit,
    onName: (String) -> Unit,
    onGrade: (Int) -> Unit,
    onGetCode: () -> Unit,
    onPassword: (String) -> Unit,
    onPasswordAgain: (String) -> Unit,
    onFinish: () -> Unit,
    onRetryLoad: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxSize().pageBackground(LearnmateTheme.colors.paper, LearnmateTheme.surfaces)) {
        LearnmateTopBar {
            ThemeSwitch(dark, onDarkChange)
            GhostButton("Settings", onSettings)
        }
        BoxWithConstraints(Modifier.fillMaxSize()) {
            val compact = maxWidth < 720.dp
            val padding =
                Modifier.padding(
                    vertical = LearnmateSpacing.screenPaddingVertical,
                    horizontal = LearnmateSpacing.screenPaddingHorizontal,
                )
            val steps: @Composable ColumnScope.() -> Unit = {
                Header()
                when {
                    state.loadFailed -> {
                        LearnmateAlert(NETWORK_ERROR, AlertTone.Error)
                        GhostButton("Try again", onRetryLoad)
                    }
                    state.loading -> repeat(3) { LoadingCard() }
                    else -> {
                        ChildStep(state, compact, onName, onGrade)
                        TelegramStep(state, onGetCode)
                        PasswordStep(state, compact, onPassword, onPasswordAgain)
                    }
                }
            }
            val panel: @Composable ColumnScope.() -> Unit = { LockedPanel(state, onFinish) }
            // ux.md: screens stack into one column below 720 dp; reading order is also focus order.
            if (compact) {
                Column(
                    Modifier.fillMaxSize().verticalScroll(rememberScrollState()).then(padding),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    steps()
                    panel()
                }
            } else {
                Row(
                    Modifier.fillMaxSize().verticalScroll(rememberScrollState()).then(padding),
                    horizontalArrangement = Arrangement.spacedBy(24.dp),
                ) {
                    Column(Modifier.weight(1.55f), verticalArrangement = Arrangement.spacedBy(16.dp), content = steps)
                    Column(Modifier.weight(1f), content = panel)
                }
            }
        }
    }
}

@Composable
private fun Header() {
    val colors = LearnmateTheme.colors
    Column {
        Text("Welcome to Learnmate", color = colors.ink, style = MaterialTheme.typography.headlineLarge)
        Text(
            "Three quick steps, then you can start the first study session.",
            color = colors.inkSoft,
            style = MaterialTheme.typography.bodyLarge,
        )
    }
}

@Composable
private fun LoadingCard() {
    LearnmateCard(Modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().height(48.dp).background(LearnmateTheme.colors.line, LearnmateShapes.button))
    }
}

@Composable
private fun StepCard(
    number: Int,
    title: String,
    stepState: StepState,
    content: @Composable () -> Unit,
) {
    val halo = if (stepState == StepState.Current) Modifier.selectedHalo(LearnmateTheme.surfaces, LearnmateShapes.card) else Modifier
    LearnmateCard(Modifier.fillMaxWidth().then(halo)) {
        Row(
            Modifier.semantics(mergeDescendants = true) {
                heading()
                stateDescription = stepState.description
            },
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            StepDot(number, stepState)
            Text(title, color = LearnmateTheme.colors.ink, style = MaterialTheme.typography.titleLarge)
        }
        content()
    }
}

@Composable
private fun ChildStep(
    state: FirstRunUiState,
    compact: Boolean,
    onName: (String) -> Unit,
    onGrade: (Int) -> Unit,
) {
    StepCard(1, "Your child", state.childStep) {
        val name: @Composable (Modifier) -> Unit = {
            OutlinedTextField(
                state.childName,
                onName,
                it,
                label = { Text("First name") },
                isError = nameError(state.childName) != null,
                supportingText = nameError(state.childName)?.let { msg -> { Text(msg) } },
                singleLine = true,
                enabled = !state.busy,
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
                shape = LearnmateShapes.input,
                colors = learnmateFieldColors(),
            )
        }
        if (compact) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                name(Modifier.fillMaxWidth())
                GradePicker(state.grade, onGrade, Modifier.fillMaxWidth(), !state.busy)
            }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                name(Modifier.weight(1f))
                GradePicker(state.grade, onGrade, Modifier.width(200.dp), !state.busy)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun GradePicker(
    grade: Int?,
    onGrade: (Int) -> Unit,
    modifier: Modifier,
    enabled: Boolean,
) {
    var open by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(open && enabled, { open = it }, modifier) {
        OutlinedTextField(
            grade?.let { "Grade $it" }.orEmpty(),
            {},
            Modifier.menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable).fillMaxWidth(),
            readOnly = true,
            enabled = enabled,
            label = { Text("Grade") },
            singleLine = true,
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(open) },
            shape = LearnmateShapes.input,
            colors = learnmateFieldColors(),
        )
        ExposedDropdownMenu(open, { open = false }) {
            Grades.forEach {
                DropdownMenuItem(text = { Text("Grade $it") }, onClick = {
                    onGrade(it)
                    open = false
                })
            }
        }
    }
}

@Composable
private fun TelegramStep(
    state: FirstRunUiState,
    onGetCode: () -> Unit,
) {
    val colors = LearnmateTheme.colors
    val body = MaterialTheme.typography.bodyLarge
    StepCard(2, "Connect Telegram", state.telegramStep) {
        when {
            state.telegramConnected -> TelegramLine(connectedLine(state.telegramHandle))
            state.linkCode != null -> {
                Text("In Telegram, open the Learnmate bot and send this message:", color = colors.inkSoft, style = body)
                SelectionContainer {
                    Text(
                        "/start ${state.linkCode}",
                        Modifier.background(colors.blueTint, LearnmateShapes.button).padding(14.dp),
                        color = colors.blueText,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        style = body,
                    )
                }
                Text(
                    "Waiting for Telegram…",
                    Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                    color = colors.inkSoft,
                    style = MaterialTheme.typography.bodySmall,
                )
                GhostButton("Get a new code", onGetCode, enabled = !state.busy)
            }
            else -> {
                Text("Grades, alerts and session PINs are sent to you in Telegram.", color = colors.inkSoft, style = body)
                SecondaryButton("Get link code", onGetCode, enabled = state.childValid && !state.busy)
                if (!state.childValid) {
                    Text(
                        "Add your child's first name and grade first.",
                        color = colors.inkSoft,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}

@Composable
private fun PasswordStep(
    state: FirstRunUiState,
    compact: Boolean,
    onPassword: (String) -> Unit,
    onPasswordAgain: (String) -> Unit,
) {
    val colors = LearnmateTheme.colors
    StepCard(3, "Choose a fallback password", state.passwordStep) {
        Text(
            "Your last resort: it can force-end a session if the PIN doesn't work. It's never sent to Telegram, so keep it somewhere safe.",
            color = colors.inkSoft,
            style = MaterialTheme.typography.bodyLarge,
        )
        if (state.fallbackSet) {
            LearnmateAlert("Fallback password is set. You can change it in Settings.", AlertTone.Ok)
        } else {
            val first = passwordError(state.password, state.passwordAgain)
            val again = againError(state.password, state.passwordAgain)
            val fields: @Composable (Modifier) -> Unit = {
                PasswordField(
                    state.password,
                    onPassword,
                    "Fallback password",
                    it,
                    isError = first != null,
                    supporting = first ?: "At least 8 characters",
                    enabled = !state.busy,
                )
                PasswordField(
                    state.passwordAgain,
                    onPasswordAgain,
                    "Type it again",
                    it,
                    isError = again != null,
                    supporting = again,
                    enabled = !state.busy,
                )
            }
            if (compact) {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) { fields(Modifier) }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) { fields(Modifier.weight(1f)) }
            }
        }
    }
}

@Composable
private fun LockedPanel(
    state: FirstRunUiState,
    onFinish: () -> Unit,
) {
    val colors = LearnmateTheme.colors
    LearnmateCard(Modifier.fillMaxWidth()) {
        Text("How sessions are locked", color = colors.ink, style = MaterialTheme.typography.titleLarge)
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            LockRules.forEach { (icon, text) ->
                Row(
                    Modifier.fillMaxWidth().border(1.dp, colors.line, LearnmateShapes.button).padding(horizontal = 14.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(icon, Modifier.clearAndSetSemantics {})
                    Text(text, color = colors.ink, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
        state.error?.let { LearnmateAlert(it, AlertTone.Error) }
        PrimaryButton("Finish setup", onFinish, Modifier.fillMaxWidth(), enabled = state.canFinish)
        Text(
            "Finish setup unlocks once Telegram is connected and the fallback password is set.",
            color = colors.inkSoft,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
fun FirstRunRoute(
    container: AppContainer,
    onDone: () -> Unit,
    onSettings: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val controller = remember { FirstRunController(container.familyRepository, scope) }
    LaunchedEffect(controller) { controller.load() }
    val state by controller.state.collectAsState()
    val appearance by container.appearanceRepository.appearance.collectAsState(initial = null)
    val systemDark = isSystemInDarkTheme()
    FirstRunScreen(
        state = state,
        dark = appearance?.isDark(systemDark) ?: systemDark,
        onDarkChange = { scope.launch { container.appearanceRepository.setAppearance(if (it) Appearance.Dark else Appearance.Light) } },
        onSettings = onSettings,
        onName = controller::setName,
        onGrade = controller::setGrade,
        onGetCode = controller::getLinkCode,
        onPassword = controller::setPassword,
        onPasswordAgain = controller::setPasswordAgain,
        onFinish = { controller.finish(onDone) },
        onRetryLoad = controller::load,
    )
}
