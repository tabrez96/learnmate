package app.learnmate.data.subjects

import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.SubjectDto
import app.learnmate.data.api.SubjectPatchDto
import app.learnmate.data.api.SubjectRequestDto
import app.learnmate.data.api.apiCall

class SubjectRepository(
    private val api: LearnmateApi,
) {
    suspend fun list(): List<SubjectDto> = apiCall { api.subjects() }

    suspend fun create(
        name: String,
        icon: String? = null,
    ): SubjectDto = apiCall { api.createSubject(SubjectRequestDto(name, icon)) }

    suspend fun update(
        id: Long,
        name: String? = null,
        icon: String? = null,
    ): SubjectDto = apiCall { api.patchSubject(id, SubjectPatchDto(name, icon)) }

    suspend fun delete(id: Long) = apiCall { api.deleteSubject(id) }
}
