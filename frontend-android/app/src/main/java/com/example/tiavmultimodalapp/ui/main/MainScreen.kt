package com.example.tiavmultimodalapp.ui.main

import android.content.ClipboardManager
import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation3.runtime.NavKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

// -------------------------------------------------------------
// CONFIG CONSTANTS & MODEL CONTRACTS
// -------------------------------------------------------------
private const val API_BASE = "http://10.0.2.2:8000"

data class Message(
    val text: String,
    val isUser: Boolean,
    val isStreaming: Boolean = false,
    val isError: Boolean = false
)

// -------------------------------------------------------------
// PREMIUM DARK MODE COLOR SYSTEM
// -------------------------------------------------------------
private val Slate900 = Color(0xFF111827) // Deep canvas
private val Slate800 = Color(0xFF1F2937) // Surfaces / Cards
private val Slate700 = Color(0xFF374151) // AI Bubble
private val Slate600 = Color(0xFF4B5563) // Borders / Muted
private val Slate400 = Color(0xFF9CA3AF) // Secondary Text
private val Slate100 = Color(0xFFF3F4F6) // Pure white contrast

private val AccentText = Color(0xFF34D399)   // Mint / Emerald (#6EE7B7 equivalent)
private val AccentImage = Color(0xFF60A5FA)  // Sky / Blue (#93C5FD equivalent)
private val AccentAudio = Color(0xFFF472B6)  // Pink (#F9A8D4 equivalent)
private val AccentVideo = Color(0xFFFBBF24)  // Amber (#FCD34D equivalent)

enum class TiavTab(val id: String, val label: String, val color: Color) {
    TEXT("text", "Text", AccentText),
    IMAGE("image", "Image", AccentImage),
    AUDIO("audio", "Audio", AccentAudio),
    VIDEO("video", "Video", AccentVideo)
}

// Global OkHttpClient with generous timeouts to allow model reasoning delays
private val httpClient = OkHttpClient.Builder()
    .connectTimeout(20, TimeUnit.SECONDS)
    .readTimeout(300, TimeUnit.SECONDS)
    .writeTimeout(300, TimeUnit.SECONDS)
    .build()

// -------------------------------------------------------------
// MAIN ENTRYPOINT SCREENS
// -------------------------------------------------------------
@Composable
fun MainScreen(
    onItemClick: (NavKey) -> Unit,
    modifier: Modifier = Modifier
) {
    var activeTab by remember { mutableStateOf(TiavTab.TEXT) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Slate900)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
        ) {
            // Premium App Header
            AppHeader(activeTab)

            // Tab Bar Switcher
            TabBar(activeTab = activeTab, onTabSelected = { activeTab = it })

            Spacer(modifier = Modifier.height(12.dp))

            // Body Content Panel
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
            ) {
                when (activeTab) {
                    TiavTab.TEXT -> TextModalityPanel(activeTab.color)
                    TiavTab.IMAGE -> FileModalityPanel(TiavTab.IMAGE)
                    TiavTab.AUDIO -> FileModalityPanel(TiavTab.AUDIO)
                    TiavTab.VIDEO -> FileModalityPanel(TiavTab.VIDEO)
                }
            }
        }
    }
}

// -------------------------------------------------------------
// UI COMPONENTS: HEADER & TABS
// -------------------------------------------------------------
@Composable
fun AppHeader(selectedTab: TiavTab) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 16.dp, start = 20.dp, end = 20.dp, bottom = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Glowing Active Indicator Badge
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(100.dp))
                .background(Slate800)
                .border(1.dp, Slate700, RoundedCornerShape(100.dp))
                .padding(horizontal = 12.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(RoundedCornerShape(100.dp))
                    .background(selectedTab.color)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Multimodal AI Companion",
                color = Slate100,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold
            )
        }

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = "TIAV Studio",
            color = Slate100,
            fontSize = 28.sp,
            fontWeight = FontWeight.ExtraBold,
            fontFamily = FontFamily.SansSerif,
            letterSpacing = (-0.5).sp
        )

        Text(
            text = "Interact with AI through text, images, audio and video",
            color = Slate400,
            fontSize = 13.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 2.dp)
        )
    }
}

@Composable
fun TabBar(activeTab: TiavTab, onTabSelected: (TiavTab) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(Slate800)
            .padding(4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        TiavTab.values().forEach { tab ->
            val isSelected = activeTab == tab
            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(8.dp))
                    .background(if (isSelected) Slate700 else Color.Transparent)
                    .clickable { onTabSelected(tab) }
                    .padding(vertical = 10.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = tab.label,
                    color = if (isSelected) tab.color else Slate400,
                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                    fontSize = 14.sp
                )
            }
        }
    }
}

// -------------------------------------------------------------
// TEXT MODALITY PANEL (CHAT + REALTIME STREAMING)
// -------------------------------------------------------------
@Composable
fun TextModalityPanel(accentColor: Color) {
    val coroutineScope = rememberCoroutineScope()
    val messages = remember { mutableStateListOf<Message>() }
    var promptInput by remember { mutableStateOf("") }
    var isSending by remember { mutableStateOf(false) }

    val listState = rememberLazyListState()

    // Auto-scroll to bottom as messages flow in
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // Chat History Canvas
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Slate800)
                .border(1.dp, Slate700, RoundedCornerShape(16.dp))
        ) {
            if (messages.isEmpty()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Ask anything...",
                        color = Slate400,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Enter a prompt below to start a live conversation. The AI will stream responses token-by-token.",
                        color = Slate400,
                        fontSize = 13.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(top = 8.dp).padding(horizontal = 24.dp)
                    )
                }
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(messages) { message ->
                        ChatBubble(message, accentColor)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Chat Input Row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            val keyboardController = LocalSoftwareKeyboardController.current

            OutlinedTextField(
                value = promptInput,
                onValueChange = { promptInput = it },
                placeholder = { Text("Type your message...", color = Slate400) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Slate100,
                    unfocusedTextColor = Slate100,
                    focusedContainerColor = Slate800,
                    unfocusedContainerColor = Slate800,
                    focusedBorderColor = accentColor,
                    unfocusedBorderColor = Slate700
                ),
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(12.dp)),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = {
                    if (promptInput.trim().isNotEmpty() && !isSending) {
                        keyboardController?.hide()
                        val textToSend = promptInput.trim()
                        promptInput = ""
                        messages.add(Message(textToSend, isUser = true))
                        isSending = true

                        coroutineScope.launch {
                            executeTextStream(textToSend, messages)
                            isSending = false
                        }
                    }
                }),
                enabled = !isSending
            )

            Spacer(modifier = Modifier.width(8.dp))

            Button(
                onClick = {
                    if (promptInput.trim().isNotEmpty() && !isSending) {
                        keyboardController?.hide()
                        val textToSend = promptInput.trim()
                        promptInput = ""
                        messages.add(Message(textToSend, isUser = true))
                        isSending = true

                        coroutineScope.launch {
                            executeTextStream(textToSend, messages)
                            isSending = false
                        }
                    }
                },
                enabled = promptInput.trim().isNotEmpty() && !isSending,
                colors = ButtonDefaults.buttonColors(
                    containerColor = accentColor,
                    disabledContainerColor = Slate800
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .height(56.dp)
                    .width(60.dp),
                contentPadding = PaddingValues(0.dp)
            ) {
                if (isSending) {
                    CircularProgressIndicator(color = Slate900, modifier = Modifier.size(24.dp))
                } else {
                    Icon(
                        imageVector = Icons.Default.Send,
                        contentDescription = "Send",
                        tint = if (promptInput.trim().isNotEmpty()) Slate900 else Slate400
                    )
                }
            }
        }
    }
}

@Composable
fun ChatBubble(message: Message, accentColor: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (message.isUser) Arrangement.End else Arrangement.Start
    ) {
        Box(
            modifier = Modifier
                .clip(
                    RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (message.isUser) 16.dp else 2.dp,
                        bottomEnd = if (message.isUser) 2.dp else 16.dp
                    )
                )
                .background(if (message.isUser) Slate700 else Slate800)
                .border(
                    width = 1.dp,
                    color = if (message.isError) Color.Red else if (message.isUser) Slate600 else Slate700,
                    shape = RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (message.isUser) 16.dp else 2.dp,
                        bottomEnd = if (message.isUser) 2.dp else 16.dp
                    )
                )
                .padding(horizontal = 14.dp, vertical = 10.dp)
                .widthIn(max = 280.dp)
        ) {
            Column {
                // Header badge inside bubble
                Text(
                    text = if (message.isUser) "You" else "AI",
                    color = if (message.isUser) accentColor else Slate400,
                    fontWeight = FontWeight.Bold,
                    fontSize = 11.sp,
                    modifier = Modifier.padding(bottom = 2.dp)
                )
                
                Text(
                    text = message.text.ifEmpty { if (message.isStreaming) "Thinking..." else "" },
                    color = if (message.isError) Color.Red else Slate100,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                    fontStyle = if (message.text.isEmpty() && message.isStreaming) FontStyle.Italic else FontStyle.Normal
                )
            }
        }
    }
}

// -------------------------------------------------------------
// TEXT STREAMING NETWORKING LOGIC
// -------------------------------------------------------------
private suspend fun executeTextStream(promptText: String, messages: MutableList<Message>) {
    // Append the initial empty AI streaming container
    withContext(Dispatchers.Main) {
        messages.add(Message("", isUser = false, isStreaming = true))
    }

    val request = Request.Builder()
        .url("$API_BASE/text")
        .post(
            MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("prompt", promptText)
                .build()
        )
        .build()

    try {
        withContext(Dispatchers.IO) {
            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errMsg = "HTTP error code: ${response.code}"
                    withContext(Dispatchers.Main) {
                        val lastIdx = messages.size - 1
                        messages[lastIdx] = Message(errMsg, isUser = false, isStreaming = false, isError = true)
                    }
                    return@use
                }

                val source = response.body?.source()
                if (source == null) {
                    withContext(Dispatchers.Main) {
                        val lastIdx = messages.size - 1
                        messages[lastIdx] = Message("Null response stream received", isUser = false, isStreaming = false, isError = true)
                    }
                    return@use
                }

                var fullText = ""
                val buffer = ByteArray(1024)
                var bytesRead: Int

                while (true) {
                    bytesRead = source.read(buffer)
                    if (bytesRead == -1) break

                    val chunk = String(buffer, 0, bytesRead, Charsets.UTF_8)
                    if (chunk.isNotEmpty()) {
                        fullText += chunk
                        val textToEmit = fullText
                        withContext(Dispatchers.Main) {
                            val lastIdx = messages.size - 1
                            messages[lastIdx] = Message(textToEmit, isUser = false, isStreaming = true)
                        }
                    }
                }

                // Finish stream cleanly
                withContext(Dispatchers.Main) {
                    val lastIdx = messages.size - 1
                    messages[lastIdx] = Message(fullText, isUser = false, isStreaming = false)
                }
            }
        }
    } catch (e: Exception) {
        withContext(Dispatchers.Main) {
            val lastIdx = messages.size - 1
            messages[lastIdx] = Message(
                "Network failure: ${e.localizedMessage ?: "timeout or connection refused"}",
                isUser = false,
                isStreaming = false,
                isError = true
            )
        }
    }
}

// -------------------------------------------------------------
// MULTIMODAL FILE MODAL PANEL (IMAGE/AUDIO/VIDEO)
// -------------------------------------------------------------
@Composable
fun FileModalityPanel(tab: TiavTab) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var selectedUri by remember { mutableStateOf<Uri?>(null) }
    var fileName by remember { mutableStateOf("") }
    var fileSize by remember { mutableStateOf("") }

    var isUploading by remember { mutableStateOf(false) }
    var responseOutput by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf("") }

    // Re-initialize picker state when active tab switches
    LaunchedEffect(tab) {
        selectedUri = null
        fileName = ""
        fileSize = ""
        responseOutput = ""
        errorMessage = ""
        isUploading = false
    }

    // Dynamic label naming mapping
    val mimeTypeFilter = when (tab) {
        TiavTab.IMAGE -> "image/*"
        TiavTab.AUDIO -> "audio/*"
        TiavTab.VIDEO -> "video/*"
        else -> "*/*"
    }

    val actionLabel = when (tab) {
        TiavTab.IMAGE -> "Analyze Image"
        TiavTab.AUDIO -> "Transcribe Audio"
        TiavTab.VIDEO -> "Analyze Video"
        else -> "Analyze File"
    }

    val fileLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            selectedUri = uri
            fileName = getFileName(context, uri)
            fileSize = getFileSizeString(context, uri)
            responseOutput = ""
            errorMessage = ""
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(bottom = 16.dp)
    ) {
        // Large DropZone / Picker Box
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(200.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(Slate800)
                .border(
                    width = 1.dp,
                    color = if (selectedUri != null) tab.color else Slate700,
                    shape = RoundedCornerShape(16.dp)
                )
                .clickable(enabled = !isUploading) { fileLauncher.launch(mimeTypeFilter) },
            contentAlignment = Alignment.Center
        ) {
            if (selectedUri != null) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(16.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.CheckCircle,
                        contentDescription = "Selected",
                        tint = tab.color,
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = fileName,
                        color = Slate100,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center
                    )
                    Text(
                        text = "$fileSize — Click to change",
                        color = Slate400,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(top = 2.dp)
                    )
                }
            } else {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(16.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Share, // Upload indicator
                        contentDescription = "Browse",
                        tint = tab.color,
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Drop your ${tab.label.lowercase()} here",
                        color = Slate100,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "or click to browse local files",
                        color = tab.color,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Upload Button
        Button(
            onClick = {
                val uri = selectedUri
                if (uri != null && !isUploading) {
                    isUploading = true
                    responseOutput = ""
                    errorMessage = ""
                    coroutineScope.launch {
                        executeFileUpload(context, uri, fileName, tab.id, onResult = { text ->
                            responseOutput = text
                        }, onError = { err ->
                            errorMessage = err
                        })
                        isUploading = false
                    }
                }
            },
            enabled = selectedUri != null && !isUploading,
            colors = ButtonDefaults.buttonColors(
                containerColor = tab.color,
                disabledContainerColor = Slate800
            ),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
        ) {
            if (isUploading) {
                CircularProgressIndicator(color = Slate900, modifier = Modifier.size(24.dp))
            } else {
                Text(
                    text = actionLabel,
                    color = if (selectedUri != null) Slate900 else Slate400,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Display Server Response Box
        if (errorMessage.isNotEmpty() || responseOutput.isNotEmpty() || isUploading) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .clip(RoundedCornerShape(16.dp))
                    .background(Slate800)
                    .border(1.dp, Slate700, RoundedCornerShape(16.dp))
                    .padding(16.dp)
            ) {
                Column(modifier = Modifier.fillMaxSize()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Response Output",
                            color = tab.color,
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                        if (responseOutput.isNotEmpty()) {
                            Text(
                                text = "Copy",
                                color = Slate400,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier
                                    .clickable {
                                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                        val clip = android.content.ClipData.newPlainText("Response", responseOutput)
                                        clipboard.setPrimaryClip(clip)
                                    }
                                    .border(1.dp, Slate700, RoundedCornerShape(4.dp))
                                    .padding(horizontal = 8.dp, vertical = 2.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    if (isUploading && responseOutput.isEmpty()) {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(color = tab.color)
                        }
                    } else if (errorMessage.isNotEmpty()) {
                        Text(
                            text = errorMessage,
                            color = Color.Red,
                            fontSize = 14.sp
                        )
                    } else {
                        LazyColumn(modifier = Modifier.fillMaxSize()) {
                            item {
                                Text(
                                    text = responseOutput,
                                    color = Slate100,
                                    fontSize = 14.sp,
                                    lineHeight = 20.sp
                                )
                            }
                        }
                    }
                }
            }
        } else {
            // Buffer space filler to balance heights
            Spacer(modifier = Modifier.weight(1f))
        }
    }
}

// -------------------------------------------------------------
// FILE UPLOAD NETWORKING LOGIC
// -------------------------------------------------------------
private suspend fun executeFileUpload(
    context: Context,
    uri: Uri,
    fileName: String,
    tabId: String,
    onResult: (String) -> Unit,
    onError: (String) -> Unit
) {
    val fileBytes = try {
        withContext(Dispatchers.IO) {
            context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
        }
    } catch (e: Exception) {
        onError("Failed to read local file: ${e.localizedMessage}")
        return
    }

    if (fileBytes == null) {
        onError("Selected file is empty")
        return
    }

    val requestBody = MultipartBody.Builder()
        .setType(MultipartBody.FORM)
        .addFormDataPart(
            "file",
            fileName,
            RequestBody.create("application/octet-stream".toMediaTypeOrNull(), fileBytes)
        )
        .build()

    val request = Request.Builder()
        .url("$API_BASE/$tabId")
        .post(requestBody)
        .build()

    try {
        withContext(Dispatchers.IO) {
            httpClient.newCall(request).execute().use { response ->
                val bodyStr = response.body?.string() ?: ""
                if (!response.isSuccessful) {
                    withContext(Dispatchers.Main) {
                        onError("HTTP error ${response.code}: $bodyStr")
                    }
                    return@use
                }

                try {
                    val json = JSONObject(bodyStr)
                    val serverMsg = json.optString("response", "")
                    withContext(Dispatchers.Main) {
                        onResult(serverMsg.ifEmpty { "Success! File uploaded successfully." })
                    }
                } catch (jsonErr: Exception) {
                    withContext(Dispatchers.Main) {
                        onResult(bodyStr) // Fallback to raw text if not JSON
                    }
                }
            }
        }
    } catch (e: IOException) {
        withContext(Dispatchers.Main) {
            onError("Network error: ${e.localizedMessage ?: "Could not connect to FastAPI at http://10.0.2.2:8000"}")
        }
    } catch (e: Exception) {
        withContext(Dispatchers.Main) {
            onError("Unexpected error: ${e.localizedMessage}")
        }
    }
}

// -------------------------------------------------------------
// FILE RESOLUTION HELPERS
// -------------------------------------------------------------
private fun getFileName(context: Context, uri: Uri): String {
    var name = ""
    val cursor = context.contentResolver.query(uri, null, null, null, null)
    if (cursor != null) {
        val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
        if (nameIndex != -1 && cursor.moveToFirst()) {
            name = cursor.getString(nameIndex)
        }
        cursor.close()
    }
    if (name.isEmpty()) {
        name = uri.path?.substringAfterLast('/') ?: "file"
    }
    return name
}

private fun getFileSizeString(context: Context, uri: Uri): String {
    var sizeBytes: Long = 0
    val cursor = context.contentResolver.query(uri, null, null, null, null)
    if (cursor != null) {
        val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
        if (sizeIndex != -1 && cursor.moveToFirst()) {
            sizeBytes = cursor.getLong(sizeIndex)
        }
        cursor.close()
    }
    return if (sizeBytes > 0) {
        String.format("%.1f KB", sizeBytes / 1024.0)
    } else {
        "Unknown size"
    }
}
