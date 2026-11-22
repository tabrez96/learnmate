package app.learnmate.data.api

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

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

    @GET("budget")
    suspend fun budget(): BudgetDto
}
