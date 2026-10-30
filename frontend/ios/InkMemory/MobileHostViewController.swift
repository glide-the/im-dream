// [Input] Original Web resources/theme tokens, v1 bridge requests and iOS lifecycle/network notifications.
// [Output] One WKWebView, native page appearance, origin/generation checks and original startup/status replies.
// [Pos] Minimal iOS container; embedded Python starts before the existing React entry.
// [Sync] 2026-10-25: bind production ASGI pull streams with document-owned cancellation and stale-reply rejection.
// [Sync] 2026-10-25: load application-owned original Next after Python/Node startup qualifies its listening owner.
// [Sync] 2026-10-25: accept the original configured localhost browser origin after application-process listening verification.
// [Sync] 2026-10-25: remove the temporary startup-cache diagnostic after relay verification.
// [Sync] 2026-10-25: load the existing localhost Web/BFF through an optional build-configured LAN relay.
// [Sync] 2026-10-25: allow normal HTTPS form navigation; bridge access stays restricted to app resources.
// [Sync] 2026-10-25: start actual CPython/FastAPI and retain closed business capability gates.
// [Sync] 2026-10-24: remove unused platform registry, file storage, and duplicate native recovery UI.
// [Sync] 2026-10-25: project the existing page background/theme onto native safe areas without changing Web or keyboard layout.
// [Sync] 2026-10-27: expose a persistent RN business surface with typed path/state messages and shared runtime startup.

import Network
import OSLog
import UIKit
import WebKit

final class MobileHostViewController: UIViewController, WKScriptMessageHandler, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    // Initial --color-bg-app values from tokens.css; the loaded page owns the effective color.
    static let initialBackground = UIColor { traits in
        traits.userInterfaceStyle == .dark
            ? UIColor(red: 31.0 / 255, green: 27.0 / 255, blue: 22.0 / 255, alpha: 1)
            : UIColor(red: 246.0 / 255, green: 239.0 / 255, blue: 229.0 / 255, alpha: 1)
    }
    var appearanceDidChange: ((UIColor, UIUserInterfaceStyle) -> Void)?
    var reactNativeHost = false
    var hostStateDidChange: (([String: Any]) -> Void)?
    private var pendingNavigation: String?
    private var webFailed = false
    private var lastBusinessPath = "/story-workspace/chat"
    private var downloads: [ObjectIdentifier: URL] = [:]
    private let capabilities = RuntimeCapabilities()
    private let networkMonitor = NWPathMonitor()
    private let logger = Logger(subsystem: Bundle.main.bundleIdentifier ?? "com.inkmemory.mobile", category: "MobileHost")
    private var webView: WKWebView!
    private var page = MobilePageGenerationGate()
    private var notifications: [NSObjectProtocol] = []
    private var reachable: Bool?
    private var reloadingRenderer = false
    private var localDevelopmentRelay: LocalDevelopmentRelay?
    private var localWebOrigin: String?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = Self.initialBackground
        let content = WKUserContentController()
        content.add(WeakScriptMessageHandler(delegate: self), name: "inkBridge")
        content.add(WeakScriptMessageHandler(delegate: self), name: "inkAppearance")
        if reactNativeHost {
            content.add(WeakScriptMessageHandler(delegate: self), name: "inkHostState")
            content.addUserScript(WKUserScript(source:
                "Object.defineProperty(window, '__INK_NATIVE_HOST__', {value: Object.freeze({framework: 'react-native'}), writable: false});",
                injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }
        content.addUserScript(WKUserScript(source: #"""
            (() => {
                let previous;
                const update = () => {
                    const root = document.documentElement;
                    const background = getComputedStyle(root).getPropertyValue('--color-bg-app').trim();
                    const mode = root.dataset.themeMode || 'system';
                    const signature = background + '|' + mode;
                    if (signature === previous) return;
                    previous = signature;
                    window.webkit.messageHandlers.inkAppearance.postMessage({background, mode});
                };
                new MutationObserver(update).observe(document.documentElement, {
                    attributes: true, attributeFilter: ['data-theme', 'data-theme-mode', 'style']
                });
                matchMedia('(prefers-color-scheme: dark)').addEventListener('change', update);
                window.addEventListener('load', update, {once: true});
                update();
            })();
            """#, injectionTime: .atDocumentEnd, forMainFrameOnly: true))
        let configuration = WKWebViewConfiguration()
        configuration.userContentController = content
        configuration.setURLSchemeHandler(AppURLSchemeHandler(), forURLScheme: "ink-memory")
        configuration.websiteDataStore = .default()

        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.isOpaque = false
        webView.backgroundColor = Self.initialBackground
        webView.scrollView.backgroundColor = Self.initialBackground
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.translatesAutoresizingMaskIntoConstraints = false
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.scrollView.keyboardDismissMode = .interactive
        webView.allowsBackForwardNavigationGestures = true
#if DEBUG
        webView.isInspectable = true
#endif
        view.addSubview(webView)
        NSLayoutConstraint.activate([
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            webView.topAnchor.constraint(equalTo: view.topAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
        observeLifecycle()
        networkMonitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.reachable = path.status == .satisfied
                self?.emit("network.changed", ["reachable": path.status == .satisfied])
            }
        }
        networkMonitor.start(queue: DispatchQueue(label: "com.inkmemory.mobile.network"))
        startApplicationRuntime()
    }

    private func startApplicationRuntime() {
        if let topology = LocalDevelopmentTopology.from() {
            let relay = LocalDevelopmentRelay(topology: topology)
            localDevelopmentRelay = relay
            relay.start { [weak self] result in
                guard let self else { return }
                switch result {
                case .success:
                    self.startEmbeddedDream()
                case .failure(let error):
                    self.showStartupFailure(error, title: "无法连接本机服务")
                }
            }
        } else {
            startEmbeddedDream()
        }
    }

    private func startEmbeddedDream() {
        EmbeddedDreamBackend.shared.start { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let facts):
                self.localWebOrigin = facts["localWebOrigin"] as? String
                self.logger.notice("Dream Python started version=\(facts["pythonVersion"] as? String ?? "unknown", privacy: .public) platform=\(facts["platform"] as? String ?? "unknown", privacy: .public)")
                self.loadApplication()
            case .failure(let error):
                self.logger.error("Dream Python startup failed: \(error.localizedDescription, privacy: .public)")
                self.showStartupFailure(error, title: "Dream 启动失败")
            }
        }
    }

    deinit {
        if let generation = page.activeGeneration { EmbeddedDreamBackend.shared.closeDocument(generation) }
        networkMonitor.cancel()
        localDevelopmentRelay?.cancel()
        notifications.forEach(NotificationCenter.default.removeObserver)
        webView?.configuration.userContentController.removeScriptMessageHandler(forName: "inkBridge")
        webView?.configuration.userContentController.removeScriptMessageHandler(forName: "inkAppearance")
        webView?.configuration.userContentController.removeScriptMessageHandler(forName: "inkHostState")
    }

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        let origin = message.frameInfo.securityOrigin
        let local = localWebOrigin.flatMap(URL.init(string:))
        let localPort = local?.port ?? (local?.scheme == "https" ? 443 : 80)
        let allowedOrigin = (origin.protocol == "ink-memory" && origin.host == "app") ||
            (origin.protocol == local?.scheme && origin.host == local?.host && origin.port == localPort)
        guard message.frameInfo.isMainFrame, allowedOrigin else { return }
        if message.name == "inkHostState", reactNativeHost,
           let state = message.body as? [String: Any],
           let path = state["path"] as? String, path.hasPrefix("/"), !path.hasPrefix("//"),
           let authenticated = state["authenticated"] as? Bool {
            if authenticated && path.hasPrefix("/story-workspace/") { lastBusinessPath = path }
            var projection: [String: Any] = ["path": path, "authenticated": authenticated, "loading": false, "failed": false]
            if let failed = state["authFailure"] as? Bool { projection["authFailure"] = failed }
            hostStateDidChange?(projection)
            return
        }
        if message.name == "inkAppearance", message.frameInfo.isMainFrame {
            updateAppearance(message.body)
            return
        }
        guard message.name == "inkBridge" else { return }
        do {
            let request = try MobileBridgeContract.parse(message.body)
            guard page.accept(request.pageGeneration) else {
                reply(MobileBridgeContract.failure(request: request, code: "PROTOCOL_MISMATCH", message: "The Web document changed."))
                return
            }
            switch request.method {
            case "app.getInfo":
                reply(MobileBridgeContract.success(request: request, result: capabilities.appInfo()))
            case "runtime.getCapabilities":
                reply(MobileBridgeContract.success(request: request, result: capabilities.snapshot()))
            case "lifecycle.getState":
                var state: [String: Any] = ["state": lifecycleState]
                state["reachable"] = reachable.map { $0 as Any } ?? NSNull()
                reply(MobileBridgeContract.success(request: request, result: state))
            case "runtime.request", "runtime.response.read", "runtime.cancel":
                EmbeddedDreamBackend.shared.bridge(request) { [weak self] result in
                    guard let self, self.page.isCurrent(request.pageGeneration) else { return }
                    switch result {
                    case .success(var value):
                        // HttpOnly response values stay outside the JavaScript envelope.
                        value.removeValue(forKey: "nativeCookies")
                        self.reply(MobileBridgeContract.success(request: request, result: value))
                    case .failure(let error):
                        self.logger.error("Local transport failed code=\((error as NSError).code)")
                        self.reply(MobileBridgeContract.failure(request: request, code: "INTERNAL_ERROR", message: "Local request failed."))
                    }
                }
            default:
                reply(MobileBridgeContract.failure(request: request, code: "CAPABILITY_UNAVAILABLE", message: "This device integration is not implemented."))
            }
        } catch let error as MobileBridgeFailure {
            guard let body = message.body as? [String: Any],
                  let id = body["id"] as? String,
                  let generation = body["pageGeneration"] as? String else { return }
            reply(MobileBridgeContract.failure(id: id, pageGeneration: generation, code: error.code, message: error.message))
        } catch {}
    }

    private func updateAppearance(_ value: Any) {
        guard let appearance = value as? [String: Any],
              let background = appearance["background"] as? String,
              background.count == 7, background.first == "#",
              let rgb = UInt32(background.dropFirst(), radix: 16), rgb <= 0xFFFFFF,
              let mode = appearance["mode"] as? String,
              ["light", "dark", "system"].contains(mode) else { return }
        let color = UIColor(red: CGFloat((rgb >> 16) & 255) / 255,
                            green: CGFloat((rgb >> 8) & 255) / 255,
                            blue: CGFloat(rgb & 255) / 255, alpha: 1)
        view.backgroundColor = color
        webView.backgroundColor = color
        webView.scrollView.backgroundColor = color
        webView.underPageBackgroundColor = color
        let style: UIUserInterfaceStyle = mode == "system" ? .unspecified : mode == "dark" ? .dark : .light
        if reactNativeHost { view.window?.overrideUserInterfaceStyle = style }
        appearanceDidChange?(color, style)
        hostStateDidChange?(["background": background, "mode": mode])
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if action.shouldPerformDownload, let target = action.request.url,
           isBusinessDownloadURL(target) {
            decisionHandler(.download)
            return
        }
        if action.targetFrame?.isMainFrame == false,
           let target = action.request.url, let source = webView.url,
           ((target.scheme == source.scheme && target.host == source.host && target.port == source.port)
            || target.absoluteString == "about:blank" || target.absoluteString == "about:srcdoc") {
            decisionHandler(.allow)
            return
        }
        if action.navigationType == .linkActivated, let target = action.request.url,
           target.scheme == "https", target.host != webView.url?.host {
            UIApplication.shared.open(target)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(AppNavigationPolicy.allows(action.request.url, mainFrame: action.targetFrame?.isMainFrame == true) ? .allow : .cancel)
    }

    private func isBusinessDownloadURL(_ target: URL) -> Bool {
        guard let source = localWebOrigin.flatMap(URL.init(string:)) else { return false }
        let resource = target.scheme == "blob" ? URL(string: String(target.absoluteString.dropFirst(5))) : target
        return resource?.scheme == source.scheme && resource?.host == source.host && resource?.port == source.port
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse,
                 decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        let disposition = (response.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition") ?? ""
        if let target = response.response.url, isBusinessDownloadURL(target),
           !response.canShowMIMEType || disposition.lowercased().hasPrefix("attachment") {
            decisionHandler(.download)
        } else { decisionHandler(.allow) }
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        download.delegate = self
    }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        download.delegate = self
    }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse,
                  suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        do {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ink-export-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
            let name = (suggestedFilename as NSString).lastPathComponent
            let file = directory.appendingPathComponent(name.isEmpty || name == "." || name == ".." ? "download" : name)
            downloads[ObjectIdentifier(download)] = file
            completionHandler(file)
        } catch { completionHandler(nil) }
    }
    func downloadDidFinish(_ download: WKDownload) {
        guard let file = downloads.removeValue(forKey: ObjectIdentifier(download)) else { return }
        let activity = UIActivityViewController(activityItems: [file], applicationActivities: nil)
        activity.popoverPresentationController?.sourceView = view
        activity.popoverPresentationController?.sourceRect = CGRect(x: view.bounds.midX, y: view.bounds.midY, width: 1, height: 1)
        activity.completionWithItemsHandler = { _, _, _, _ in
            try? FileManager.default.removeItem(at: file.deletingLastPathComponent())
        }
        present(activity, animated: true)
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        if let file = downloads.removeValue(forKey: ObjectIdentifier(download)) {
            try? FileManager.default.removeItem(at: file.deletingLastPathComponent())
        }
        logger.error("File export failed code=\((error as NSError).code)")
        let alert = UIAlertController(title: "文件下载失败", message: "请检查连接后重试。", preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "关闭", style: .cancel))
        if presentedViewController == nil { present(alert, animated: true) }
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        guard action.targetFrame == nil, let url = action.request.url else { return nil }
        if LocalDevelopmentTopology.isLoopbackWebURL(url) { webView.load(action.request) }
        else if url.scheme == "https" { UIApplication.shared.open(url) }
        return nil
    }

    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        closeDocument()
        hostStateDidChange?(["loading": true, "failed": false, "authenticated": false])
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        reloadingRenderer = false
        webFailed = false
        hostStateDidChange?(["loading": false, "failed": false])
        if let path = pendingNavigation {
            pendingNavigation = nil
            navigateFromHost(path)
        }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        showLoadFailure(error)
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        showLoadFailure(error)
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        closeDocument()
        hostStateDidChange?(["loading": true])
        if reloadingRenderer {
            showLoadFailure(NSError(domain: WKError.errorDomain, code: WKError.webContentProcessTerminated.rawValue))
        } else {
            reloadingRenderer = true
            loadApplication()
        }
    }

    private var lifecycleState: String {
        switch UIApplication.shared.applicationState {
        case .active: return "active"
        case .inactive: return "inactive"
        case .background: return "background"
        @unknown default: return "unknown"
        }
    }

    private func closeDocument() {
        if let generation = page.activeGeneration {
            EmbeddedDreamBackend.shared.closeDocument(generation)
        }
        page.reset()
    }

    private func observeLifecycle() {
        for name in [UIApplication.didBecomeActiveNotification, UIApplication.willResignActiveNotification, UIApplication.didEnterBackgroundNotification] {
            notifications.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
                guard let self else { return }
                self.emit("lifecycle.changed", ["state": self.lifecycleState])
            })
        }
    }

    private func emit(_ name: String, _ payload: Any) {
        guard let next = page.nextEvent(),
              let envelope = MobileBridgeContract.event(name: name, payload: payload, pageGeneration: next.generation, sequence: next.sequence) else { return }
        reply(envelope)
    }

    private func reply(_ envelope: [String: Any]) {
        guard JSONSerialization.isValidJSONObject(envelope) else { return }
        webView.callAsyncJavaScript("window.__inkBridgeReceive?.(message)", arguments: ["message": envelope], in: nil, in: .page) { [weak self] result in
            if case .failure(let error) = result {
                self?.logger.error("Bridge delivery failed code=\((error as NSError).code)")
            }
        }
    }

    private func loadApplication() {
        guard let target = localDevelopmentRelay == nil ? localWebOrigin : "http://localhost:5173/",
              let url = URL(string: target), ["127.0.0.1", "localhost", "::1", "[::1]"].contains(url.host ?? "") || localDevelopmentRelay != nil else {
            showStartupFailure(CocoaError(.coderInvalidValue), title: "Dream 启动失败")
            return
        }
        let entry = reactNativeHost ? URL(string: lastBusinessPath, relativeTo: url)?.absoluteURL ?? url : url
        webView.load(URLRequest(url: entry))
    }

    func navigateFromHost(_ path: String) {
        guard path.hasPrefix("/story-workspace/"), !path.contains("://"), !path.contains("\\"),
              let localWebOrigin, let source = URL(string: localWebOrigin),
              let current = webView?.url, current.host == source.host, current.port == source.port else {
            pendingNavigation = path.hasPrefix("/story-workspace/") ? path : nil
            return
        }
        if webFailed {
            webFailed = false
            lastBusinessPath = path
            loadApplication()
            return
        }
        webView.callAsyncJavaScript(
            "window.dispatchEvent(new CustomEvent('ink:host-navigate', {detail: {path}}));",
            arguments: ["path": path], in: nil, in: .page) { _ in }
    }

    func logoutFromHost() {
        guard let source = localWebOrigin.flatMap(URL.init(string:)), let current = webView?.url,
              current.scheme == source.scheme, current.host == source.host, current.port == source.port else { return }
        webView.callAsyncJavaScript("window.dispatchEvent(new Event('ink:host-logout'));",
                                   arguments: [:], in: nil, in: .page) { _ in }
    }

    private func showStartupFailure(_ error: Error, title: String) {
        logger.error("Application startup failed: \(error.localizedDescription, privacy: .public)")
        guard presentedViewController == nil else { return }
        let message = localDevelopmentRelay == nil ? "应用内服务启动失败，请重试。" : "请检查开发连接后重试。"
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "重试", style: .default) { [weak self] _ in self?.startApplicationRuntime() })
        present(alert, animated: true)
    }

    private func showLoadFailure(_ error: Error) {
        let failure = error as NSError
        if failure.code == NSURLErrorCancelled { return }
        logger.error("Local page load failed code=\(failure.code)")
        if reactNativeHost {
            webFailed = true
            hostStateDidChange?(["loading": false, "failed": true])
            return
        }
        guard presentedViewController == nil else { return }
        let alert = UIAlertController(title: "无法打开工作区", message: "本地页面载入失败，请重试。", preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "重新载入", style: .default) { [weak self] _ in
            self?.reloadingRenderer = false
            self?.loadApplication()
        })
        present(alert, animated: true)
    }
}

