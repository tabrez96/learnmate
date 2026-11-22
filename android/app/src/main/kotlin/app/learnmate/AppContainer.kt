package app.learnmate

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import androidx.work.WorkManager
import app.learnmate.data.api.createLearnmateApi
import app.learnmate.data.budget.BudgetRepository
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.presence.LearnmateWorkerFactory
import app.learnmate.data.presence.OutboxSender
import app.learnmate.data.presence.PresenceRepository
import app.learnmate.data.presence.WorkManagerOutboxScheduler
import app.learnmate.data.session.SessionRepository
import app.learnmate.data.settings.AppearanceRepository

private val Context.settingsDataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

/** Builds the app's long-lived objects once; screens receive them through constructors. */
class AppContainer(
    context: Context,
) {
    private val appContext = context.applicationContext

    val appearanceRepository = AppearanceRepository(appContext.settingsDataStore)

    // Lazy so UI tests never open the database or touch WorkManager.
    val api by lazy { createLearnmateApi(BuildConfig.SERVER_URL, BuildConfig.DEVICE_TOKEN) }
    val database by lazy { LearnmateDatabase.build(appContext) }
    val outboxSender by lazy { OutboxSender(api, database.outboxDao()) }
    val workerFactory by lazy { LearnmateWorkerFactory { outboxSender } }
    val outboxScheduler by lazy { WorkManagerOutboxScheduler { WorkManager.getInstance(appContext) } }
    val sessionRepository by lazy { SessionRepository(api, database.sessionDao()) }
    val presenceRepository by lazy {
        PresenceRepository(api, database.outboxDao(), database.sessionDao(), outboxScheduler)
    }
    val budgetRepository by lazy { BudgetRepository(api) }
}
