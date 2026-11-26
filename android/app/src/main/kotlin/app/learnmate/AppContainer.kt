package app.learnmate

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import androidx.work.WorkManager
import app.learnmate.data.api.createLearnmateApi
import app.learnmate.data.assess.AssessRepository
import app.learnmate.data.budget.BudgetRepository
import app.learnmate.data.db.LearnmateDatabase
import app.learnmate.data.exams.ExamRepository
import app.learnmate.data.family.FamilyRepository
import app.learnmate.data.materials.MaterialRepository
import app.learnmate.data.mentor.MentorRepository
import app.learnmate.data.plan.PlanRepository
import app.learnmate.data.presence.LearnmateWorkerFactory
import app.learnmate.data.presence.OutboxSender
import app.learnmate.data.presence.PresenceRepository
import app.learnmate.data.presence.WorkManagerOutboxScheduler
import app.learnmate.data.session.OfflineEndRepository
import app.learnmate.data.session.SessionRepository
import app.learnmate.data.settings.AppearanceRepository
import app.learnmate.data.settings.FallbackPasswordCache
import app.learnmate.data.subjects.SubjectRepository
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow

private val Context.settingsDataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

/** Builds the app's long-lived objects once; screens receive them through constructors. */
class AppContainer(
    context: Context,
) {
    private val appContext = context.applicationContext

    val appearanceRepository = AppearanceRepository(appContext.settingsDataStore)
    val fallbackPasswordCache = FallbackPasswordCache(appContext.settingsDataStore)

    /** A tick for every touch or key press; feeds the inactivity timer. */
    val userActivity = MutableSharedFlow<Unit>(extraBufferCapacity = 1, onBufferOverflow = BufferOverflow.DROP_OLDEST)

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
    val offlineEndRepository by lazy {
        OfflineEndRepository(database, fallbackPasswordCache, outboxScheduler)
    }
    val budgetRepository by lazy { BudgetRepository(api) }
    val familyRepository by lazy { FamilyRepository(api, fallbackPasswordCache) }
    val subjectRepository by lazy { SubjectRepository(api) }
    val materialRepository by lazy { MaterialRepository(api) }
    val examRepository by lazy { ExamRepository(api) }
    val planRepository by lazy { PlanRepository(api) }
    val mentorRepository by lazy { MentorRepository(api) }
    val assessRepository by lazy { AssessRepository(api, database.sessionDao()) }
}
