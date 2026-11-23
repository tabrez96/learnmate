package app.learnmate.data.materials

import app.learnmate.data.api.ClassroomRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.MaterialDto
import app.learnmate.data.api.apiCall
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

/**
 * One file picked for upload. The caller holds all the bytes in memory, so the upload screen must stream large
 * files instead of using this class as it is.
 */
class UploadFile(
    val name: String,
    val mimeType: String,
    val bytes: ByteArray,
)

class MaterialRepository(
    private val api: LearnmateApi,
) {
    suspend fun upload(
        subjectId: Long,
        files: List<UploadFile>,
        title: String? = null,
        chapters: String? = null,
    ): MaterialDto {
        val parts =
            files.map {
                MultipartBody.Part.createFormData("files", it.name, it.bytes.toRequestBody(it.mimeType.toMediaType()))
            }

        fun text(value: String?) = value?.takeIf { it.isNotBlank() }?.toRequestBody("text/plain".toMediaType())
        return apiCall { api.uploadMaterial(subjectId, parts, text(title), text(chapters)) }
    }

    /** The access token is sent once and never logged or stored. */
    suspend fun addFromClassroom(
        subjectId: Long,
        link: String,
        accessToken: String,
        title: String? = null,
        chapters: String? = null,
    ): MaterialDto = apiCall { api.addClassroomMaterial(subjectId, ClassroomRequestDto(link, accessToken, title, chapters)) }

    suspend fun list(subjectId: Long): List<MaterialDto> = apiCall { api.materials(subjectId) }

    suspend fun get(id: Long): MaterialDto = apiCall { api.material(id) }

    suspend fun delete(id: Long) = apiCall { api.deleteMaterial(id) }

    suspend fun figure(id: Long): ByteArray = apiCall { api.figure(id).use { it.bytes() } }
}
