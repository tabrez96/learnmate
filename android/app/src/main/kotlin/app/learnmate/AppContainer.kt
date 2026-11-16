package app.learnmate

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import app.learnmate.data.settings.AppearanceRepository

private val Context.settingsDataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

/** Builds the app's long-lived objects once; screens receive them through constructors. */
class AppContainer(
    context: Context,
) {
    val appearanceRepository = AppearanceRepository(context.applicationContext.settingsDataStore)
}
