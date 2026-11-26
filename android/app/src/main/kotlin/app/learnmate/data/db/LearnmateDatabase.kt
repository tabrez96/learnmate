package app.learnmate.data.db

import android.content.Context
import androidx.room.AutoMigration
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "current_session")
data class CurrentSessionEntity(
    /** Server session id; at most one row. */
    @PrimaryKey val id: Long,
    val subjectId: Long?,
    val type: String,
    val questionCount: Int,
    val state: String,
    /** "salt:hash" in base64; null when the PIN was changed somewhere else. */
    val pinHash: String?,
    val pinVersion: Int,
    val startedAt: String?,
    /** Lesson step the child is on. */
    val stepIndex: Int = 0,
    /** Graded test in progress; null before the test starts. */
    val testId: Long? = null,
    /** Next test question. */
    val testQuestionIndex: Int = 0,
    val testCorrect: Int = 0,
    val updatedAtMs: Long,
)

@Entity(tableName = "event_outbox")
data class OutboxEventEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val sessionId: Long,
    val type: String,
    /** ISO instant when it happened. */
    val at: String,
    val attempts: Int = 0,
    /** The PIN or fallback password for an end queued offline; deleted once delivered. */
    val secret: String? = null,
)

@Dao
interface SessionDao {
    @Query("SELECT * FROM current_session LIMIT 1")
    fun observe(): Flow<CurrentSessionEntity?>

    @Query("SELECT * FROM current_session LIMIT 1")
    suspend fun get(): CurrentSessionEntity?

    @Upsert
    suspend fun upsert(entity: CurrentSessionEntity)

    /** Keeps the "at most one row" rule when the session id changes. */
    @Transaction
    suspend fun replaceCurrent(entity: CurrentSessionEntity) {
        clear()
        upsert(entity)
    }

    @Query("DELETE FROM current_session")
    suspend fun clear()

    @Query("UPDATE current_session SET state = :state, updatedAtMs = :updatedAtMs WHERE id = :id")
    suspend fun updateState(
        id: Long,
        state: String,
        updatedAtMs: Long,
    )

    @Query(
        "UPDATE current_session SET stepIndex = :stepIndex, testQuestionIndex = :testQuestionIndex, " +
            "testCorrect = :testCorrect, updatedAtMs = :updatedAtMs WHERE id = :id",
    )
    suspend fun updateProgress(
        id: Long,
        stepIndex: Int,
        testQuestionIndex: Int,
        testCorrect: Int,
        updatedAtMs: Long,
    )

    @Query(
        "UPDATE current_session SET testId = :testId, testQuestionIndex = :testQuestionIndex, " +
            "testCorrect = :testCorrect, updatedAtMs = :updatedAtMs WHERE id = :id AND " +
            "(testId IS NULL OR testId != :testId OR testQuestionIndex <= :testQuestionIndex)",
    )
    suspend fun updateTest(
        id: Long,
        testId: Long,
        testQuestionIndex: Int,
        testCorrect: Int,
        updatedAtMs: Long,
    )
}

@Dao
interface OutboxDao {
    @Insert
    suspend fun insert(event: OutboxEventEntity): Long

    @Query("SELECT * FROM event_outbox ORDER BY id LIMIT :limit")
    suspend fun pending(limit: Int = 50): List<OutboxEventEntity>

    @Query("DELETE FROM event_outbox WHERE id = :id")
    suspend fun delete(id: Long)

    @Query("UPDATE event_outbox SET attempts = attempts + 1 WHERE id = :id")
    suspend fun bumpAttempts(id: Long)

    @Query("SELECT COUNT(*) FROM event_outbox")
    suspend fun count(): Int
}

@Database(
    entities = [CurrentSessionEntity::class, OutboxEventEntity::class],
    version = 3,
    autoMigrations = [AutoMigration(from = 1, to = 2), AutoMigration(from = 2, to = 3)],
    exportSchema = true,
)
abstract class LearnmateDatabase : RoomDatabase() {
    abstract fun sessionDao(): SessionDao

    abstract fun outboxDao(): OutboxDao

    companion object {
        fun build(context: Context): LearnmateDatabase =
            Room.databaseBuilder(context, LearnmateDatabase::class.java, "learnmate.db").build()
    }
}
