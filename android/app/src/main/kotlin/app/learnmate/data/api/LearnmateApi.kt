package app.learnmate.data.api

import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.HTTP
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface LearnmateApi {
    @POST("sessions")
    suspend fun createSession(
        @Body body: SessionRequestDto,
    ): SessionWithPinDto

    @GET("sessions/current")
    suspend fun currentSession(): SessionDto

    @POST("sessions/{id}/pin")
    suspend fun replacePin(
        @Path("id") id: Long,
    ): SessionWithPinDto

    @POST("sessions/{id}/start")
    suspend fun startSession(
        @Path("id") id: Long,
    ): SessionDto

    @POST("sessions/{id}/end")
    suspend fun endSession(
        @Path("id") id: Long,
        @Body body: EndRequestDto,
    ): EndDto

    @POST("sessions/{id}/pin/resend")
    suspend fun resendPin(
        @Path("id") id: Long,
    ): ResendDto

    @POST("sessions/{id}/force-end")
    suspend fun forceEnd(
        @Path("id") id: Long,
        @Body body: ForceEndRequestDto,
    ): EndDto

    @POST("sessions/{id}/events")
    suspend fun postEvent(
        @Path("id") id: Long,
        @Body body: EventRequestDto,
    ): EventDto

    @POST("sessions/{id}/heartbeat")
    suspend fun heartbeat(
        @Path("id") id: Long,
    ): HeartbeatDto

    @GET("sessions/{id}/plan")
    suspend fun plan(
        @Path("id") sessionId: Long,
    ): PlanDto

    @PATCH("sessions/{id}/plan/steps/{key}")
    suspend fun patchPlanStep(
        @Path("id") sessionId: Long,
        @Path("key") key: String,
        @Body body: StepPatchDto,
    ): PlanDto

    @GET("progress")
    suspend fun progress(): ProgressDto

    @POST("sessions/{id}/mentor/lesson")
    suspend fun startLesson(
        @Path("id") sessionId: Long,
    ): LessonDto

    @POST("sessions/{id}/mentor/lesson/steps/{index}/answer")
    suspend fun answerLessonCheck(
        @Path("id") sessionId: Long,
        @Path("index") index: Int,
        @Body body: AnswerRequestDto,
    ): CheckResultDto

    @GET("sessions/{id}/mentor/messages")
    suspend fun mentorMessages(
        @Path("id") sessionId: Long,
    ): List<MessageDto>

    @POST("sessions/{id}/mentor/messages")
    suspend fun postMentorMessage(
        @Path("id") sessionId: Long,
        @Body body: MessageRequestDto,
    ): PostMessageDto

    @POST("sessions/{id}/tests")
    suspend fun createTest(
        @Path("id") sessionId: Long,
    ): TestDto

    @GET("tests/{id}")
    suspend fun test(
        @Path("id") testId: Long,
    ): TestDto

    @POST("tests/{id}/answers")
    suspend fun answerTest(
        @Path("id") testId: Long,
        @Body body: TestAnswerRequestDto,
    ): TestAnswerDto

    @POST("sessions/{id}/challenges")
    suspend fun createChallenge(
        @Path("id") sessionId: Long,
        @Body body: ChallengeRequestDto,
    ): TestDto

    @GET("budget")
    suspend fun budget(): BudgetDto

    @GET("family")
    suspend fun family(): FamilyDto

    @PUT("family")
    suspend fun putFamily(
        @Body body: FamilyRequestDto,
    ): FamilyDto

    @PUT("family/fallback")
    suspend fun putFallback(
        @Body body: FallbackRequestDto,
    )

    @POST("family/telegram-code")
    suspend fun telegramCode(): TelegramCodeDto

    @GET("subjects")
    suspend fun subjects(): List<SubjectDto>

    @POST("subjects")
    suspend fun createSubject(
        @Body body: SubjectRequestDto,
    ): SubjectDto

    @PATCH("subjects/{id}")
    suspend fun patchSubject(
        @Path("id") id: Long,
        @Body body: SubjectPatchDto,
    ): SubjectDto

    @DELETE("subjects/{id}")
    suspend fun deleteSubject(
        @Path("id") id: Long,
    )

    @Multipart
    @POST("subjects/{id}/materials")
    suspend fun uploadMaterial(
        @Path("id") subjectId: Long,
        @Part files: List<MultipartBody.Part>,
        @Part("title") title: RequestBody?,
        @Part("chapters") chapters: RequestBody?,
    ): MaterialDto

    @POST("subjects/{id}/materials/classroom")
    suspend fun addClassroomMaterial(
        @Path("id") subjectId: Long,
        @Body body: ClassroomRequestDto,
    ): MaterialDto

    @GET("subjects/{id}/materials")
    suspend fun materials(
        @Path("id") subjectId: Long,
    ): List<MaterialDto>

    @GET("materials/{id}")
    suspend fun material(
        @Path("id") id: Long,
    ): MaterialDto

    @DELETE("materials/{id}")
    suspend fun deleteMaterial(
        @Path("id") id: Long,
    )

    @GET("figures/{id}")
    suspend fun figure(
        @Path("id") id: Long,
    ): ResponseBody

    @GET("exams")
    suspend fun exams(
        @Query("subject_id") subjectId: Long?,
    ): List<ExamDto>

    @POST("exams")
    suspend fun createExam(
        @Body body: ExamRequestDto,
    ): ExamDto

    @PATCH("exams/{id}")
    suspend fun patchExam(
        @Path("id") id: Long,
        @Body body: ExamPatchDto,
    ): ExamDto

    @DELETE("exams/{id}")
    suspend fun deleteExam(
        @Path("id") id: Long,
    )

    // Retrofit's @DELETE can't carry a body.
    @HTTP(method = "DELETE", path = "data", hasBody = true)
    suspend fun deleteData(
        @Body body: DeleteDataRequestDto,
    )
}
