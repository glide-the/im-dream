// [Input] Bridge file/browser requests, Activity Result launchers, and application-private file handles.
// [Output] Android document-picker, export, share-sheet, and HTTPS browser operations.
// [Pos] MainActivity-owned implementation of MobilePlatformActions.
// [Sync] 2026-10-24: roll back every copied document when a multi-file import fails.
// [Sync] 2026-10-24: implement the Android system-resource bridge slice.

package com.inkmemory.mobile.platform

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Intent
import android.net.Uri
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import com.inkmemory.mobile.BuildConfig
import com.inkmemory.mobile.R
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors

internal class AndroidPlatformActions(private val activity: ComponentActivity) : MobilePlatformActions, AutoCloseable {
    private val fileStore = LocalFileStore(activity)
    private val worker = Executors.newSingleThreadExecutor()
    private val allowedExternalHosts = activity.resources
        .getStringArray(R.array.mobile_allowed_external_hosts)
        .map { it.lowercase() }
        .toSet()
    private var pendingSinglePick: ((PlatformResult) -> Unit)? = null
    private var pendingMultiplePick: ((PlatformResult) -> Unit)? = null
    private var pendingSave: Pair<File, (PlatformResult) -> Unit>? = null
    private var started = false

    private val singlePicker = activity.registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        val completion = pendingSinglePick ?: return@registerForActivityResult
        pendingSinglePick = null
        if (uri == null) completion(PlatformResult.Failure("CANCELLED", "Document selection was cancelled."))
        else importUris(listOf(uri), completion)
    }

    private val multiplePicker = activity.registerForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        val completion = pendingMultiplePick ?: return@registerForActivityResult
        pendingMultiplePick = null
        if (uris.isEmpty()) completion(PlatformResult.Failure("CANCELLED", "Document selection was cancelled."))
        else importUris(uris, completion)
    }

    private val documentCreator = activity.registerForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri ->
        val pending = pendingSave ?: return@registerForActivityResult
        pendingSave = null
        if (uri == null) {
            pending.second(PlatformResult.Failure("CANCELLED", "Document export was cancelled."))
            return@registerForActivityResult
        }
        worker.execute {
            val result = runCatching {
                activity.contentResolver.openOutputStream(uri, "w")?.use { output ->
                    pending.first.inputStream().use { input -> input.copyTo(output) }
                } ?: error("The selected export destination cannot be opened.")
                PlatformResult.Success(JSONObject().put("completed", true))
            }.getOrElse { PlatformResult.Failure("INTERNAL_ERROR", "Document export failed.") }
            activity.runOnUiThread { pending.second(result) }
        }
    }

    fun markStarted(value: Boolean) {
        started = value
    }

    override fun lifecycleState(): String = if (started) "active" else "background"

    override fun pickFiles(params: JSONObject, completion: (PlatformResult) -> Unit) {
        if (pendingSinglePick != null || pendingMultiplePick != null || pendingSave != null) {
            completion(PlatformResult.Failure("CAPABILITY_UNAVAILABLE", "A document operation is already active."))
            return
        }
        val mimeTypes = params.optJSONArray("mimeTypes").toStringList().ifEmpty { listOf("*/*") }.toTypedArray()
        if (params.optBoolean("multiple", true)) {
            pendingMultiplePick = completion
            multiplePicker.launch(mimeTypes)
        } else {
            pendingSinglePick = completion
            singlePicker.launch(mimeTypes)
        }
    }

    override fun saveFile(params: JSONObject, completion: (PlatformResult) -> Unit) {
        if (pendingSinglePick != null || pendingMultiplePick != null || pendingSave != null) {
            completion(PlatformResult.Failure("CAPABILITY_UNAVAILABLE", "A document operation is already active."))
            return
        }
        val handle = params.optString("handle")
        val file = runCatching { fileStore.resolve(handle) }.getOrElse {
            completion(PlatformResult.Failure("NOT_FOUND", "The requested application file was not found."))
            return
        }
        val suggestedName = params.optString("suggestedName")
            .replace(Regex("[\\r\\n/\\\\]"), "_")
            .take(240)
            .ifBlank { "ink-memory-document" }
        pendingSave = file to completion
        documentCreator.launch(suggestedName)
    }

    override fun shareFile(params: JSONObject, completion: (PlatformResult) -> Unit) {
        val file = runCatching { fileStore.resolve(params.optString("handle")) }.getOrElse {
            completion(PlatformResult.Failure("NOT_FOUND", "The requested application file was not found."))
            return
        }
        val uri = FileProvider.getUriForFile(activity, "${BuildConfig.APPLICATION_ID}.files", file)
        val intent = Intent(Intent.ACTION_SEND)
            .setType(params.optString("mimeType").ifBlank { "application/octet-stream" })
            .putExtra(Intent.EXTRA_STREAM, uri)
            .setClipData(ClipData.newRawUri("Ink & Memory file", uri))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        return try {
            activity.startActivity(Intent.createChooser(intent, null))
            completion(PlatformResult.Success(JSONObject().put("opened", true)))
        } catch (_: ActivityNotFoundException) {
            completion(PlatformResult.Failure("CAPABILITY_UNAVAILABLE", "No Android share target is available."))
        }
    }

    override fun openExternal(params: JSONObject, completion: (PlatformResult) -> Unit) {
        val uri = runCatching { Uri.parse(params.optString("url")) }.getOrNull()
        if (uri?.scheme != "https" || uri.host?.lowercase() !in allowedExternalHosts || uri.userInfo != null || uri.port != -1) {
            completion(PlatformResult.Failure("FORBIDDEN", "The HTTPS URL is outside the configured external-host policy."))
            return
        }
        return try {
            activity.startActivity(Intent(Intent.ACTION_VIEW, uri))
            completion(PlatformResult.Success(JSONObject().put("opened", true)))
        } catch (_: ActivityNotFoundException) {
            completion(PlatformResult.Failure("CAPABILITY_UNAVAILABLE", "No Android browser is available."))
        }
    }

    override fun close() {
        worker.shutdownNow()
    }

    private fun importUris(uris: List<Uri>, completion: (PlatformResult) -> Unit) {
        worker.execute {
            val importedHandles = mutableListOf<String>()
            val result = runCatching {
                val files = JSONArray()
                uris.forEach {
                    val imported = fileStore.importUri(it)
                    importedHandles += imported.getString("handle")
                    files.put(imported)
                }
                PlatformResult.Success(JSONObject().put("files", files))
            }.getOrElse {
                importedHandles.forEach { handle -> runCatching { fileStore.delete(handle) } }
                PlatformResult.Failure("INTERNAL_ERROR", "Selected documents could not be imported.")
            }
            activity.runOnUiThread { completion(result) }
        }
    }

    private fun JSONArray?.toStringList(): List<String> {
        if (this == null) return emptyList()
        return buildList {
            for (index in 0 until length()) {
                optString(index).takeIf { it.isNotBlank() }?.let(::add)
            }
        }
    }
}

