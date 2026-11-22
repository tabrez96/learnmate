package app.learnmate

import android.app.Application
import androidx.work.Configuration

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
    }
}
