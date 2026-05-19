package com.rodski.demo

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

data class LoginRequest(val username: String, val password: String)
data class LoginResponse(val success: Boolean, val status: Int, val message: String, val data: Map<String, String>?)
data class Order(val order_id: String, val customer: String, val amount: Double, val status: String)
data class OrdersResponse(val success: Boolean, val data: List<Order>)

interface ApiService {
    @POST("/api/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @GET("/api/orders")
    suspend fun getOrders(): Response<OrdersResponse>
}
