// [Input] Runtime bridge requests and Android service-connection lifecycle.
// [Output] Generation-preserving JSON callbacks from the private :dream_runtime process.
// [Pos] UI-process owner of the non-exported Dream runtime Binder connection.
// [Sync] 2026-10-24: add fail-closed Binder routing without remote runtime fallback.

package com.inkmemory.mobile.runtime

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.IBinder
import android.os.RemoteException
import android.os.Handler
import android.os.Looper
import org.json.JSONObject

internal class DreamRuntimeClient(
    private val context: Context,
) : AutoCloseable {
    private val mainHandler = Handler(Looper.getMainLooper())
    private var service: IDreamRuntime? = null
    private var bound = false

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, binder: IBinder) {
            service = IDreamRuntime.Stub.asInterface(binder)
        }

        override fun onServiceDisconnected(name: ComponentName) {
            service = null
        }

        override fun onBindingDied(name: ComponentName) {
            service = null
        }

        override fun onNullBinding(name: ComponentName) {
            service = null
        }
    }

    fun bind() {
        if (bound) return
        bound = context.bindService(
            Intent(context, DreamRuntimeService::class.java),
            connection,
            Context.BIND_AUTO_CREATE,
        )
    }

    fun dispatch(method: String, requestJson: String, callback: (JSONObject) -> Unit) {
        val runtime = service
        if (runtime == null) {
            callback(unavailableFrom(requestJson, "The private Dream runtime process is unavailable."))
            return
        }
        val binderCallback = object : IDreamRuntimeCallback.Stub() {
            override fun onResult(responseJson: String) {
                val response = runCatching { JSONObject(responseJson) }.getOrElse {
                    unavailableFrom(requestJson, "The private Dream runtime returned an invalid response.")
                }
                mainHandler.post { callback(response) }
            }
        }
        try {
            when (method) {
                "runtime.request" -> runtime.request(requestJson, binderCallback)
                "runtime.response.read" -> runtime.readResponse(requestJson, binderCallback)
                "runtime.cancel" -> runtime.cancel(requestJson, binderCallback)
                else -> callback(unavailableFrom(requestJson, "The requested runtime operation is unavailable."))
            }
        } catch (_: RemoteException) {
            callback(unavailableFrom(requestJson, "The private Dream runtime process disconnected."))
        }
    }

    override fun close() {
        if (bound) context.unbindService(connection)
        bound = false
        service = null
    }

    private fun unavailableFrom(requestJson: String, message: String): JSONObject {
        val value = runCatching { JSONObject(requestJson) }.getOrElse { JSONObject() }
        val id = value.optString("id").ifBlank { "runtime" }
        val generation = value.optString("pageGeneration").ifBlank { "invalid" }
        return JSONObject()
            .put("version", "1.0")
            .put("pageGeneration", generation)
            .put("id", id)
            .put("ok", false)
            .put(
                "error",
                JSONObject()
                    .put("code", "CAPABILITY_UNAVAILABLE")
                    .put("message", message),
            )
    }
}

