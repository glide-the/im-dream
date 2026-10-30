// [Input] Exact-origin WebMessage calls, active page generation, private runtime client, and Android platform services.
// [Output] Generation-correlated responses plus monotonically sequenced lifecycle, network, and runtime events.
// [Pos] Sole JavaScript-to-native dispatch boundary in the Android application process.
// [Sync] 2026-10-25: delete the speculative native authentication dispatcher.
// [Sync] 2026-10-24: implement allowlisted Android bridge routing and stale-callback rejection.

package com.inkmemory.mobile.bridge

import android.net.Uri
import android.webkit.WebView
import androidx.webkit.JavaScriptReplyProxy
import androidx.webkit.WebMessageCompat
import androidx.webkit.WebViewCompat
import com.inkmemory.mobile.BuildConfig
import com.inkmemory.mobile.platform.MobilePlatformActions
import com.inkmemory.mobile.platform.PlatformResult
import com.inkmemory.mobile.runtime.DreamRuntimeClient
import org.json.JSONObject

internal class MobileBridgeHandler(
    private val runtimeClient: DreamRuntimeClient,
    private val platform: MobilePlatformActions,
) : WebViewCompat.WebMessageListener {
    private var activePageGeneration: String? = null
    private var activeReplyProxy: JavaScriptReplyProxy? = null
    private var eventSequence = 0L

    fun activatePageGeneration(generation: String) {
        require(GENERATION.matches(generation))
        activePageGeneration = generation
        activeReplyProxy = null
        eventSequence = 0L
    }

    fun clearPageGeneration() {
        activePageGeneration = null
        activeReplyProxy = null
        eventSequence = 0L
    }

    override fun onPostMessage(
        view: WebView,
        message: WebMessageCompat,
        sourceOrigin: Uri,
        isMainFrame: Boolean,
        replyProxy: JavaScriptReplyProxy,
    ) {
        if (!isMainFrame || !isApplicationOrigin(sourceOrigin)) return
        val generation = activePageGeneration ?: return
        val request = try {
            MobileBridgeContract.parse(message.data ?: return, generation)
        } catch (failure: MobileBridgeContract.ProtocolFailure) {
            replyProtocolFailure(message.data, generation, failure, replyProxy)
            return
        }
        activeReplyProxy = replyProxy
        dispatch(request, replyProxy)
    }

    fun emit(name: String, payload: JSONObject) {
        val generation = activePageGeneration ?: return
        val replyProxy = activeReplyProxy ?: return
        eventSequence += 1
        val event = MobileBridgeContract.event(name, generation, eventSequence, payload) ?: return
        replyProxy.postMessage(event.toString())
    }

    private fun dispatch(request: MobileBridgeContract.Request, replyProxy: JavaScriptReplyProxy) {
        when (request.method) {
            "app.getInfo" -> post(
                request,
                replyProxy,
                MobileBridgeContract.success(
                    request,
                    JSONObject()
                        .put("platform", "android")
                        .put("appVersion", BuildConfig.VERSION_NAME)
                        .put("buildNumber", BuildConfig.VERSION_CODE.toString())
                        .put("bridgeVersion", MobileBridgeContract.VERSION),
                ),
            )
            "runtime.getCapabilities" -> post(
                request,
                replyProxy,
                MobileBridgeContract.success(request, MobileBridgeContract.capabilitySnapshot()),
            )
            "lifecycle.getState" -> post(
                request,
                replyProxy,
                MobileBridgeContract.success(
                    request,
                    JSONObject().put("state", platform.lifecycleState()),
                ),
            )
            "runtime.request", "runtime.response.read", "runtime.cancel" -> {
                runtimeClient.dispatch(request.method, request.source) { response -> post(request, replyProxy, response) }
            }
            "file.pick", "file.save", "share.open" -> {
                if (!MobileBridgeContract.isCapabilityAvailable("files")) {
                    post(
                        request,
                        replyProxy,
                        MobileBridgeContract.failure(
                            request,
                            "CAPABILITY_UNAVAILABLE",
                            "The native file contract is not qualified for this application.",
                        ),
                    )
                } else if (request.method == "file.pick") {
                    platform.pickFiles(request.params) { result -> postPlatformResult(request, replyProxy, result) }
                } else if (request.method == "file.save") {
                    platform.saveFile(request.params) { result -> postPlatformResult(request, replyProxy, result) }
                } else {
                    platform.shareFile(request.params) { result -> postPlatformResult(request, replyProxy, result) }
                }
            }
            "external.open" -> platform.openExternal(request.params) { result -> postPlatformResult(request, replyProxy, result) }
            else -> post(
                request,
                replyProxy,
                MobileBridgeContract.failure(request, "FORBIDDEN", "Bridge method is not allowlisted."),
            )
        }
    }

    private fun postPlatformResult(
        request: MobileBridgeContract.Request,
        replyProxy: JavaScriptReplyProxy,
        result: PlatformResult,
    ) {
        val envelope = when (result) {
            is PlatformResult.Success -> MobileBridgeContract.success(request, result.value)
            is PlatformResult.Failure -> MobileBridgeContract.failure(request, result.code, result.message)
        }
        post(request, replyProxy, envelope)
    }

    private fun post(
        request: MobileBridgeContract.Request,
        replyProxy: JavaScriptReplyProxy,
        envelope: JSONObject,
    ) {
        if (request.pageGeneration != activePageGeneration) return
        replyProxy.postMessage(envelope.toString())
    }

    private fun replyProtocolFailure(
        raw: String?,
        generation: String,
        failure: MobileBridgeContract.ProtocolFailure,
        replyProxy: JavaScriptReplyProxy,
    ) {
        val value = runCatching { JSONObject(raw.orEmpty()) }.getOrElse { return }
        val id = value.optString("id")
        val requestGeneration = value.optString("pageGeneration")
        if (!GENERATION.matches(id) || requestGeneration != generation) return
        replyProxy.postMessage(
            MobileBridgeContract.failure(id, generation, failure.code, failure.message).toString(),
        )
    }

    companion object {
        const val APP_ORIGIN = "https://appassets.androidplatform.net"
        private val GENERATION = Regex("^[A-Za-z0-9_-]{1,96}$")

        private fun isApplicationOrigin(origin: Uri): Boolean =
            origin.scheme == "https" &&
                origin.host == "appassets.androidplatform.net" &&
                origin.port == -1 &&
                origin.path.orEmpty().isEmpty() &&
                origin.query == null &&
                origin.fragment == null
    }
}

