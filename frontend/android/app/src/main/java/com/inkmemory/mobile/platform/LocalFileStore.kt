// [Input] User-selected content URIs and opaque ink-file handles.
// [Output] Application-private file copies and canonical paths constrained to mobile-files.
// [Pos] Android file-capability storage boundary; callers never receive raw container paths.
// [Sync] 2026-10-24: add batch rollback support for opaque Android file imports.

package com.inkmemory.mobile.platform

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import com.inkmemory.mobile.R
import org.json.JSONObject
import java.io.File
import java.io.FileNotFoundException
import java.util.UUID

internal class LocalFileStore(private val context: Context) {
    private val root = File(context.filesDir, "mobile-files").apply { mkdirs() }.canonicalFile
    private val maximumImportBytes = context.resources.getInteger(R.integer.mobile_maximum_import_bytes).toLong()
    private val allowedExtensions = context.resources.getStringArray(R.array.mobile_allowed_file_extensions).toSet()

    fun importUri(uri: Uri): JSONObject {
        val metadata = metadata(uri)
        if (metadata.second != null && metadata.second!! > maximumImportBytes) {
            throw IllegalArgumentException("The selected file exceeds the configured attachment limit.")
        }
        val extension = metadata.first.substringAfterLast('.', "").lowercase()
        if (extension !in allowedExtensions) {
            throw IllegalArgumentException("The selected file type is not allowed.")
        }
        val id = UUID.randomUUID().toString().replace("-", "")
        val directory = File(root, id).apply { mkdir() }
        val destination = File(directory, metadata.first)
        try {
            context.contentResolver.openInputStream(uri)?.use { input ->
                destination.outputStream().use { output ->
                    val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                    var copied = 0L
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        copied += count
                        if (copied > maximumImportBytes) {
                            throw IllegalArgumentException("The selected file exceeds the configured attachment limit.")
                        }
                        output.write(buffer, 0, count)
                    }
                }
            } ?: throw FileNotFoundException("The selected document cannot be opened.")
            if (!destination.isFile || destination.length() > maximumImportBytes) {
                throw IllegalArgumentException("The imported file failed validation.")
            }
            return JSONObject()
                .put("handle", "ink-file:$id")
                .put("name", metadata.first)
                .put("mimeType", context.contentResolver.getType(uri) ?: "application/octet-stream")
                .put("size", destination.length())
        } catch (error: Exception) {
            directory.deleteRecursively()
            throw error
        }
    }

    fun resolve(handle: String): File {
        val id = HANDLE.matchEntire(handle)?.groupValues?.get(1)
            ?: throw IllegalArgumentException("The opaque file handle is invalid.")
        val directory = File(root, id).canonicalFile
        val files = directory.listFiles()?.filter(File::isFile).orEmpty()
        val candidate = files.singleOrNull()?.canonicalFile
        if (directory.parentFile != root || candidate == null || candidate.parentFile != directory) {
            throw FileNotFoundException("The requested application file was not found.")
        }
        return candidate
    }

    fun delete(handle: String) {
        val id = HANDLE.matchEntire(handle)?.groupValues?.get(1)
            ?: throw IllegalArgumentException("The opaque file handle is invalid.")
        val directory = File(root, id).canonicalFile
        if (directory.parentFile != root) {
            throw IllegalArgumentException("The opaque file handle is invalid.")
        }
        directory.deleteRecursively()
    }

    private fun metadata(uri: Uri): Pair<String, Long?> {
        var name: String? = null
        var size: Long? = null
        context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)
            ?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
                    if (nameIndex >= 0) name = cursor.getString(nameIndex)
                    if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) size = cursor.getLong(sizeIndex)
                }
            }
        val safeName = name
            ?.replace(Regex("[\\r\\n/\\\\]"), "_")
            ?.take(240)
            ?.ifBlank { null }
            ?: "document"
        return safeName to size
    }

    private companion object {
        val HANDLE = Regex("^ink-file:([A-Za-z0-9_-]{1,96})$")
    }
}

