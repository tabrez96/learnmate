package app.learnmate.classroomcheck

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import app.learnmate.BuildConfig
import com.google.android.gms.auth.api.identity.AuthorizationRequest
import com.google.android.gms.auth.api.identity.AuthorizationResult
import com.google.android.gms.auth.api.identity.Identity
import com.google.android.gms.common.api.ApiException
import com.google.android.gms.common.api.CommonStatusCodes
import com.google.android.gms.common.api.Scope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ClassroomCheckActivity : ComponentActivity() {
    // Plain mutableStateOf on purpose: saved state can be written to disk, and the check must never persist a token.
    private var state by mutableStateOf(ClassroomCheckState(clientId = BuildConfig.GOOGLE_ANDROID_CLIENT_ID))
    private val runner = ClassroomCheckRunner(OkHttpGoogleHttp())

    private val consent =
        registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { res ->
            if (res.resultCode != RESULT_OK) {
                fail(
                    "Consent screen closed without granting (resultCode=${res.resultCode}). " +
                        "Copy any error text shown on the Google screen into the report.",
                )
            } else {
                try {
                    onAuthorized(Identity.getAuthorizationClient(this).getAuthorizationResultFromIntent(res.data))
                } catch (e: ApiException) {
                    fail(describeAuthError(e))
                }
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { ClassroomCheckScreen(state, ::startCheck) }
    }

    private fun startCheck() {
        state = state.copy(busy = true, lines = listOf("Requesting authorization..."))
        val request = AuthorizationRequest.builder().setRequestedScopes(REQUIRED_SCOPES.map { Scope(it) }).build()
        Identity
            .getAuthorizationClient(this)
            .authorize(request)
            .addOnSuccessListener { result ->
                val pending = result.pendingIntent
                if (result.hasResolution() && pending != null) {
                    consent.launch(IntentSenderRequest.Builder(pending.intentSender).build())
                } else {
                    onAuthorized(result)
                }
            }.addOnFailureListener { fail(describeAuthError(it)) }
    }

    private fun onAuthorized(result: AuthorizationResult) {
        val token = result.accessToken
        if (token == null) {
            fail("Authorized but no access token returned")
            return
        }
        val granted = result.grantedScopes
        lifecycleScope.launch {
            val lines = withContext(Dispatchers.IO) { runner.run(token, granted) }
            state = state.copy(busy = false, lines = state.lines + lines)
        }
    }

    private fun fail(line: String) {
        state = state.copy(busy = false, lines = state.lines + line + "RESULT: BLOCKED at sign-in")
    }
}

private fun describeAuthError(e: Exception): String =
    if (e is ApiException) {
        "Sign-in error ${e.statusCode} (${CommonStatusCodes.getStatusCodeString(e.statusCode)}): ${e.message}"
    } else {
        "Sign-in error ${e.javaClass.simpleName}: ${e.message}"
    }
