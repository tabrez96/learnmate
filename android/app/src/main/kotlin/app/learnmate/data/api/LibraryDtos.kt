package app.learnmate.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GradeDto(
    /** "done" or "missed" */
    val status: String,
    @SerialName("score_pct") val scorePct: Int? = null,
    val band: String? = null,
    val at: String,
)

@Serializable
data class SubjectDto(
    val id: Long,
    val name: String,
    val icon: String,
    @SerialName("material_count") val materialCount: Int,
    @SerialName("latest_grade") val latestGrade: GradeDto? = null,
    @SerialName("average_pct") val averagePct: Int? = null,
)

@Serializable
data class SubjectRequestDto(
    val name: String,
    val icon: String? = null,
)

@Serializable
data class SubjectPatchDto(
    val name: String? = null,
    val icon: String? = null,
)

@Serializable
data class ChapterDto(
    val id: Long,
    val name: String,
    val position: Int,
)

@Serializable
data class MaterialDto(
    val id: Long,
    @SerialName("subject_id") val subjectId: Long,
    val title: String,
    /** "upload" or "classroom" */
    val kind: String,
    /** "reading", "ready" or "failed" */
    val status: String,
    val error: String? = null,
    @SerialName("pages_read") val pagesRead: Int = 0,
    @SerialName("pages_total") val pagesTotal: Int? = null,
    @SerialName("chapters_hint") val chaptersHint: String? = null,
    val chapters: List<ChapterDto> = emptyList(),
    @SerialName("file_types") val fileTypes: List<String> = emptyList(),
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class ClassroomRequestDto(
    val link: String,
    @SerialName("access_token") val accessToken: String,
    val title: String? = null,
    val chapters: String? = null,
)

@Serializable
data class ExamDto(
    val id: Long,
    @SerialName("subject_id") val subjectId: Long,
    @SerialName("subject_name") val subjectName: String,
    /** yyyy-MM-dd */
    val date: String,
)

@Serializable
data class ExamRequestDto(
    @SerialName("subject_id") val subjectId: Long,
    val date: String,
)

@Serializable
data class ExamPatchDto(
    @SerialName("subject_id") val subjectId: Long? = null,
    val date: String? = null,
)
