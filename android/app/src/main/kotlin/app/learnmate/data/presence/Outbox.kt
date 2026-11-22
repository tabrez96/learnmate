package app.learnmate.data.presence

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ListenableWorker
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerFactory
import androidx.work.WorkerParameters
import app.learnmate.data.api.ApiError
import app.learnmate.data.api.EventRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.apiCall
import app.learnmate.data.db.OutboxDao
import java.util.concurrent.TimeUnit

const val OUTBOX_WORK_NAME = "event-outbox"

class OutboxSender(
    private val api: LearnmateApi,
    private val dao: OutboxDao,
) {
    /** Returns true when the outbox is empty, false when delivery must be retried later. */
    suspend fun sendAll(): Boolean {
        while (true) {
            val batch = dao.pending()
            if (batch.isEmpty()) return true
            for (e in batch) {
                try {
                    apiCall { api.postEvent(e.sessionId, EventRequestDto(e.type, e.at, null)) }
                    dao.delete(e.id)
                } catch (err: ApiError) {
                    if (!err.isRetryable()) {
                        // The session is gone or over: nothing to retry.
                        dao.delete(e.id)
                    } else {
                        // Stop here so a later event never overtakes this one.
                        dao.bumpAttempts(e.id)
                        return false
                    }
                }
            }
        }
    }

    private fun ApiError.isRetryable() =
        when (this) {
            is ApiError.Network, ApiError.Unauthorized, is ApiError.TooSoon -> true
            is ApiError.Server -> code >= 500
            else -> false
        }
}

class OutboxWorker(
    ctx: Context,
    params: WorkerParameters,
    private val sender: OutboxSender,
) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = if (sender.sendAll()) Result.success() else Result.retry()
}

fun interface OutboxScheduler {
    fun schedule()
}

class WorkManagerOutboxScheduler(
    private val workManager: () -> WorkManager,
) : OutboxScheduler {
    override fun schedule() {
        val request =
            OneTimeWorkRequestBuilder<OutboxWorker>()
                .setConstraints(Constraints(requiredNetworkType = NetworkType.CONNECTED))
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build()
        workManager().enqueueUniqueWork(OUTBOX_WORK_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
    }
}

class LearnmateWorkerFactory(
    private val sender: () -> OutboxSender,
) : WorkerFactory() {
    override fun createWorker(
        appContext: Context,
        workerClassName: String,
        workerParameters: WorkerParameters,
    ): ListenableWorker? =
        if (workerClassName == OutboxWorker::class.java.name) {
            OutboxWorker(appContext, workerParameters, sender())
        } else {
            null
        }
}
