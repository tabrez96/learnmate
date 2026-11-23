package app.learnmate.data.exams

import app.learnmate.data.api.ExamDto
import app.learnmate.data.api.ExamPatchDto
import app.learnmate.data.api.ExamRequestDto
import app.learnmate.data.api.LearnmateApi
import app.learnmate.data.api.apiCall
import java.time.LocalDate

class ExamRepository(
    private val api: LearnmateApi,
) {
    suspend fun list(subjectId: Long? = null): List<ExamDto> = apiCall { api.exams(subjectId) }

    suspend fun create(
        subjectId: Long,
        date: LocalDate,
    ): ExamDto = apiCall { api.createExam(ExamRequestDto(subjectId, date.toString())) }

    suspend fun update(
        id: Long,
        subjectId: Long? = null,
        date: LocalDate? = null,
    ): ExamDto = apiCall { api.patchExam(id, ExamPatchDto(subjectId, date?.toString())) }

    suspend fun delete(id: Long) = apiCall { api.deleteExam(id) }
}
