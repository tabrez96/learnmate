package app.learnmate.data.session

import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class PinHasherTest {
    @Test
    fun `right pin verifies and wrong pin fails`() {
        val stored = PinHasher.hash("4821")
        assertTrue(PinHasher.verify("4821", stored))
        assertFalse(PinHasher.verify("4822", stored))
    }

    @Test
    fun `salt makes two hashes differ`() = assertNotEquals(PinHasher.hash("4821"), PinHasher.hash("4821"))

    @Test
    fun `hash does not contain the pin`() = assertFalse(PinHasher.hash("4821").contains("4821"))

    @Test
    fun `malformed stored value is rejected`() {
        assertFalse(PinHasher.verify("4821", "nope"))
        assertFalse(PinHasher.verify("4821", "a:b:c"))
        assertFalse(PinHasher.verify("4821", "!!!:???"))
    }
}
