package app.learnmate.data.settings

enum class Appearance(
    val storedValue: String,
) {
    Light("light"),
    Dark("dark"),
    MatchDevice("match_device"),
    ;

    /** True when the app should draw in dark mode. */
    fun isDark(deviceIsDark: Boolean): Boolean =
        when (this) {
            Light -> false
            Dark -> true
            MatchDevice -> deviceIsDark
        }

    companion object {
        /** Unknown or missing values fall back to the default, Match device. */
        fun fromStored(value: String?): Appearance = entries.firstOrNull { it.storedValue == value } ?: MatchDevice
    }
}
