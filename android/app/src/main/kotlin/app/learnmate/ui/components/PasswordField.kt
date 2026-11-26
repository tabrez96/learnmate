package app.learnmate.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextFieldColors
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import app.learnmate.ui.theme.LearnmateShapes
import app.learnmate.ui.theme.LearnmateTheme

/** Password input with a Show/Hide text button. */
@Composable
fun PasswordField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    isError: Boolean = false,
    supporting: String? = null,
    enabled: Boolean = true,
) {
    val colors = LearnmateTheme.colors
    var visible by rememberSaveable { mutableStateOf(false) }
    OutlinedTextField(
        value,
        onValueChange,
        modifier.fillMaxWidth(),
        label = { Text(label) },
        singleLine = true,
        enabled = enabled,
        isError = isError,
        shape = LearnmateShapes.input,
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, autoCorrectEnabled = false),
        trailingIcon = {
            TextButton(
                onClick = { visible = !visible },
                modifier = Modifier.semantics { contentDescription = if (visible) "Hide password" else "Show password" },
            ) { Text(if (visible) "Hide" else "Show", color = colors.blueText) }
        },
        supportingText = supporting?.let { { Text(it) } },
        colors = learnmateFieldColors(),
    )
}

@Composable
fun learnmateFieldColors(): TextFieldColors {
    val colors = LearnmateTheme.colors
    return OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.blue,
        unfocusedBorderColor = colors.line,
        focusedContainerColor = colors.card,
        unfocusedContainerColor = colors.card,
        errorBorderColor = colors.red,
        focusedTextColor = colors.ink,
        unfocusedTextColor = colors.ink,
        focusedLabelColor = colors.blue,
        unfocusedLabelColor = colors.inkSoft,
    )
}
