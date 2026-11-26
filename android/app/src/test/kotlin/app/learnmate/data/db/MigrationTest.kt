package app.learnmate.data.db

import androidx.room.testing.MigrationTestHelper
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class MigrationTest {
    @get:Rule
    val helper = MigrationTestHelper(InstrumentationRegistry.getInstrumentation(), LearnmateDatabase::class.java)

    @Test
    fun `migrate 2 to 3 keeps rows`() {
        helper.createDatabase("migration-test", 2).apply {
            execSQL("INSERT INTO event_outbox (id, sessionId, type, at, attempts) VALUES (1, 7, 'left', 't0', 2)")
            close()
        }
        val db = helper.runMigrationsAndValidate("migration-test", 3, true)
        db.query("SELECT type, attempts, secret FROM event_outbox").use { c ->
            assertEquals(true, c.moveToFirst())
            assertEquals("left", c.getString(0))
            assertEquals(2, c.getInt(1))
            assertNull(c.getString(2))
        }
    }
}
