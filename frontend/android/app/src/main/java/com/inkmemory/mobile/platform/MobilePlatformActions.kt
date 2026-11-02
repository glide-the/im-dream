// [Input] Allowlisted bridge parameters and Android activity-result callbacks.
// [Output] Opaque file handles, document export/share results, and system-browser launches.
// [Pos] Android OS-resource adapter consumed by MobileBridgeHandler.
// [Sync] 2026-10-24: define the narrow Android platform action boundary.

package com.inkmemory.mobile.platform

import org.json.JSONObject

internal interface MobilePlatformActions {
    fun lifecycleState(): String
    fun pickFiles(params: JSONObject, completion: (PlatformResult) -> Unit)
    fun saveFile(params: JSONObject, completion: (PlatformResult) -> Unit)
    fun shareFile(params: JSONObject, completion: (PlatformResult) -> Unit)
    fun openExternal(params: JSONObject, completion: (PlatformResult) -> Unit)
}

internal sealed interface PlatformResult {
    data class Success(val value: JSONObject) : PlatformResult
    data class Failure(val code: String, val message: String) : PlatformResult
}

