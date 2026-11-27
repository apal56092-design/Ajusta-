package com.ajusta.app

import com.ajusta.app.BuildConfig
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class ApiResult(val payload: JSONObject, val statusCode: Int)

class AjustaApiClient {
    private val baseUrl = BuildConfig.AJUSTA_API_BASE_URL.trimEnd('/')

    fun register(email: String, password: String): ApiResult =
        request("POST", "/v1/auth/register", body = JSONObject()
            .put("email", email).put("password", password))

    fun login(email: String, password: String): ApiResult =
        request("POST", "/v1/auth/login", body = JSONObject()
            .put("email", email).put("password", password))

    fun currentUser(token: String): ApiResult = request("GET", "/v1/auth/me", token = token)

    fun logout(token: String): ApiResult =
        request("POST", "/v1/auth/logout", token = token, body = JSONObject())

    fun submitTask(token: String, taskId: String, instruction: String): ApiResult =
        request("POST", "/v1/tasks", token = token, body = JSONObject()
            .put("task_id", taskId).put("instruction", instruction))

    private fun request(
        method: String,
        path: String,
        token: String? = null,
        body: JSONObject? = null
    ): ApiResult {
        require(baseUrl.startsWith("https://")) { "AJUSTA API must use HTTPS." }
        val connection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 30_000
            setRequestProperty("Accept", "application/json")
            token?.let { setRequestProperty("Authorization", "Bearer $it") }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        return try {
            if (body != null) {
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            val json = if (text.isBlank()) JSONObject() else JSONObject(text)
            ApiResult(json, code)
        } finally {
            connection.disconnect()
        }
    }
}
