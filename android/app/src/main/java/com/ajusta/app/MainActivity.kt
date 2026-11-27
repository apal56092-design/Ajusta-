package com.ajusta.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) { AjustaHome() }
            }
        }
    }
}

private data class ChatMessage(val text: String, val fromUser: Boolean)

private data class TaskHistoryItem(
    val taskId: String,
    val instruction: String,
    val status: String,
    val result: String?,
    val errorMessage: String?
)

private fun parseTaskHistory(payload: org.json.JSONObject): List<TaskHistoryItem> {
    val items = payload.optJSONArray("items") ?: return emptyList()
    return buildList {
        for (index in 0 until items.length()) {
            val item = items.optJSONObject(index) ?: continue
            add(TaskHistoryItem(
                taskId = item.optString("task_id"),
                instruction = item.optString("instruction", "AJUSTA task"),
                status = item.optString("status", "unknown"),
                result = item.optString("result").takeIf { it.isNotBlank() && it != "null" },
                errorMessage = item.optString("error_message").takeIf { it.isNotBlank() && it != "null" }
            ))
        }
    }
}

@Composable
private fun AjustaHome() {
    val context = LocalContext.current
    val sessionStore = remember { SessionStore(context) }
    val api = remember { AjustaApiClient() }
    val scope = rememberCoroutineScope()
    val messages = remember { mutableStateListOf<ChatMessage>() }
    var taskHistory by remember { mutableStateOf<List<TaskHistoryItem>>(emptyList()) }
    var token by remember { mutableStateOf<String?>(null) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var taskDraft by remember { mutableStateOf("") }
    var activeTaskId by remember { mutableStateOf<String?>(null) }
    var isRegister by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("Sign in to connect to AJUSTA.") }

    LaunchedEffect(Unit) {
        val saved = sessionStore.read()
        if (saved != null) {
            try {
                val check = withContext(Dispatchers.IO) { api.currentUser(saved) }
                if (check.statusCode == 200) {
                    token = saved
                    status = "Connected as " + check.payload.optString("email")
                } else sessionStore.clear()
            } catch (_: Exception) {
                status = "Saved session could not be verified. Check API address and connection."
            }
        }
    }

    LaunchedEffect(token) {
        val activeToken = token ?: return@LaunchedEffect
        try {
            val response = withContext(Dispatchers.IO) { api.listTasks(activeToken) }
            if (response.statusCode == 200) taskHistory = parseTaskHistory(response.payload)
            else status = "Task history unavailable (" + response.statusCode + ")."
        } catch (error: Exception) {
            status = "Task history connection failed: " + (error.message ?: "unknown error")
        }
    }

    fun refreshTaskHistory(activeToken: String) {
        scope.launch {
            try {
                val response = withContext(Dispatchers.IO) { api.listTasks(activeToken) }
                if (response.statusCode == 200) {
                    taskHistory = parseTaskHistory(response.payload)
                } else {
                    status = "Task history unavailable (" + response.statusCode + ")."
                }
            } catch (error: Exception) {
                status = "Could not refresh history: " + (error.message ?: "unknown error")
            }
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("AJUSTA", style = MaterialTheme.typography.headlineLarge)
        Text("Unified AI workspace", style = MaterialTheme.typography.titleMedium)
        Text(status, style = MaterialTheme.typography.bodyMedium)

        if (token == null) {
            OutlinedTextField(
                value = email, onValueChange = { email = it },
                modifier = Modifier.fillMaxWidth(), label = { Text("Email") }, singleLine = true
            )
            OutlinedTextField(
                value = password, onValueChange = { password = it },
                modifier = Modifier.fillMaxWidth(), label = { Text("Password (12+ characters)") },
                singleLine = true
            )
            Button(
                enabled = !busy && email.isNotBlank() && password.length >= 12,
                onClick = {
                    busy = true
                    status = if (isRegister) "Creating account..." else "Signing in..."
                    scope.launch {
                        try {
                            if (isRegister) {
                                val registration = withContext(Dispatchers.IO) {
                                    api.register(email.trim(), password)
                                }
                                if (registration.statusCode != 201) {
                                    status = registration.payload.optString("detail", "Registration failed.")
                                } else {
                                    val signedIn = withContext(Dispatchers.IO) {
                                        api.login(email.trim(), password)
                                    }
                                    val error = acceptLogin(signedIn.statusCode, signedIn.payload, sessionStore) {
                                        token = it
                                        status = "Account created. Connected as " + email
                                    }
                                    if (error != null) status = error
                                }
                            } else {
                                val signedIn = withContext(Dispatchers.IO) {
                                    api.login(email.trim(), password)
                                }
                                val error = acceptLogin(signedIn.statusCode, signedIn.payload, sessionStore) {
                                    token = it
                                    status = "Connected as " + email
                                }
                                if (error != null) status = error
                            }
                        } catch (error: Exception) {
                            status = "Connection failed: " + (error.message ?: "check API configuration")
                        } finally { busy = false }
                    }
                }
            ) { Text(if (busy) "Please wait..." else if (isRegister) "Create account" else "Sign in") }
            Button(onClick = { isRegister = !isRegister }) {
                Text(if (isRegister) "Already have an account? Sign in" else "Create a new account")
            }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(enabled = !busy, onClick = {
                    val activeToken = token ?: return@Button
                    refreshTaskHistory(activeToken)
                }) { Text("Refresh history") }
                Button(enabled = !busy, onClick = {
                    val activeToken = token ?: return@Button
                    busy = true
                    scope.launch {
                        try { withContext(Dispatchers.IO) { api.logout(activeToken) } }
                        catch (_: Exception) { /* Always clear local credentials. */ }
                        sessionStore.clear()
                        token = null
                        taskHistory = emptyList()
                        status = "Signed out."
                        busy = false
                    }
                }) { Text("Sign out") }
                if (activeTaskId != null) {
                    Button(onClick = {
                        val activeToken = token ?: return@Button
                        val taskId = activeTaskId ?: return@Button
                        scope.launch {
                            try {
                                val cancelled = withContext(Dispatchers.IO) {
                                    api.cancelAsyncTask(activeToken, taskId)
                                }
                                status = if (cancelled.statusCode in 200..299) {
                                    "Cancellation requested for task " + taskId
                                } else {
                                    cancelled.payload.optString("detail", "Task could not be cancelled.")
                                }
                            } catch (error: Exception) {
                                status = "Cancel request failed: " + (error.message ?: "unknown error")
                            }
                        }
                    }) { Text("Cancel task") }
                }
            }
            LazyColumn(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                item { Text("Recent task history", style = MaterialTheme.typography.titleMedium) }
                items(taskHistory, key = { it.taskId }) { task ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(task.instruction, style = MaterialTheme.typography.titleSmall)
                            Text("Status: " + task.status, style = MaterialTheme.typography.labelMedium)
                            task.result?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
                            task.errorMessage?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
                            Text("Task ID: " + task.taskId, style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
                items(messages) { message ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (message.fromUser)
                                MaterialTheme.colorScheme.primaryContainer
                            else MaterialTheme.colorScheme.surfaceVariant
                        )
                    ) { Text(message.text, modifier = Modifier.padding(14.dp)) }
                }
            }
            OutlinedTextField(
                value = taskDraft, onValueChange = { taskDraft = it },
                modifier = Modifier.fillMaxWidth(), placeholder = { Text("AJUSTA ko task do...") },
                maxLines = 4
            )
            Button(enabled = !busy && taskDraft.isNotBlank(), onClick = {
                val activeToken = token ?: return@Button
                val instruction = taskDraft.trim()
                val taskId = "android-" + UUID.randomUUID().toString()
                messages.add(ChatMessage(instruction, true))
                taskDraft = ""
                busy = true
                status = "Task AJUSTA Brain ko bheja ja raha hai..."
                scope.launch {
                    activeTaskId = taskId
                    try {
                        val response = withContext(Dispatchers.IO) {
                            api.submitAsyncTask(activeToken, taskId, instruction)
                        }
                        if (response.statusCode !in 200..299) {
                            status = "Task request failed (" + response.statusCode + "): " +
                                response.payload.optString("detail", "API error")
                            activeTaskId = null
                        } else {
                            status = "Task queued. AJUSTA is processing it..."
                            var terminal = false
                            repeat(120) {
                                if (!terminal) {
                                    delay(1000)
                                    val live = withContext(Dispatchers.IO) {
                                        api.getAsyncTask(activeToken, taskId)
                                    }
                                    if (live.statusCode == 200) {
                                        val liveStatus = live.payload.optString("status", "queued")
                                        val progress = live.payload.optInt("progress_percent", 0)
                                        val progressMessage = live.payload.optString("progress_message", "")
                                        status = "AJUSTA task status: " + liveStatus + " (" +
                                            progress + "%) " + progressMessage
                                        if (liveStatus in setOf("succeeded", "failed", "needs_approval", "cancelled")) {
                                            terminal = true
                                            val resultText = live.payload.optString(
                                                "result",
                                                live.payload.optString("error_message", liveStatus)
                                            )
                                            messages.add(ChatMessage(resultText, false))
                                            status = "Task finished: " + liveStatus
                                            activeTaskId = null
                                        }
                                    } else if (live.statusCode == 404) {
                                        terminal = true
                                        activeTaskId = null
                                        status = "Task was not found on the server."
                                    } else {
                                        status = "Task status check returned " + live.statusCode
                                    }
                                }
                            }
                            if (!terminal) {
                                status = "Task is still running. You can refresh history or cancel it."
                            }
                        }
                        val historyResponse = withContext(Dispatchers.IO) { api.listTasks(activeToken) }
                        if (historyResponse.statusCode == 200) {
                            taskHistory = parseTaskHistory(historyResponse.payload)
                        }
                    } catch (error: Exception) {
                        status = "Task connection failed: " + (error.message ?: "unknown error")
                    } finally {
                        busy = false
                    }
                }
            }) { Text(if (busy) "Working..." else "Send task") }
        }
        Spacer(modifier = Modifier.height(2.dp))
        Text("API: " + BuildConfig.AJUSTA_API_BASE_URL, style = MaterialTheme.typography.labelSmall)
    }
}

private fun acceptLogin(
    statusCode: Int,
    payload: org.json.JSONObject,
    sessionStore: SessionStore,
    onSuccess: (String) -> Unit
): String? {
    if (statusCode !in 200..299 || !payload.has("access_token")) {
        return payload.optString("detail", "Authentication failed (" + statusCode + ").")
    }
    val token = payload.optString("access_token")
    if (token.isBlank()) return "The server returned an empty session token."
    sessionStore.save(token)
    onSuccess(token)
    return null
}
