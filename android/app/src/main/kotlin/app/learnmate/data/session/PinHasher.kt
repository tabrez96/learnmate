package app.learnmate.data.session

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/** Salted PBKDF2 hash of the session PIN, so the PIN can be checked offline without being stored. */
object PinHasher {
    private const val ITERATIONS = 100_000
    private const val KEY_BITS = 256
    private const val SALT_BYTES = 16

    fun randomSalt(): ByteArray = ByteArray(SALT_BYTES).also { SecureRandom().nextBytes(it) }

    fun hash(
        pin: String,
        salt: ByteArray = randomSalt(),
    ): String {
        val enc = Base64.getEncoder()
        return enc.encodeToString(salt) + ":" + enc.encodeToString(derive(pin, salt))
    }

    fun verify(
        pin: String,
        stored: String,
    ): Boolean {
        val parts = stored.split(":")
        if (parts.size != 2) return false
        return try {
            val dec = Base64.getDecoder()
            MessageDigest.isEqual(derive(pin, dec.decode(parts[0])), dec.decode(parts[1]))
        } catch (_: IllegalArgumentException) {
            false
        }
    }

    private fun derive(
        pin: String,
        salt: ByteArray,
    ): ByteArray =
        SecretKeyFactory
            .getInstance("PBKDF2WithHmacSHA256")
            .generateSecret(PBEKeySpec(pin.toCharArray(), salt, ITERATIONS, KEY_BITS))
            .encoded
}
