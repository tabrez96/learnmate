package app.learnmate.data.session

import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class SecretHasherTest {
    @Test
    fun `right pin verifies and wrong pin fails`() {
        val stored = SecretHasher.hash("4821")
        assertTrue(SecretHasher.verify("4821", stored))
        assertFalse(SecretHasher.verify("4822", stored))
    }

    @Test
    fun `salt makes two hashes differ`() = assertNotEquals(SecretHasher.hash("4821"), SecretHasher.hash("4821"))

    @Test
    fun `hash does not contain the pin`() = assertFalse(SecretHasher.hash("4821").contains("4821"))

    @Test
    fun `malformed stored value is rejected`() {
        assertFalse(SecretHasher.verify("4821", "nope"))
        assertFalse(SecretHasher.verify("4821", "a:b:c"))
        assertFalse(SecretHasher.verify("4821", "!!!:???"))
    }
}
