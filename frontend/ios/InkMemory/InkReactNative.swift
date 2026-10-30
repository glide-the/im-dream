// [Sync] 2026-10-30: settle account login after dismissing its navigation sheet; close cancels, navigation completion rechecks the original session.
// [Sync] 2026-10-29: bind MCP resource authorization to its operation and exact packaged callback through ASWebAuthenticationSession.
// [Sync] 2026-10-29: project only Content-Type/Retry-After response metadata; Cookie/credential response headers stay native.
// [Sync] 2026-10-29: expose Foundation UUID for the original idempotent Settings request ID.
// [Sync] 2026-10-28: honor caller-owned HTTP request IDs so AbortSignal cancels URLSession before response headers.
// [Sync] 2026-10-28: original single-file export shares ordered multi-PNG system export and image-only DOM leases.
// [Sync] 2026-10-28: existing file picker accepts directory intent; original Workspace batches acquire and release each selected private handle.
// [Sync] 2026-10-28: expose GET-only binary Workspace leases, text reads and system export without passing binary bytes through JS.
// [Sync] 2026-10-28: message Copy writes caller-selected text to UIPasteboard without a service request.
// [Input] React Native lifecycle calls and relative original BFF HTTP requests.
// [Output] App-owned runtime, incremental HTTP reads and normal Web authentication.
// [Pos] iOS platform adapter; React Native owns main application screens.
// [Sync] 2026-10-28: import user-selected file handles and upload bytes through the original BFF or signed direct URL; retain Cookie/CSRF ownership and request cancellation.
// [Sync] 2026-10-28: accept the local sketch PNG through existing opaque-file ownership and cleanup.
import React
import UIKit
import WebKit
import OSLog
import AuthenticationServices

@objc(InkRuntime)
final class InkRuntime: RCTEventEmitter, UIAdaptivePresentationControllerDelegate, ASWebAuthenticationPresentationContextProviding {
    private let logger = Logger(subsystem: "com.inkmemory.mobile", category: "ReactNativeRuntime")
    private var origin: URL?
    private var requests: [String: NativeHTTPResponse] = [:]
    private var login: UINavigationController?
    private var loginResolve: RCTPromiseResolveBlock?
    private var loginFinishing = false
    private var loginReject: RCTPromiseRejectBlock?
    private var loginProbe: NativeLoginSessionProbe?
    private var fileStore: NativePickedFileStore?
    private var filePicker: NativeFilePicker?
    private var observing = false
    private var workspaceReads: [String: NativeWorkspaceFileRead] = [:]
    private var exportingFile = false
    private var preparingUploads = Set<String>()
    private var cancelledUploads = Set<String>()
    private var mcpAuthorization: ASWebAuthenticationSession?
    private var mcpAuthorizationID: String?
    private var mcpAuthorizationReject: RCTPromiseRejectBlock?
    private var mcpAuthorizationAnchor: UIWindow?
    @objc override static func requiresMainQueueSetup() -> Bool { true }
    override func supportedEvents() -> [String]! { ["InkUploadProgress"] }
    override func startObserving() { DispatchQueue.main.async { self.observing = true } }
    override func stopObserving() { DispatchQueue.main.async { self.observing = false } }

    @objc(randomUUID:rejecter:)
    func randomUUID(_ resolve: RCTPromiseResolveBlock, rejecter reject: RCTPromiseRejectBlock) {
        resolve(UUID().uuidString.lowercased())
    }
    @objc(ensureStarted:rejecter:)
    func ensureStarted(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        logger.info("Runtime startup requested")
        EmbeddedDreamBackend.shared.start { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let facts):
                    guard let value = facts["localWebOrigin"] as? String, let url = URL(string: value),
                          ["localhost", "127.0.0.1", "::1", "[::1]"].contains(url.host ?? "") else {
                        reject("RUNTIME_ORIGIN_INVALID", "本机服务地址无效。", nil); return
                    }
                    self.origin = url
                    self.logger.info("Runtime ready")
                    resolve(["state": "ready", "localWebOrigin": value])
                case .failure(let error): reject("RUNTIME_START_FAILED", "本机服务启动失败，请重试。", error)
                }
            }
        }
    }
    @objc(readWorkspaceFile:resolver:rejecter:)
    func readWorkspaceFile(_ options: NSDictionary, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let id = options["id"] as? String, !id.isEmpty, self.workspaceReads[id] == nil,
                  let origin = self.origin, let request = try? NativeWorkspaceFileRequest.make(origin: origin, options: options) else { reject("WORKSPACE_READ_INVALID", "文件读取地址无效。", nil); return }
            do {
                if self.fileStore == nil { self.fileStore = try NativePickedFileStore() }
                let store = self.fileStore!
                let read = try NativeWorkspaceFileRead(request: request, store: store) { [weak self] result in
                    DispatchQueue.main.async {
                        guard let self else { if case .success(let file) = result { store.release(file.id) }; return }
                        self.workspaceReads.removeValue(forKey: id)
                        switch result {
                        case .success(let file): resolve(file.metadata)
                        case .failure(let error):
                            if case NativeWorkspaceFileError.http(let status) = error { reject("WORKSPACE_HTTP_\(status)", "文件暂时不可读取。", nil) }
                            else { reject("WORKSPACE_READ_FAILED", "文件读取失败，请重试。", nil) }
                        }
                    }
                }
                self.workspaceReads[id] = read; read.start()
            } catch { reject("WORKSPACE_READ_FAILED", "文件读取失败，请重试。", nil) }
        }
    }
    @objc(cancelWorkspaceFile:)
    func cancelWorkspaceFile(_ id: String) { DispatchQueue.main.async { self.workspaceReads[id]?.cancel() } }
    @objc(readWorkspaceText:resolver:rejecter:)
    func readWorkspaceText(_ id: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let store = self.fileStore else { reject("WORKSPACE_TEXT_INVALID", "文档已关闭。", nil); return }
            DispatchQueue.global(qos: .userInitiated).async {
                do { resolve(try store.readText(id)) } catch { reject("WORKSPACE_TEXT_INVALID", "该文档无法预览。", nil) }
            }
        }
    }
    @objc(copyWorkspaceFile:resolver:rejecter:)
    func copyWorkspaceFile(_ id: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let store = self.fileStore, let file = try? store.acquire(id) else { reject("WORKSPACE_FILE_CLOSED", "文件已关闭。", nil); return }
            DispatchQueue.global(qos: .userInitiated).async {
                defer { store.finish(id) }
                do { resolve(try store.importDownloadedFile(file.url, name: file.name, type: file.type).metadata) }
                catch { reject("WORKSPACE_FILE_COPY_FAILED", "文件无法添加，请重试。", nil) }
            }
        }
    }
    @objc(readWorkspaceImage:resolver:rejecter:)
    func readWorkspaceImage(_ id: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let store = self.fileStore else { reject("WORKSPACE_IMAGE_CLOSED", "图片已关闭。", nil); return }
            DispatchQueue.global(qos: .userInitiated).async {
                do { resolve(try store.readImageData(id)) }
                catch { reject("WORKSPACE_IMAGE_INVALID", "图片无法读取。", nil) }
            }
        }
    }
    @objc(exportFile:resolver:rejecter:)
    func exportFile(_ id: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        exportFiles([id] as NSArray, resolver: resolve, rejecter: reject)
    }
    @objc(exportFiles:resolver:rejecter:)
    func exportFiles(_ ids: NSArray, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard !self.exportingFile, let store = self.fileStore, let identifiers = ids as? [String], !identifiers.isEmpty, Set(identifiers).count == identifiers.count else { reject("FILE_EXPORT_UNAVAILABLE", "文件导出暂时不可用。", nil); return }
            var acquired: [NativePickedFile] = []
            do { for id in identifiers { acquired.append(try store.acquire(id)) } }
            catch { for file in acquired { store.finish(file.id) }; reject("FILE_EXPORT_UNAVAILABLE", "文件导出暂时不可用。", nil); return }
            let files = acquired
            self.exportingFile = true
            DispatchQueue.global(qos: .userInitiated).async {
                var copies: [NativeWorkspaceExportCopy] = []
                do {
                    for file in files { copies.append(try NativeWorkspaceExportCopy.make(file: file)) }
                    let exports = copies
                    DispatchQueue.main.async {
                        guard let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first(where: { $0.activationState == .foregroundActive }), var presenter = scene.windows.first(where: { $0.isKeyWindow })?.rootViewController else {
                            for copy in exports { copy.remove() }; for file in files { store.finish(file.id) }; self.exportingFile = false; reject("FILE_EXPORT_UNAVAILABLE", "文件导出暂时不可用。", nil); return
                        }
                        while let presented = presenter.presentedViewController { presenter = presented }
                        let activity = UIActivityViewController(activityItems: exports.map { $0.url }, applicationActivities: nil)
                        activity.popoverPresentationController?.sourceView = presenter.view
                        activity.popoverPresentationController?.sourceRect = CGRect(x: presenter.view.bounds.midX, y: presenter.view.bounds.midY, width: 1, height: 1)
                        activity.completionWithItemsHandler = { _, completed, _, error in
                            for copy in exports { copy.remove() }; for file in files { store.finish(file.id) }; self.exportingFile = false
                            if error != nil { reject("FILE_EXPORT_FAILED", "文件导出失败，请重试。", nil) } else { resolve(["completed": completed]) }
                        }
                        presenter.present(activity, animated: true)
                    }
                } catch {
                    for copy in copies { copy.remove() }; for file in files { store.finish(file.id) }
                    DispatchQueue.main.async { self.exportingFile = false; reject("FILE_EXPORT_FAILED", "文件导出失败，请重试。", nil) }
                }
            }
        }
    }
    @objc(copyText:resolver:rejecter:)
    func copyText(_ text: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async { UIPasteboard.general.string = text; resolve(nil) }
    }
    @objc(openRequest:resolver:rejecter:)
    func openRequest(_ options: NSDictionary, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        logger.info("Local HTTP requested")
        DispatchQueue.main.async {
            guard let origin = self.origin, let request = try? NativeUploadRequest.local(origin: origin, options: options) else {
                reject("HTTP_ORIGIN_INVALID", "请求地址无效。", nil); return
            }
            let id = options["id"] as? String ?? UUID().uuidString
            guard !id.isEmpty, self.requests[id] == nil, !self.preparingUploads.contains(id) else {
                reject("HTTP_REQUEST_ID_INVALID", "请求标识无效。", nil); return
            }
            let response = NativeHTTPResponse(request: request, resolve: { status in
                self.logger.info("Local HTTP head status=\(status, privacy: .public) id=\(id, privacy: .public)")
                resolve(["id": id, "status": status, "headers": self.requests[id]?.readableHeaders ?? [:]])
            }, reject: { code, message, error in
                self.requests.removeValue(forKey: id); reject(code, message, error)
            })
            self.requests[id] = response
            self.logger.info("Local HTTP opened id=\(id, privacy: .public)")
            response.start()
        }
    }
    @objc(readResponse:resolver:rejecter:)
    func readResponse(_ id: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let response = self.requests[id] else { reject("HTTP_RESPONSE_CLOSED", "连接已关闭。", nil); return }
            response.read(resolve: { value in
                if (value as? [String: Any])?["done"] as? Bool == true { self.logger.info("Local HTTP completed id=\(id, privacy: .public)") }
                if (value as? [String: Any])?["done"] as? Bool == true { self.requests.removeValue(forKey: id) }
                resolve(value)
            }, reject: { code, message, error in self.requests.removeValue(forKey: id); reject(code, message, error) })
        }
    }
    @objc(cancelRequest:)
    func cancelRequest(_ id: String) { DispatchQueue.main.async {
        if self.preparingUploads.contains(id) { self.cancelledUploads.insert(id) }
        if let response = self.requests.removeValue(forKey: id) {
            self.logger.info("Local HTTP cancelled id=\(id, privacy: .public)")
            response.cancel()
        }
    } }
    @objc(pickFiles:resolver:rejecter:)
    func pickFiles(_ options: NSDictionary, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard self.filePicker == nil, let max = options["maxBytes"] as? NSNumber, max.doubleValue > 0,
                  max.doubleValue <= 9_007_199_254_740_991, max.doubleValue.rounded() == max.doubleValue,
                  let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first(where: { $0.activationState == .foregroundActive }),
                  var presenter = scene.windows.first(where: { $0.isKeyWindow })?.rootViewController else { reject("FILE_PICK_UNAVAILABLE", "文件选择暂时不可用。", nil); return }
            while let presented = presenter.presentedViewController { presenter = presented }
            do {
                if self.fileStore == nil { self.fileStore = try NativePickedFileStore() }
                let picker = NativeFilePicker(store: self.fileStore!, maxBytes: max.intValue, directory: options["directory"] as? Bool ?? false) { [weak self] result in
                    self?.filePicker = nil
                    switch result { case .success(let selection): resolve(selection); case .failure(let error): reject("FILE_PICK_FAILED", "文件读取失败，请重试。", error) }
                }
                self.filePicker = picker; picker.present(from: presenter)
            } catch { reject("FILE_PICK_FAILED", "文件读取失败，请重试。", error) }
        }
    }
    @objc(releaseFiles:)
    func releaseFiles(_ ids: [String]) { DispatchQueue.main.async { ids.forEach { self.fileStore?.release($0) } } }
    @objc(importSketch:resolver:rejecter:)
    func importSketch(_ options: NSDictionary, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let base64 = options["base64"] as? String, let name = options["name"] as? String,
                  let max = options["maxBytes"] as? NSNumber, max.doubleValue > 0,
                  max.doubleValue <= 9_007_199_254_740_991, max.doubleValue.rounded() == max.doubleValue else {
                reject("SKETCH_FILE_INVALID", "草图文件无效。", nil); return
            }
            do {
                if self.fileStore == nil { self.fileStore = try NativePickedFileStore() }
                let store = self.fileStore!
                DispatchQueue.global(qos: .userInitiated).async {
                    do { let file = try store.importSketch(base64: base64, name: name, maxBytes: max.intValue); DispatchQueue.main.async { resolve(file.metadata) } }
                    catch { DispatchQueue.main.async { reject("SKETCH_FILE_INVALID", "草图文件无法读取，请重试。", error) } }
                }
            } catch { reject("SKETCH_FILE_INVALID", "草图文件无法读取，请重试。", error) }
        }
    }
    @objc(openFileUpload:resolver:rejecter:)
    func openFileUpload(_ options: NSDictionary, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard let id = options["id"] as? String, !id.isEmpty, self.requests[id] == nil, !self.preparingUploads.contains(id),
                  let store = self.fileStore else { reject("FILE_UPLOAD_INVALID", "上传文件无效。", nil); return }
            var files: [NativePickedFile] = []
            do {
                let ids = (options["fileIds"] as? [String]) ?? (options["fileId"] as? String).map { [$0] } ?? []
                guard !ids.isEmpty, Set(ids).count == ids.count else { throw NativeFileError.invalidFile }
                for fileId in ids { files.append(try store.acquire(fileId)) }
                let acquired = files
                let file = files[0]
                self.preparingUploads.insert(id)
                let origin = self.origin
                DispatchQueue.global(qos: .userInitiated).async {
                    var multipart: NativeMultipartFile?
                    do {
                        let direct = options["url"] != nil
                        var request: URLRequest
                        let body: URL
                        if direct { guard acquired.count == 1 else { throw NativeFileError.invalidFile }; request = try NativeUploadRequest.direct(options: options); body = file.url }
                        else {
                            guard let origin, let path = options["path"] as? String,
                                  ["/api/storage/upload", "/api/workspace/files"].contains(path) else { throw NativeFileError.invalidFile }
                            request = try NativeUploadRequest.local(origin: origin, options: options)
                            request.httpMethod = "POST"; request.httpBody = nil
                            guard path == "/api/workspace/files" || acquired.count == 1 else { throw NativeFileError.invalidFile }
                            if options["fileIds"] != nil {
                                multipart = try NativeMultipartFile.make(files: acquired, relativePaths: options["relativePaths"] as? [String], fields: options["fields"] as? [String: String] ?? [:])
                            } else {
                                multipart = try NativeMultipartFile.make(file: file, filename: options["filename"] as? String ?? file.name, fields: options["fields"] as? [String: String] ?? [:])
                            }
                            body = multipart!.url; request.setValue(multipart!.contentType, forHTTPHeaderField: "Content-Type")
                        }
                        DispatchQueue.main.async {
                            self.preparingUploads.remove(id)
                            guard self.cancelledUploads.remove(id) == nil else { multipart?.remove(); acquired.forEach { store.finish($0.id) }; reject("HTTP_ABORTED", "上传已取消。", nil); return }
                            guard self.requests[id] == nil else { multipart?.remove(); acquired.forEach { store.finish($0.id) }; reject("FILE_UPLOAD_INVALID", "上传标识重复。", nil); return }
                            let response = NativeHTTPResponse(request: request, uploadFile: body, cookies: !direct, progress: { sent, total in
                                if self.observing && total > 0 { self.sendEvent(withName: "InkUploadProgress", body: ["id": id, "progress": Int((Double(sent) / Double(total) * 100).rounded())]) }
                            }, close: { multipart?.remove(); acquired.forEach { store.finish($0.id) } }, resolve: { status in resolve(["id": id, "status": status, "headers": self.requests[id]?.readableHeaders ?? [:]]) }, reject: { code, message, error in
                                self.requests.removeValue(forKey: id); reject(code, message, error)
                            })
                            self.requests[id] = response; response.start()
                        }
                    } catch { multipart?.remove(); acquired.forEach { store.finish($0.id) }; DispatchQueue.main.async {
                        self.preparingUploads.remove(id); self.cancelledUploads.remove(id)
                        reject("FILE_UPLOAD_FAILED", "文件上传失败，请重试。", error)
                    } }
                }
            } catch { files.forEach { store.finish($0.id) }; reject("FILE_UPLOAD_INVALID", "上传文件已关闭。", error) }
        }
    }
    @objc(presentMcpAuthorization:resolver:rejecter:)
    func presentMcpAuthorization(_ options: NSDictionary, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard self.mcpAuthorization == nil, self.login == nil,
                  let id = options["operationId"] as? String, !id.isEmpty,
                  let raw = options["authorizationUrl"] as? String,
                  let configured = Bundle.main.object(forInfoDictionaryKey: "InkMcpOAuthCallbackURI") as? String,
                  let callback = URL(string: configured), let scheme = callback.scheme,
                  let authorization = NativeMcpOAuthCallback.authorizationURL(raw, callback: callback),
                  let types = Bundle.main.object(forInfoDictionaryKey: "CFBundleURLTypes") as? [[String: Any]],
                  types.flatMap({ $0["CFBundleURLSchemes"] as? [String] ?? [] }).contains(scheme),
                  let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first(where: { $0.activationState == .foregroundActive }),
                  let anchor = scene.windows.first(where: { $0.isKeyWindow }) else {
                reject("MCP_AUTH_UNAVAILABLE", "资源授权页面暂时无法打开，请检查回调配置。", nil); return
            }
            let completion: ASWebAuthenticationSession.CompletionHandler = { [weak self] url, error in
                DispatchQueue.main.async {
                    guard let self, self.mcpAuthorizationID == id else { return }
                    self.mcpAuthorization = nil; self.mcpAuthorizationID = nil
                    self.mcpAuthorizationReject = nil; self.mcpAuthorizationAnchor = nil
                    if let url, error == nil, NativeMcpOAuthCallback.matches(url, callback: callback) { resolve(url.absoluteString) }
                    else if (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin { reject("MCP_AUTH_CANCELLED", "资源授权已取消。", nil) }
                    else { reject("MCP_AUTH_FAILED", "资源授权未完成，请重试。", nil) }
                }
            }
            let session: ASWebAuthenticationSession
            if #available(iOS 17.4, *) { session = ASWebAuthenticationSession(url: authorization, callback: .customScheme(scheme), completionHandler: completion) }
            else { session = ASWebAuthenticationSession(url: authorization, callbackURLScheme: scheme, completionHandler: completion) }
            self.mcpAuthorization = session; self.mcpAuthorizationID = id
            self.mcpAuthorizationReject = reject; self.mcpAuthorizationAnchor = anchor
            session.presentationContextProvider = self
            if !session.start() {
                self.mcpAuthorization = nil; self.mcpAuthorizationID = nil
                self.mcpAuthorizationReject = nil; self.mcpAuthorizationAnchor = nil
                reject("MCP_AUTH_UNAVAILABLE", "资源授权页面暂时无法打开，请重试。", nil)
            }
        }
    }
    @objc(cancelMcpAuthorization:)
    func cancelMcpAuthorization(_ id: String) {
        DispatchQueue.main.async {
            guard self.mcpAuthorizationID == id else { return }
            let session = self.mcpAuthorization, reject = self.mcpAuthorizationReject
            self.mcpAuthorization = nil; self.mcpAuthorizationID = nil
            self.mcpAuthorizationReject = nil; self.mcpAuthorizationAnchor = nil
            session?.cancel(); reject?("MCP_AUTH_CANCELLED", "资源授权已取消。", nil)
        }
    }
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        mcpAuthorizationAnchor ?? ASPresentationAnchor()
    }
    @objc(presentLogin:rejecter:)
    func presentLogin(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async {
            guard self.login == nil, self.mcpAuthorization == nil, let origin = self.origin,
                  let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first(where: { $0.activationState == .foregroundActive }),
                  var presenter = scene.windows.first(where: { $0.isKeyWindow })?.rootViewController else {
                reject("LOGIN_UNAVAILABLE", "登录页面暂时无法打开。", nil); return
            }
            while let presented = presenter.presentedViewController { presenter = presented }
            let controller = MobileHostViewController(), navigation = UINavigationController()
            controller.reactNativeHost = true
            controller.edgesForExtendedLayout = []
            navigation.setViewControllers([controller], animated: false)
            let language = UserDefaults.standard.string(forKey: "ink-language") ?? Locale.preferredLanguages.first ?? "en"
            controller.title = language.hasPrefix("zh") ? "登录" : "Login"
            let close = UIBarButtonItem(title: language.hasPrefix("zh") ? "关闭" : "Close", style: .plain, target: nil, action: nil)
            close.primaryAction = UIAction { [weak self, weak navigation] _ in
                guard let self, let navigation, self.login === navigation else { return }
                self.finishLogin(authenticated: false)
            }
            close.accessibilityIdentifier = "ink-login-close"
            controller.navigationItem.leftBarButtonItem = close
            let appearance = UINavigationBarAppearance()
            appearance.configureWithOpaqueBackground(); appearance.backgroundColor = MobileHostViewController.initialBackground
            navigation.navigationBar.standardAppearance = appearance; navigation.navigationBar.scrollEdgeAppearance = appearance
            navigation.navigationBar.tintColor = .label
            controller.appearanceDidChange = { [weak navigation] background, style in
                let appearance = UINavigationBarAppearance(); appearance.configureWithOpaqueBackground(); appearance.backgroundColor = background
                navigation?.navigationBar.standardAppearance = appearance; navigation?.navigationBar.scrollEdgeAppearance = appearance
                navigation?.overrideUserInterfaceStyle = style
            }
            self.login = navigation; self.loginResolve = resolve; self.loginReject = reject; self.loginFinishing = false
            let probe = NativeLoginSessionProbe(origin: origin) { [weak self, weak navigation] in
                guard let self, let navigation, self.login === navigation else { return }
                self.finishLogin(authenticated: true)
            }
            self.loginProbe = probe
            controller.hostStateDidChange = { state in
                if state["authenticated"] as? Bool == true || state["loading"] as? Bool == false { probe.check() }
            }
            presenter.present(navigation, animated: true) { probe.check() }
            navigation.presentationController?.delegate = self
        }
    }
    private func finishLogin(authenticated: Bool, alreadyDismissed: Bool = false) {
        guard let navigation = login, !loginFinishing else { return }
        loginFinishing = true
        loginProbe?.stop(); loginProbe = nil
        (navigation.viewControllers.first as? MobileHostViewController)?.hostStateDidChange = nil
        (navigation.viewControllers.first as? MobileHostViewController)?.appearanceDidChange = nil
        navigation.viewControllers.first?.navigationItem.leftBarButtonItem?.isEnabled = false
        let resolve = loginResolve, reject = loginReject
        loginResolve = nil; loginReject = nil
        let settled = { [weak self, weak navigation] in
            guard let self, self.login === navigation else { return }
            self.login = nil; self.loginFinishing = false
            if authenticated { resolve?(nil) } else { reject?("LOGIN_CANCELLED", "登录已取消。", nil) }
        }
        if alreadyDismissed { settled() } else { navigation.dismiss(animated: true, completion: settled) }
    }
    func presentationControllerDidDismiss(_ presentationController: UIPresentationController) {
        guard presentationController.presentedViewController === login else { return }
        finishLogin(authenticated: false, alreadyDismissed: true)
    }
    deinit { mcpAuthorization?.cancel(); requests.values.forEach { $0.cancel() } }
}

// Cookie changes complete the original callback independently of a heavy business page render.
// Only the existing BFF session endpoint can confirm authentication.
final class NativeLoginSessionProbe: NSObject, WKHTTPCookieStoreObserver {
    private let origin: URL
    private let store = WKWebsiteDataStore.default().httpCookieStore
    private let completed: () -> Void
    private var stopped = false
    private var checking = false
    private var changed = false
    private var task: URLSessionDataTask?
    init(origin: URL, completed: @escaping () -> Void) {
        self.origin = origin; self.completed = completed
        super.init(); store.add(self)
    }
    func cookiesDidChange(in cookieStore: WKHTTPCookieStore) { check() }
    func check() {
        guard !stopped else { return }
        if checking { changed = true; return }
        checking = true
        store.getAllCookies { [weak self] cookies in
            guard let self, !self.stopped else { return }
            let matches: (HTTPCookie) -> Bool = { $0.domain.trimmingCharacters(in: CharacterSet(charactersIn: ".")) == self.origin.host }
            for cookie in HTTPCookieStorage.shared.cookies ?? [] where matches(cookie) { HTTPCookieStorage.shared.deleteCookie(cookie) }
            for cookie in cookies where matches(cookie) { HTTPCookieStorage.shared.setCookie(cookie) }
            var request = URLRequest(url: URL(string: "/auth/session", relativeTo: self.origin)!.absoluteURL)
            request.cachePolicy = .reloadIgnoringLocalCacheData
            self.task = URLSession.shared.dataTask(with: request) { data, response, _ in
                DispatchQueue.main.async {
                    guard !self.stopped else { return }
                    self.checking = false
                    let status = (response as? HTTPURLResponse)?.statusCode ?? 0
                    Logger(subsystem: "com.inkmemory.mobile", category: "ReactNativeRuntime").info("Web login session status=\(status, privacy: .public)")
                    if Self.isAuthenticated(data: data, response: response, origin: self.origin) { self.stop(); self.completed() }
                    else if self.changed { self.changed = false; self.check() }
                }
            }
            self.task?.resume()
        }
    }
    static func isAuthenticated(data: Data?, response: URLResponse?, origin: URL) -> Bool {
        guard let response = response as? HTTPURLResponse, response.statusCode == 200, let url = response.url,
              url.scheme == origin.scheme, url.host == origin.host, url.port == origin.port, url.path == "/auth/session",
              let data, let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let user = value["user"] as? [String: Any], let id = user["id"] as? String,
              id.range(of: "^[1-9][0-9]{0,18}$", options: .regularExpression) != nil,
              let csrf = value["csrf_token"] as? String, csrf.range(of: "^[A-Za-z0-9_-]{43}$", options: .regularExpression) != nil else { return false }
        return true
    }
    func stop() { guard !stopped else { return }; stopped = true; task?.cancel(); task = nil; store.remove(self) }
}

// Transports bytes; the original DTO, SSE reducer and Stop implementation own business semantics.
enum NativeMcpOAuthCallback {
    static func matches(_ url: URL, callback: URL) -> Bool {
        guard let value = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let expected = URLComponents(url: callback, resolvingAgainstBaseURL: false),
              expected.query == nil, expected.fragment == nil, expected.user == nil, expected.password == nil,
              let scheme = expected.scheme, scheme.contains("."), !["http", "https"].contains(scheme),
              expected.percentEncodedPath.hasPrefix("/"), value.user == nil, value.password == nil, value.fragment == nil else { return false }
        return value.scheme?.lowercased() == expected.scheme?.lowercased() && value.host?.lowercased() == expected.host?.lowercased() && value.port == expected.port && value.percentEncodedPath == expected.percentEncodedPath
    }
    static func authorizationURL(_ raw: String, callback: URL) -> URL? {
        guard let value = URLComponents(string: raw), let url = value.url,
              ["http", "https"].contains(value.scheme ?? ""), value.host != nil,
              value.user == nil, value.password == nil, value.fragment == nil else { return nil }
        let redirects = value.queryItems?.filter { $0.name == "redirect_uri" } ?? []
        guard redirects.count == 1, let rawCallback = redirects.first?.value, let supplied = URL(string: rawCallback),
              supplied.query == nil, supplied.fragment == nil, matches(supplied, callback: callback) else { return nil }
        return url
    }
}

final class NativeHTTPResponse: NSObject, URLSessionDataDelegate {
    private(set) var readableHeaders: [String: String] = [:]
    private let request: URLRequest
    private var head: ((Int) -> Void)?
    private var headReject: RCTPromiseRejectBlock?
    private var reader: RCTPromiseResolveBlock?
    private var readerReject: RCTPromiseRejectBlock?
    private var buffer = Data()
    private var finished = false
    private var failure: Error?
    private var suspended = false
    private var task: URLSessionDataTask?
    private var session: URLSession?
    private let uploadFile: URL?
    private let cookies: Bool
    private let progress: ((Int64, Int64) -> Void)?
    private var close: (() -> Void)?
    private let configuration: URLSessionConfiguration
    init(request: URLRequest, uploadFile: URL? = nil, cookies: Bool = true, configuration: URLSessionConfiguration = .default, progress: ((Int64, Int64) -> Void)? = nil, close: (() -> Void)? = nil, resolve: @escaping (Int) -> Void, reject: @escaping RCTPromiseRejectBlock) {
        self.request = request; self.head = resolve; self.headReject = reject
        self.uploadFile = uploadFile; self.cookies = cookies; self.configuration = configuration; self.progress = progress; self.close = close
    }
    func start() {
        configuration.httpCookieStorage = cookies ? .shared : nil; configuration.httpShouldSetCookies = cookies
        if !cookies { configuration.urlCredentialStorage = nil }
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        session = URLSession(configuration: configuration, delegate: self, delegateQueue: .main)
        if let uploadFile { task = session?.uploadTask(with: request, fromFile: uploadFile) }
        else { task = session?.dataTask(with: request) }
        task?.resume()
    }
    func read(resolve: @escaping RCTPromiseResolveBlock, reject: @escaping RCTPromiseRejectBlock) {
        guard reader == nil else { reject("HTTP_CONCURRENT_READ", "连接正在读取。", nil); return }
        reader = resolve; readerReject = reject; flush()
        if suspended && reader != nil { suspended = false; task?.resume() }
    }
    private func flush() {
        guard let reader else { return }
        if let failure { readerReject?("HTTP_FAILED", "连接已中断。", failure); clearReader(); return }
        // Keep a split UTF-8 scalar between data callbacks.
        for suffix in 0...min(3, buffer.count) {
            let count = buffer.count - suffix
            guard count > 0 || finished else { continue }
            if let text = String(data: buffer.prefix(count), encoding: .utf8), !finished || suffix == 0 {
                buffer.removeFirst(count)
                reader(["text": text, "done": finished && buffer.isEmpty]); clearReader(); return
            }
        }
        if finished { readerReject?("HTTP_UTF8_INVALID", "响应编码无效。", nil); clearReader() }
    }
    private func clearReader() { reader = nil; readerReject = nil }
    private func closeResources() { let cleanup = close; close = nil; cleanup?() }
    func cancel() { task?.cancel(); session?.invalidateAndCancel(); failure = URLError(.cancelled); closeResources(); flush() }
    func urlSession(_ session: URLSession, task: URLSessionTask, didSendBodyData bytesSent: Int64, totalBytesSent: Int64, totalBytesExpectedToSend: Int64) { progress?(totalBytesSent, totalBytesExpectedToSend) }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse, completionHandler: @escaping (URLSession.ResponseDisposition) -> Void) {
        guard let response = response as? HTTPURLResponse else { completionHandler(.cancel); return }
        for name in ["Content-Type", "Retry-After"] {
            if let value = response.value(forHTTPHeaderField: name) { readableHeaders[name.lowercased()] = value }
        }
        head?(response.statusCode); head = nil; headReject = nil; completionHandler(.allow)
    }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        buffer.append(data); flush()
        if reader == nil && !buffer.isEmpty && !suspended { suspended = true; dataTask.suspend() }
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        finished = true; failure = error
        closeResources()
        if let reject = headReject { reject("HTTP_FAILED", "连接未建立。", error); headReject = nil; head = nil }
        flush(); session.finishTasksAndInvalidate()
    }
}
