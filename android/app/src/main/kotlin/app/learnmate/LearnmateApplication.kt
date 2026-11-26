package app.learnmate

import android.app.Application
import androidx.work.Configuration
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class LearnmateApplication :
    Application(),
    Configuration.Provider {
    lateinit var container: AppContainer
        private set

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder().setWorkerFactory(container.workerFactory).build()

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        // Rows left by a killed process (e.g. an offline end) still get sent.
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch { container.presenceRepository.flushIfPending() }
    }
}
