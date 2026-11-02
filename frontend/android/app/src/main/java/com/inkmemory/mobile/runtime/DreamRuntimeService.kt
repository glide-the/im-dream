// [Input] Binder calls containing generation-bound v1 bridge request JSON.
// [Output] Explicit capability snapshot and CAPABILITY_UNAVAILABLE response envelopes.
// [Pos] Private :dream_runtime process boundary reserved for a qualified embedded Python runtime.
// [Sync] 2026-10-24: implement the fail-closed Android runtime service scaffold.

package com.inkmemory.mobile.runtime

import android.app.Service
import android.content.Intent
import android.os.IBinder
import com.inkmemory.mobile.bridge.MobileBridgeContract
import org.json.JSONObject

class DreamRuntimeService : Service() {
    private val binder = object : IDreamRuntime.Stub() {
        override fun getCapabilities(): String = MobileBridgeContract.capabilitySnapshot().toString()

        override fun request(requestJson: String, callback: IDreamRuntimeCallback) {
            unavailable(requestJson, callback, "The qualified embedded Dream Python runtime is unavailable.")
        }

        override fun readResponse(requestJson: String, callback: IDreamRuntimeCallback) {
            unavailable(requestJson, callback, "The qualified embedded Dream response stream is unavailable.")
        }

        override fun cancel(requestJson: String, callback: IDreamRuntimeCallback) {
            unavailable(requestJson, callback, "The qualified embedded Dream runtime is unavailable.")
        }
    }

    override fun onBind(intent: Intent): IBinder = binder

    private fun unavailable(requestJson: String, callback: IDreamRuntimeCallback, message: String) {
        val value = runCatching { JSONObject(requestJson) }.getOrElse { JSONObject() }
        val id = value.optString("id").takeIf { it.matches(IDENTIFIER) } ?: "runtime"
        val generation = value.optString("pageGeneration").takeIf { it.matches(IDENTIFIER) } ?: "invalid"
        callback.onResult(
            MobileBridgeContract.failure(
                id = id,
                pageGeneration = generation,
                code = "CAPABILITY_UNAVAILABLE",
                message = message,
            ).toString(),
        )
    }

    private companion object {
        val IDENTIFIER = Regex("^[A-Za-z0-9_-]{1,96}$")
    }
}

