// [Input] JSON messages from the exact-origin Android WebMessage listener.
// [Output] Strict v1 requests, generation-bound responses, sequenced events, and stable capability states.
// [Pos] Android source mirror of mobile/shared/bridge/contract.json.
// [Sync] 2026-10-25: remove native account RPCs and callback; existing web authentication remains authoritative.
// [Sync] 2026-10-24: implement the Android v1 bridge envelope with navigation isolation.

package com.inkmemory.mobile.bridge

import org.json.JSONObject

internal object MobileBridgeContract {
    const val VERSION = "1.0"
    private val identifier = Regex("^[A-Za-z0-9_-]{1,96}$")

    val methods: Set<String> = setOf(
        "app.getInfo",
        "runtime.getCapabilities",
        "runtime.request",
        "runtime.response.read",
        "runtime.cancel",
        "lifecycle.getState",
        "file.pick",
        "file.save",
        "share.open",
        "external.open",
    )

    val events: Set<String> = setOf(
        "lifecycle.changed",
        "network.changed",
        "runtime.changed",
    )

    data class Request(
        val id: String,
        val pageGeneration: String,
        val method: String,
        val params: JSONObject,
        val source: String,
    )

    class ProtocolFailure(val code: String, override val message: String) : IllegalArgumentException(message)

    fun parse(source: String, expectedPageGeneration: String): Request {
        val value = try {
            JSONObject(source)
        } catch (_: Exception) {
            throw ProtocolFailure("BAD_REQUEST", "Bridge request must be a JSON object.")
        }
        if (value.optString("version") != VERSION) {
            throw ProtocolFailure("PROTOCOL_MISMATCH", "Bridge protocol version is unsupported.")
        }
        val id = value.optString("id")
        if (!identifier.matches(id)) {
            throw ProtocolFailure("BAD_REQUEST", "Bridge request identifier is invalid.")
        }
        val pageGeneration = value.optString("pageGeneration")
        if (!identifier.matches(pageGeneration) || pageGeneration != expectedPageGeneration) {
            throw ProtocolFailure("PROTOCOL_MISMATCH", "Bridge page generation is inactive.")
        }
        val method = value.optString("method")
        if (method !in methods) {
            throw ProtocolFailure("FORBIDDEN", "Bridge method is not allowlisted.")
        }
        val params = value.optJSONObject("params")
            ?: throw ProtocolFailure("BAD_REQUEST", "Bridge params must be an object.")
        return Request(id, pageGeneration, method, params, source)
    }

    fun success(request: Request, result: Any): JSONObject = JSONObject()
        .put("version", VERSION)
        .put("pageGeneration", request.pageGeneration)
        .put("id", request.id)
        .put("ok", true)
        .put("result", result)

    fun failure(request: Request, code: String, message: String): JSONObject = failure(
        id = request.id,
        pageGeneration = request.pageGeneration,
        code = code,
        message = message,
    )

    fun failure(id: String, pageGeneration: String, code: String, message: String): JSONObject = JSONObject()
        .put("version", VERSION)
        .put("pageGeneration", pageGeneration)
        .put("id", id)
        .put("ok", false)
        .put("error", JSONObject().put("code", code).put("message", message))

    fun event(name: String, pageGeneration: String, sequence: Long, payload: Any): JSONObject? {
        if (name !in events || sequence <= 0) return null
        return JSONObject()
            .put("version", VERSION)
            .put("pageGeneration", pageGeneration)
            .put("sequence", sequence.toString())
            .put("event", name)
            .put("payload", payload)
    }

    fun capabilitySnapshot(): JSONObject = JSONObject()
        .put("revision", "android-host-v1")
        .put(
            "capabilities",
            JSONObject()
                .put("python", unavailable("PYTHON_EMBEDDED_BUILD_UNQUALIFIED"))
                .put("claudeRuntime", unavailable("CLAUDE_CLI_UNSUPPORTED_ANDROID"))
                .put("localTransport", unavailable("LOCAL_ASGI_TRANSPORT_UNQUALIFIED"))
                .put("files", unavailable("NATIVE_FILES_CONTRACT_UNQUALIFIED")),
        )

    fun isCapabilityAvailable(name: String): Boolean = capabilitySnapshot()
        .getJSONObject("capabilities")
        .optJSONObject(name)
        ?.optString("state") == "available"

    private fun unavailable(reasonCode: String): JSONObject = JSONObject()
        .put("state", "unavailable")
        .put("reasonCode", reasonCode)
}

