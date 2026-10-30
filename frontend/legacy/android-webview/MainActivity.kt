// [Input] Generated local React assets, Android lifecycle/network state, and the private runtime service.
// [Output] One exact-origin WebView application surface with allowlisted native capabilities.
// [Pos] Android application-process composition root.
// [Sync] 2026-10-25: preserve normal HTTPS web navigation and resources; keep app-origin bridge isolation.
// [Sync] 2026-10-24: hand off only user-activated HTTPS navigation through the shared host allowlist.
// [Sync] 2026-10-24: implement the local-resource WebView host and navigation generation boundary.

package com.inkmemory.mobile

import android.annotation.SuppressLint
import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.RenderProcessGoneDetail
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.webkit.ScriptHandler
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import com.inkmemory.mobile.bridge.MobileBridgeHandler
import com.inkmemory.mobile.platform.AndroidPlatformActions
import com.inkmemory.mobile.runtime.DreamRuntimeClient
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.util.UUID

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var platformActions: AndroidPlatformActions
    private lateinit var runtimeClient: DreamRuntimeClient
    private var bridgeHandler: MobileBridgeHandler? = null
    private var generationScript: ScriptHandler? = null
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var webViewDestroyed = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        platformActions = AndroidPlatformActions(this)
        runtimeClient = DreamRuntimeClient(this)

        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER) ||
            !WebViewFeature.isFeatureSupported(WebViewFeature.DOCUMENT_START_SCRIPT)
        ) {
            setContentView(TextView(this).apply {
                text = "The installed Android System WebView does not support the required secure bridge features."
                setPadding(48, 48, 48, 48)
            })
            return
        }

        val assetLoader = WebViewAssetLoader.Builder()
            .setDomain("appassets.androidplatform.net")
            .addPathHandler("/app/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        webView = WebView(this)
        setContentView(webView)
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            setSupportMultipleWindows(false)
            mediaPlaybackRequiresUserGesture = true
        }
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false)
        webView.webChromeClient = object : WebChromeClient() {
            override fun onCreateWindow(
                view: WebView,
                isDialog: Boolean,
                isUserGesture: Boolean,
                resultMsg: android.os.Message,
            ): Boolean = false
        }

        val handler = MobileBridgeHandler(runtimeClient, platformActions)
        bridgeHandler = handler
        WebViewCompat.addWebMessageListener(
            webView,
            "inkBridge",
            setOf(MobileBridgeHandler.APP_ORIGIN),
            handler,
        )
        webView.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                if (isLocalAppUrl(request.url)) {
                    return assetLoader.shouldInterceptRequest(request.url)
                        ?: emptyResourceResponse(404, "Not Found")
                }
                return if (request.url.scheme == "https" && !request.url.host.isNullOrBlank() && request.url.userInfo == null) null
                    else emptyResourceResponse(403, "Forbidden")
            }

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url
                if (!request.isForMainFrame) return !isLocalAppUrl(url)
                return if (isLocalAppUrl(url)) {
                    loadLocal(url.toString())
                    true
                } else {
                    !(url.scheme == "https" && !url.host.isNullOrBlank() && url.userInfo == null)
                }
            }

            override fun onRenderProcessGone(view: WebView, detail: RenderProcessGoneDetail): Boolean {
                bridgeHandler?.clearPageGeneration()
                view.destroy()
                webViewDestroyed = true
                recreate()
                return true
            }
        }

        runtimeClient.bind()
        registerNetworkObserver()
        loadLocal(APP_URL)
    }

    override fun onStart() {
        super.onStart()
        if (::platformActions.isInitialized) platformActions.markStarted(true)
        bridgeHandler?.emit("lifecycle.changed", JSONObject().put("state", "active"))
    }

    override fun onStop() {
        bridgeHandler?.emit("lifecycle.changed", JSONObject().put("state", "background"))
        if (::platformActions.isInitialized) platformActions.markStarted(false)
        super.onStop()
    }

    override fun onDestroy() {
        networkCallback?.let { callback ->
            (getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager).unregisterNetworkCallback(callback)
        }
        generationScript?.remove()
        bridgeHandler?.clearPageGeneration()
        if (::runtimeClient.isInitialized) runtimeClient.close()
        if (::platformActions.isInitialized) platformActions.close()
        if (::webView.isInitialized && !webViewDestroyed) webView.destroy()
        super.onDestroy()
    }

    private fun loadLocal(url: String) {
        val generation = "page_${UUID.randomUUID().toString().replace("-", "")}"
        generationScript?.remove()
        generationScript = WebViewCompat.addDocumentStartJavaScript(
            webView,
            "Object.defineProperty(globalThis, '__INK_MOBILE_PAGE_GENERATION__', {value: '$generation', configurable: false, writable: false});",
            setOf(MobileBridgeHandler.APP_ORIGIN),
        )
        bridgeHandler?.activatePageGeneration(generation)
        webView.loadUrl(url)
    }

    private fun registerNetworkObserver() {
        val manager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) = publishNetworkState(manager)
            override fun onLost(network: Network) = publishNetworkState(manager)
            override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) = publishNetworkState(manager)
        }
        networkCallback = callback
        manager.registerDefaultNetworkCallback(callback)
        publishNetworkState(manager)
    }

    private fun publishNetworkState(manager: ConnectivityManager) {
        val network = manager.activeNetwork
        val capabilities = network?.let(manager::getNetworkCapabilities)
        val reachable = capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true
        runOnUiThread { bridgeHandler?.emit("network.changed", JSONObject().put("reachable", reachable)) }
    }

    private fun isLocalAppUrl(url: android.net.Uri): Boolean =
        url.scheme == "https" &&
            url.authority == "appassets.androidplatform.net" &&
            url.path?.startsWith("/app/") == true

    private fun emptyResourceResponse(statusCode: Int, reason: String): WebResourceResponse = WebResourceResponse(
        "text/plain",
        "utf-8",
        statusCode,
        reason,
        emptyMap(),
        ByteArrayInputStream(ByteArray(0)),
    )

    private companion object {
        const val APP_URL = "https://appassets.androidplatform.net/app/index.html"
    }
}

