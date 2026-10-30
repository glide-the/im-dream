// [Sync] 2026-10-28: add read-only native URLSession acceptance for an existing normal-login session and selected callable model; no browser mutation, credential output or model calls.
// [Input] The packaged WKWebView; real business acceptance additionally requires explicit credentials and expected reply.
// [Output] Separate provider-free local page proof and credential-gated normal Web login/Chat acceptance.
// [Pos] Packaged Web journey harness; original authentication and business interfaces stay unchanged.
// [Sync] 2026-10-28: archive the retired InkBusinessSurface-only test body; current RN full-page/business acceptance remains pending.
// [Sync] 2026-10-26: observe original Dream viewport geometry after manual navigation, without submitting business data.
// [Sync] 2026-10-25: verify packaged login, session establishment, Chat submission, and the expected terminal reply.
// [Sync] 2026-10-25: separately qualify original React hydration and unchanged login failures through application-owned Next without credentials.
// [Sync] 2026-10-25: verify normal configured login actions separately from the unchanged missing-configuration response.
// [Sync] 2026-10-25: qualify the original callable-model catalog through the normal authenticated Web session.
// [Sync] 2026-10-25: observe one manually submitted original Chat response without logging its body or credentials.
// [Sync] 2026-10-25: terminate the observer promptly when the original message failure feedback becomes visible.
// [Sync] 2026-10-25: capture only coroutine/thread function names on an actual terminal-state timeout.
// [Sync] 2026-10-25: require a new expected reply after the observed POST; existing history cannot satisfy resume acceptance.
// [Sync] 2026-10-25: qualify original BFF capabilities through WKWebView separately from account/model acceptance.
// [Sync] 2026-10-25: record bounded recovery reads on submission/terminal timeouts without request identities or bodies.
// [Sync] 2026-10-25: distinguish account-check HTTP failures from a mismatched validated account without logging identity values.
// [Sync] 2026-10-25: diagnose original React bootstrap through bounded script/error/auth-read metadata without credentials or bodies.
// [Sync] 2026-10-25: diagnose three original owned-thread GETs through the authenticated WebView using closed response metadata.
// [Sync] 2026-10-25: trace original Python HTTP phases within owned GET and manual Chat diagnostics, excluding identities and content.
// [Sync] 2026-10-25: observe original ASGI finish/EOF and browser reader completion without logging streamed content.
// [Sync] 2026-10-25: record a manually clicked original Stop receipt against the observed submission identity.
// [Sync] 2026-10-25: retain the observation until a submitted Stop finishes before accepting the visible terminal state.
// [Sync] 2026-10-25: add an explicit acceptance method that clicks the original Stop once when a new first reply renders before EOF.
// [Sync] 2026-10-25: use the original chat-input ID and both existing UI translations when observing send, stop and recovery.
// [Sync] 2026-10-26: observe original grant renewal diagnostics for one explicit Thread during a long manually submitted turn.
// [Sync] 2026-10-26: observe one explicitly identified accepted Dream confirmation, original HTTP phases and coordinator frames without submitting business content.
// [Sync] 2026-10-26: reserve confirmation diagnostics for relevant HTTP operations and exact-message Factory frames; allow fifteen minutes for the original manual journey.
// [Sync] 2026-10-27: verify the actual RN root and persistent WebKit identity across supported native navigation requests.

import UIKit
import WebKit
import XCTest
@testable import InkMemory

@MainActor
final class PhysicalBusinessJourneyTests: XCTestCase {
    // Read-only acceptance after the human-operated original login; no session injection or model call.
    func testNativeSessionAndSelectedModelRead() async throws {
        XCTAssertEqual(Bundle.main.bundleIdentifier, "com.inkmemory.uiparity")
        guard let email = ProcessInfo.processInfo.environment["INK_DREAM_TEST_EMAIL"], !email.isEmpty else {
            throw XCTSkip("The expected product account is required.")
        }
        let facts: [String: Any] = try await withCheckedThrowingContinuation { continuation in
            EmbeddedDreamBackend.shared.start { continuation.resume(with: $0) }
        }
        let origin = try XCTUnwrap((facts["localWebOrigin"] as? String).flatMap(URL.init(string:)))
        func read(_ path: String, headers: [String: String] = [:]) async throws -> [String: Any] {
            var request = try NativeUploadRequest.local(origin: origin, options: ["path": path, "method": "GET", "headers": headers] as NSDictionary)
            request.cachePolicy = .reloadIgnoringLocalCacheData
            let (data, response) = try await URLSession.shared.data(for: request)
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            XCTAssertEqual(status, 200, "Native public GET must succeed")
            guard status == 200 else { throw NSError(domain: "InkMemory.NativeRead", code: status) }
            return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        }
        let session = try await read("/auth/session")
        let matched = (session["user"] as? [String: Any])?["email"] as? String == email
        XCTAssertTrue(matched, "The existing normal-login account must match")
        let csrf = try XCTUnwrap(session["csrf_token"] as? String)
        XCTAssertFalse(csrf.isEmpty)
        guard matched, !csrf.isEmpty else { return }
        let headers = ["x-ink-csrf": csrf]
        let configuration = try await read("/api/system-config", headers: headers)
        let config = configuration["data"] as? [String: Any] ?? configuration
        let catalog = try await read("/api/gateway/models", headers: headers)
        let saved = config["model"] as? String
        let model = try XCTUnwrap((saved?.isEmpty == false ? saved : catalog["defaultModelAlias"] as? String))
        XCTAssertNotNil(model.range(of: "^[A-Za-z0-9._:-]{1,128}$", options: .regularExpression))
        let callable = (catalog["data"] as? [[String: Any]] ?? []).contains { ($0["modelAlias"] as? String) == model && ($0["callable"] as? Bool) == true }
        XCTAssertTrue(callable, "The original selected model must be callable")
        guard callable, model.range(of: "^[A-Za-z0-9._:-]{1,128}$", options: .regularExpression) != nil else { return }
        print("IOS_RN_NATIVE_READ_PROOF accountMatched=true session=200 csrf=true config=200 models=200 modelAlias=\(model) callable=true pid=\(ProcessInfo.processInfo.processIdentifier) modelCalls=0")
    }

    func testReactNativeAccountSwitchAndNormalLogin() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard let email = environment["INK_DREAM_TEST_EMAIL"], !email.isEmpty,
              let password = environment["INK_DREAM_TEST_PASSWORD"], !password.isEmpty else {
            throw XCTSkip("Explicit normal-login credentials were not supplied.")
        }
        let webView = try await waitForWebView(timeout: 120)
        try await waitForJavaScript(webView, timeout: 120) {
            "return Boolean(document.querySelector('#chat-input') || document.querySelector('input[name=password]'));"
        }
        let existing = try await evaluate(webView, """
            const response = await fetch('/auth/session', {credentials:'same-origin', cache:'no-store'});
            return response.ok && (await response.json()).user?.email === args.email;
            """, arguments: ["args": ["email": email]]) as? Bool
        if existing != true {
            _ = try await evaluate(webView, "window.dispatchEvent(new Event('ink:host-logout')); return true;", arguments: [:])
            try await waitForJavaScript(webView, timeout: 60) {
                "return Boolean(document.querySelector('input[name=email]') && document.querySelector('input[name=password]'));"
            }
        }
        _ = try await logIn(email: email, password: password)
        print("IOS_RN_NORMAL_LOGIN_PROOF accountMatched=true originalWebForm=true credentialsLogged=false modelCalls=0")
    }

    // Historical InkBusinessSurface route test retained in legacy/ios-tests/PersistentBusinessWebViewTest-20261028.swift.txt.
    // Current RN page/account/business acceptance is recorded separately.

    func testObserveOriginalDreamViewport() async throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let webView = try await waitForWebView(timeout: 120)
        try await waitForJavaScript(webView, timeout: 180) {
            "return window.__INK_FRONTEND_VERSION__ === 'next-phase1' && Boolean(document.querySelector('#chat-input'));"
        }
        print("IOS_ORIGINAL_DREAM_VIEWPORT_READY modelCalls=0 manualNavigation=true")
        try await waitForJavaScript(webView, timeout: 180) {
            "return Boolean(document.querySelector('.story-workspace-collaboration__focus-layer'));"
        }
        let result = try await evaluate(webView, """
            const selectors = ['.story-workspace-layout__main', '.story-workspace-collaboration',
              '.story-workspace-collaboration__surface', '.story-workspace-collaboration__focus-layer',
              '.story-workspace-collaboration__focus'];
            const rows = selectors.flatMap(selector => {
              const element = document.querySelector(selector); if (!element) return [];
              const rect = element.getBoundingClientRect(); const style = getComputedStyle(element);
              const overflow = ['visible','hidden','auto','scroll','clip','overlay'].includes(style.overflowY) ? style.overflowY : 'other';
              return [{selector, clientHeight:element.clientHeight, scrollHeight:element.scrollHeight,
                scrollTop:Math.round(element.scrollTop), top:Math.round(rect.top), bottom:Math.round(rect.bottom), overflow}];
            });
            return {height:innerHeight, width:innerWidth, rows, scrollable:rows.some(row =>
              row.clientHeight > 0 && row.scrollHeight > row.clientHeight &&
              ['auto','scroll','overlay'].includes(row.overflow) && row.top >= 0 && row.bottom <= innerHeight + 1)};
            """, arguments: [:]) as? [String: Any] ?? [:]
        let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print("IOS_ORIGINAL_DREAM_VIEWPORT \(String(decoding: data, as: UTF8.self))")
        XCTAssertEqual(result["scrollable"] as? Bool, true)
    }

    func testObserveAcceptedDreamConfirmationRecovery() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard let email = environment["INK_DREAM_TEST_EMAIL"], !email.isEmpty,
              let thread = environment["INK_DREAM_TEST_THREAD_ID"], UUID(uuidString: thread) != nil,
              let run = environment["INK_DREAM_TEST_RUN_ID"], run.range(of: "^run_[0-9a-f]{32}$", options: .regularExpression) != nil,
              let message = environment["INK_DREAM_TEST_MESSAGE_ID"], message.range(of: "^dream_confirm_[0-9a-f]{64}$", options: .regularExpression) != nil else {
            throw XCTSkip("The existing account, Thread, Run and accepted message were not supplied.")
        }
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let webView = try await waitForWebView(timeout: 120)
        try await waitForJavaScript(webView, timeout: 180) {
            "return Boolean(document.querySelector('#chat-input'));"
        }
        let account = try await evaluate(webView, """
            const response = await fetch('/auth/session', {credentials:'same-origin', cache:'no-store'});
            return {status:response.status, matched:response.ok && (await response.json()).user?.email === args.email};
            """, arguments: ["args": ["email": email]]) as? [String: Any]
        XCTAssertEqual(account?["status"] as? Int, 200)
        XCTAssertEqual(account?["matched"] as? Bool, true)
        guard account?["matched"] as? Bool == true else { return }
        try installOriginalPythonHTTPTrace(confirmationOnly: true)
        try runEmbeddedPythonQualification("""
            import asyncio, logging
            from mobile_runtime import ios
            from services.deck.story_workflow_application import story_workspace_get_dream_confirmation_coordinator
            _ios_confirmation_errors = []
            class _IOSConfirmationErrorObserver(logging.Handler):
                def emit(self, record):
                    try:
                        if len(_ios_confirmation_errors) >= 8:
                            return
                        error = record.exc_info[1] if record.exc_info else None
                        code = getattr(error, 'code', None)
                        code = code if isinstance(code, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', code) else None
                        frames, trace = [], record.exc_info[2] if record.exc_info else None
                        matched = isinstance(record.args, tuple) and '\(message)' in record.args
                        while trace is not None:
                            request = trace.tb_frame.f_locals.get('request') or trace.tb_frame.f_locals.get('current_request')
                            if request is not None and getattr(request, 'thread_id', None) == '\(thread)' and getattr(request, 'message_id', None) == '\(message)':
                                matched = True
                            if len(frames) < 12:
                                frames.append(dict(function=trace.tb_frame.f_code.co_name, line=trace.tb_lineno))
                            trace = trace.tb_next
                        if matched:
                            _ios_confirmation_errors.append(dict(errorClass=type(error).__name__ if error else None, code=code, frames=frames))
                    except Exception:
                        pass
            _ios_confirmation_error_observer = _IOSConfirmationErrorObserver(level=logging.WARNING)
            _ios_confirmation_loggers = [logging.getLogger(name) for name in (
                'services.story_workspace.dream_confirmation_service', 'services.deck.story_workflow_application',
                'claude_agent.thread_factory', 'claude_agent.service')]
            for logger in _ios_confirmation_loggers:
                logger.addHandler(_ios_confirmation_error_observer)
            async def _ios_confirmation_snapshot():
                coordinator = story_workspace_get_dream_confirmation_coordinator()
                task = coordinator._in_flight.get('\(message)')
                retry = coordinator._retry_state.get('\(message)')
                frames, target_matched = [], None
                if task:
                    coroutine = task.get_coro()
                    frame = getattr(coroutine, 'cr_frame', None)
                    dispatch = frame.f_locals.get('dispatch') if frame else None
                    if dispatch:
                        target_matched = dispatch.thread_id == '\(thread)' and dispatch.metadata.get('story_workspace_run_id') == '\(run)'
                    for _ in range(12):
                        frame = getattr(coroutine, 'cr_frame', None)
                        if frame:
                            frames.append(dict(function=frame.f_code.co_name, line=frame.f_lineno))
                        coroutine = getattr(coroutine, 'cr_await', None)
                        if coroutine is None:
                            break
                turn_frames = []
                for candidate in asyncio.all_tasks():
                    coroutine = candidate.get_coro()
                    frame = getattr(coroutine, 'cr_frame', None)
                    if frame is None or frame.f_code.co_name != '_run_turn_task':
                        continue
                    request = frame.f_locals.get('current_request') or frame.f_locals.get('request')
                    if request is None or getattr(request, 'thread_id', None) != '\(thread)' or getattr(request, 'message_id', None) != '\(message)':
                        continue
                    for _ in range(12):
                        frame = getattr(coroutine, 'cr_frame', None)
                        if frame:
                            turn_frames.append(dict(function=frame.f_code.co_name, line=frame.f_lineno))
                        coroutine = getattr(coroutine, 'cr_await', None)
                        if coroutine is None:
                            break
                    break
                return dict(inFlight=task is not None, done=task.done() if task else None,
                    targetMatched=target_matched, frames=frames, failures=retry.failures if retry else 0,
                    retryRemainingMs=max(0, round((retry.not_before-coordinator._clock())*1000)) if retry else 0,
                    globalScanner=coordinator._loop_task is not None, turnFrames=turn_frames,
                    errors=list(_ios_confirmation_errors))
            """)
        defer {
            try? runEmbeddedPythonQualification("""
                httpx.Client.send = _ios_original_http_send
                for logger in _ios_confirmation_loggers:
                    logger.removeHandler(_ios_confirmation_error_observer)
                """)
        }
        print("IOS_DREAM_CONFIRMATION_OBSERVER_READY accountMatched=true relay=disabled diagnosticOnly=true")
        for _ in 0..<180 {
            try runEmbeddedPythonQualification("""
                snapshot = asyncio.run_coroutine_threadsafe(_ios_confirmation_snapshot(), ios._loop).result(timeout=10)
                print('IOS_DREAM_CONFIRMATION_STATE ' + json.dumps(snapshot), flush=True)
                """)
            try await Task.sleep(for: .seconds(5))
        }
        print("IOS_DREAM_CONFIRMATION_OBSERVER_FINISHED businessCompletionNotAsserted=true")
    }

    func testConfiguredOriginalThreadRecoveryReads() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard let email = environment["INK_DREAM_TEST_EMAIL"], !email.isEmpty,
              let threadId = environment["INK_DREAM_TEST_THREAD_ID"], UUID(uuidString: threadId) != nil else {
            throw XCTSkip("An existing Dream account and owned thread were not supplied.")
        }
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let webView = try await waitForWebView(timeout: 120)
        try await waitForJavaScript(webView, timeout: 180) {
            "return window.__INK_FRONTEND_VERSION__ === 'next-phase1' && Boolean(document.querySelector('#chat-input'));"
        }
        try installOriginalPythonHTTPTrace()
        defer { try? runEmbeddedPythonQualification("httpx.Client.send = _ios_original_http_send") }
        let result = try await evaluate(webView, """
            const started = performance.now();
            const sessionResponse = await fetch('/auth/session', {credentials:'same-origin', cache:'no-store', signal:AbortSignal.timeout(70000)});
            const session = sessionResponse.ok ? await sessionResponse.json() : null;
            const account = {status:sessionResponse.status, matched:session?.user?.email === args.email, elapsedMs:Math.round(performance.now()-started)};
            if (!account.matched || !/^[A-Za-z0-9_-]{43}$/.test(session?.csrf_token ?? '')) return {account, reads:[]};
            const reads = await Promise.all(['messages','status','inputs'].map(async operation => {
              const row = {operation, status:0, code:'none', elapsedMs:0, json:false};
              const readStarted = performance.now();
              try {
                const path = '/api/claude-agent/threads/' + encodeURIComponent(args.thread) + '/' + operation + (operation === 'messages' ? '?limit=20' : '');
                const response = await fetch(path, {credentials:'same-origin', headers:{'x-ink-csrf':session.csrf_token}, signal:AbortSignal.timeout(90000)});
                row.status = response.status;
                let payload;
                try { payload = await response.json(); row.json = true; }
                catch { row.code = 'RESPONSE_JSON_INVALID'; }
                if (!response.ok) {
                  const code = payload?.detail?.error_code ?? payload?.detail?.code ?? payload?.detail;
                  row.code = typeof code === 'string' && /^[A-Z0-9_.-]{1,80}$/.test(code) ? code : 'HTTP_REJECTED';
                } else if (operation === 'messages') {
                  row.threadMatched = payload?.thread?.id === args.thread;
                  row.messageCount = Array.isArray(payload?.messages) ? payload.messages.length : -1;
                  row.pageFields = typeof payload?.has_more === 'boolean' && typeof payload?.unchanged === 'boolean';
                } else if (operation === 'status') {
                  row.running = typeof payload?.running === 'boolean' ? payload.running : null;
                  row.lifecycle = ['idle','running','destroyed','not_found'].includes(payload?.lifecycle) ? payload.lifecycle : 'unknown';
                  row.confirmation = ['known','unknown'].includes(payload?.tool_confirmation_observation) ? payload.tool_confirmation_observation : 'invalid';
                } else {
                  row.entryCount = Array.isArray(payload?.entries) ? payload.entries.length : -1;
                  row.localOwner = typeof payload?.local_owner === 'boolean' ? payload.local_owner : null;
                }
              } catch (error) { row.code = ['AbortError','TimeoutError'].includes(error.name) ? 'REQUEST_TIMEOUT' : 'FETCH_FAILED'; }
              row.elapsedMs = Math.round(performance.now()-readStarted);
              return row;
            }));
            return {account, reads};
            """, arguments: ["args": ["email": email, "thread": threadId]]) as? [String: Any] ?? [:]
        let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print("IOS_ORIGINAL_THREAD_READ_DIAGNOSTICS \(String(decoding: data, as: UTF8.self))")
        let account = result["account"] as? [String: Any]
        XCTAssertEqual(account?["status"] as? Int, 200)
        XCTAssertEqual(account?["matched"] as? Bool, true)
        let reads = result["reads"] as? [[String: Any]] ?? []
        XCTAssertEqual(reads.count, 3)
        XCTAssertTrue(reads.allSatisfy { ($0["status"] as? Int) == 200 && ($0["code"] as? String) == "none" })
    }

    func testOriginalReactBootstrapDiagnostics() async throws {
        let webView = try await waitForWebView(timeout: 120)
        let source = """
        (() => {
        window.__INK_IOS_BOOT_PROBE__ = {errors: [], reads: []};
        const probe = window.__INK_IOS_BOOT_PROBE__;
        const safeName = value => typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(value) ? value : 'Error';
        addEventListener('error', event => { if (probe.errors.length < 8) probe.errors.push({kind:event.target?.tagName === 'SCRIPT' ? 'script-resource' : 'script-error', name:safeName(event.error?.name)}); }, true);
        addEventListener('unhandledrejection', event => { if (probe.errors.length < 8) probe.errors.push({kind:'rejection', name:safeName(event.reason?.name)}); });
        const originalFetch = window.fetch.bind(window);
        window.fetch = async (...args) => {
          const input = args[0];
          const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url, location.href);
          const selected = url.origin === location.origin && ['/auth/session','/auth/options'].includes(url.pathname);
          const row = selected && probe.reads.length < 16 ? {operation:url.pathname === '/auth/session' ? 'session' : 'options', status:0, code:'pending', elapsedMs:0} : null;
          const started = performance.now();
          if (row) probe.reads.push(row);
          try {
            const response = await originalFetch(...args);
            if (row) {row.status=response.status; row.code='none'; row.elapsedMs=Math.round(performance.now()-started);}
            return response;
          } catch(error) {
            if (row) {row.code=safeName(error.name); row.elapsedMs=Math.round(performance.now()-started);}
            throw error;
          }
        };
        })();
        """
        webView.configuration.userContentController.addUserScript(WKUserScript(source: source, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        webView.reload()
        for index in 0..<8 {
            try await Task.sleep(for: .seconds(10))
            let snapshot = try await evaluate(webView, """
            return {index:args.index, ready:document.readyState, originalReact:window.__INK_FRONTEND_VERSION__ === 'next-phase1',
              login:Boolean(document.querySelector('input[name=password]')), chat:Boolean(document.querySelector('#chat-input')),
              retry:Array.from(document.querySelectorAll('button')).some(node=>node.textContent?.trim()==='Try again'),
              scriptCount:document.scripts.length, completedResources:performance.getEntriesByType('resource').length,
              probe:window.__INK_IOS_BOOT_PROBE__ ?? null};
            """, arguments: ["args": ["index": index]]) as? [String: Any] ?? [:]
            let data = try JSONSerialization.data(withJSONObject: snapshot, options: [.sortedKeys])
            print("IOS_ORIGINAL_REACT_BOOTSTRAP \(String(decoding: data, as: UTF8.self))")
            if snapshot["originalReact"] as? Bool == true && (snapshot["login"] as? Bool == true || snapshot["chat"] as? Bool == true) { return }
        }
        XCTFail("Original React bootstrap did not reach its original auth or Chat surface")
    }

    func testConfiguredOriginalBffCapabilitiesTransport() async throws {
        let webView = try await waitForWebView(timeout: 120)
        try await waitForJavaScript(webView, timeout: 120) {
            "return ['localhost', '127.0.0.1', '::1', '[::1]'].includes(location.hostname) && document.readyState === 'complete';"
        }
        let observations = try await evaluate(webView, """
            const observations = [];
            for (let index = 1; index <= 3; index++) {
              const started = performance.now();
              let status = 0, code = 'none';
              try {
                const response = await fetch('/auth/options', {cache: 'no-store', credentials: 'same-origin', signal: AbortSignal.timeout(70000)});
                status = response.status;
                const payload = await response.json();
                if (!response.ok) code = typeof payload.detail === 'string' && /^[A-Z0-9_]+$/.test(payload.detail) ? payload.detail : 'unclassified';
              } catch (error) { code = error.name === 'AbortError' || error.name === 'TimeoutError' ? 'REQUEST_TIMEOUT' : 'FETCH_FAILED'; }
              observations.push({index, status, code, elapsedMs: Math.round(performance.now() - started)});
            }
            return observations;
            """, arguments: [:]) as? [[String: Any]]
        for observation in observations ?? [] {
            let data = try JSONSerialization.data(withJSONObject: observation, options: [.sortedKeys])
            print("IOS_ORIGINAL_BFF_CAPABILITIES_PROBE \(String(decoding: data, as: UTF8.self))")
        }
        XCTAssertEqual(observations?.count, 3)
        XCTAssertTrue(observations?.allSatisfy { ($0["status"] as? Int) == 200 && ($0["code"] as? String) == "none" } == true)
    }

    func testObserveOneManuallySubmittedChat() async throws {
        try await observeOneManuallySubmittedChat(stopAtFirstReply: false)
    }

    func testObserveOneManuallySubmittedChatAndStopAtFirstReply() async throws {
        try await observeOneManuallySubmittedChat(stopAtFirstReply: true)
    }

    func testObserveOneManuallySubmittedChatAcrossGrantRenewal() async throws {
        guard let threadId = ProcessInfo.processInfo.environment["INK_DREAM_TEST_THREAD_ID"],
              UUID(uuidString: threadId) != nil else {
            throw XCTSkip("An existing owned Thread was not supplied to the renewal observer.")
        }
        try await observeOneManuallySubmittedChat(stopAtFirstReply: false, terminalTimeout: 420, renewalThreadId: threadId)
    }

    private func observeOneManuallySubmittedChat(stopAtFirstReply: Bool, terminalTimeout: TimeInterval = 180, renewalThreadId: String? = nil) async throws {
        let environment = ProcessInfo.processInfo.environment
        guard let email = environment["INK_DREAM_TEST_EMAIL"], !email.isEmpty else {
            throw XCTSkip("The expected Dream account was not supplied to the observer.")
        }
        let webView = try await waitForWebView(timeout: 120)
        try await waitForJavaScript(webView, timeout: 240) {
            "return Boolean(document.querySelector('#chat-input'));"
        }
        let accountCheck = try await evaluate(webView, """
            const response = await fetch('/auth/session', {credentials: 'same-origin', cache: 'no-store'});
            return {status: response.status, matched: response.ok && (await response.json()).user?.email === args.email};
            """, arguments: ["args": ["email": email]]) as? [String: Any]
        print("IOS_VISIBLE_CHAT_ACCOUNT_CHECK status=\(accountCheck?["status"] as? Int ?? 0) matched=\(accountCheck?["matched"] as? Bool ?? false)")
        XCTAssertEqual(accountCheck?["status"] as? Int, 200)
        XCTAssertEqual(accountCheck?["matched"] as? Bool, true)
        guard accountCheck?["status"] as? Int == 200, accountCheck?["matched"] as? Bool == true else { return }
        try installOriginalPythonHTTPTrace(renewalOnly: renewalThreadId != nil)
        try installOriginalChatStreamTrace()
        if let renewalThreadId { try installOriginalGrantRenewalTrace(threadId: renewalThreadId) }
        defer { try? runEmbeddedPythonQualification("""
            httpx.Client.send = _ios_original_http_send
            ios._app.middleware_stack = _ios_original_application_stack
            """)
            if renewalThreadId != nil {
                try? runEmbeddedPythonQualification("RuntimeGrantKeeper.tick = _ios_original_grant_tick")
            }
        }
        _ = try await evaluate(webView, """
            const originalFetch = window.fetch.bind(window);
            const argsExpectedThread = args.expectedThreadId;
            const replyCount = () => Array.from(document.querySelectorAll('p')).filter(node => node.textContent?.trim().toLowerCase() === 'ios execution ok 20261025').length;
            const observation = {count: 0, done: false, status: 0, code: 'none', expectedThreadMatched: false, baselineReplyCount: 0, reads: [], streamReads: 0, streamBytes: 0, streamEof: false, streamEofMs: 0, streamReadError: 'none', automaticStopClicked: false, stop: {count:0, done:false, status:0, accepted:false, threadMatched:false, running:null, lifecycle:'unknown', code:'none'}};
            let submittedThread = null;
            window.__INK_IOS_TEST_CHAT_OBSERVATION__ = observation;
            window.fetch = async (...args) => {
              const request = args[0];
              const url = new URL(typeof request === 'string' ? request : request.url, location.href);
              const method = args[1]?.method || request.method || 'GET';
              const watched = url.origin === location.origin && url.pathname === '/api/claude-agent' && method.toUpperCase() === 'POST';
              const stopped = url.origin === location.origin && new RegExp('^/api/claude-agent/threads/[^/]+/stop$').test(url.pathname) && method.toUpperCase() === 'POST';
              const recovery = url.origin === location.origin && method.toUpperCase() === 'GET'
                ? (url.pathname === '/auth/session' ? 'session' : new RegExp('^/api/claude-agent/threads/[^/]+/messages$').test(url.pathname) ? 'history' : new RegExp('^/api/claude-agent/threads/[^/]+/status$').test(url.pathname) ? 'status' : new RegExp('^/api/claude-agent/threads/[^/]+/inputs$').test(url.pathname) ? 'inputs' : null)
                : null;
              const read = recovery && observation.reads.length < 32 ? {operation: recovery, status: 0, elapsedMs: 0, code: 'pending'} : null;
              const started = performance.now();
              if (read) observation.reads.push(read);
              if (watched) {
                observation.count++; observation.baselineReplyCount = replyCount();
                try { submittedThread = JSON.parse(args[1]?.body)?.id ?? null; } catch { submittedThread = null; }
                observation.expectedThreadMatched = !argsExpectedThread || submittedThread === argsExpectedThread;
              }
              if (stopped) observation.stop.count++;
              try {
                const response = await originalFetch(...args);
                if (read) { read.status = response.status; read.elapsedMs = Math.round(performance.now() - started); read.code = 'none'; }
                if (stopped) {
                  observation.stop.status = response.status;
                  try {
                    const receipt = await response.clone().json();
                    observation.stop.threadMatched = typeof submittedThread === 'string' && receipt.thread_id === submittedThread && decodeURIComponent(url.pathname.split('/')[4]) === submittedThread;
                    observation.stop.accepted = response.ok && receipt.ok === true && receipt.stop_requested === true;
                    observation.stop.running = typeof receipt.running === 'boolean' ? receipt.running : null;
                    observation.stop.lifecycle = ['idle','running','destroyed','not_found'].includes(receipt.lifecycle) ? receipt.lifecycle : 'unknown';
                    if (!response.ok) {
                      const code = receipt.detail?.error_code || receipt.detail?.code;
                      observation.stop.code = typeof code === 'string' && /^[A-Z0-9_.-]+$/.test(code) ? code : 'HTTP_REJECTED';
                    }
                  } catch { observation.stop.code = 'RESPONSE_JSON_INVALID'; }
                  observation.stop.done = true;
                }
                if (watched) {
                  observation.status = response.status;
                  if (response.body) {
                    const getReader = response.body.getReader.bind(response.body);
                    response.body.getReader = (...readerArgs) => {
                      const reader = getReader(...readerArgs);
                      const read = reader.read.bind(reader);
                      reader.read = async (...readArgs) => {
                        try {
                          const packet = await read(...readArgs);
                          observation.streamReads++;
                          observation.streamBytes += packet.value?.byteLength || 0;
                          if (packet.done) { observation.streamEof = true; observation.streamEofMs = Math.round(performance.now() - started); }
                          return packet;
                        } catch (error) {
                          observation.streamReadError = error.name === 'AbortError' ? 'REQUEST_ABORTED' : 'READ_FAILED';
                          throw error;
                        }
                      };
                      return reader;
                    };
                  }
                  if (!response.ok) {
                    try {
                      const payload = await response.clone().json();
                      const code = payload.detail?.error_code || payload.detail?.code || payload.detail;
                      observation.code = typeof code === 'string' && /^[A-Z0-9_.-]+$/.test(code) ? code : 'unclassified';
                    } catch { observation.code = 'unclassified'; }
                  }
                  observation.done = true;
                }
                return response;
              } catch (error) {
                if (read) { read.elapsedMs = Math.round(performance.now() - started); read.code = error.name === 'AbortError' ? 'REQUEST_ABORTED' : 'FETCH_FAILED'; }
                if (watched) { observation.done = true; observation.code = error.name === 'AbortError' ? 'REQUEST_ABORTED' : 'FETCH_FAILED'; }
                if (stopped) { observation.stop.done = true; observation.stop.code = error.name === 'AbortError' ? 'REQUEST_ABORTED' : 'FETCH_FAILED'; }
                throw error;
              }
            };
            return true;
            """, arguments: ["args": ["expectedThreadId": renewalThreadId ?? ""]])
        print("IOS_VISIBLE_CHAT_OBSERVER_READY manualSubmitLimit=1 stopAtFirstReply=\(stopAtFirstReply) relay=disabled")
        do {
            try await waitForJavaScript(webView, timeout: 300) {
                "return window.__INK_IOS_TEST_CHAT_OBSERVATION__?.done === true;"
            }
        } catch {
            try? await printRecoveryReads(webView)
            throw error
        }
        let result = try await evaluate(webView, "return window.__INK_IOS_TEST_CHAT_OBSERVATION__;", arguments: [:]) as? [String: Any]
        print("IOS_VISIBLE_CHAT_RESPONSE count=\(result?["count"] as? Int ?? 0) status=\(result?["status"] as? Int ?? 0) code=\(result?["code"] as? String ?? "unknown")")
        XCTAssertEqual(result?["count"] as? Int, 1)
        XCTAssertEqual(result?["status"] as? Int, 200)
        XCTAssertEqual(result?["expectedThreadMatched"] as? Bool, true)
        guard result?["count"] as? Int == 1, result?["status"] as? Int == 200,
              result?["expectedThreadMatched"] as? Bool == true else { return }
        do {
            try await waitForJavaScript(webView, timeout: terminalTimeout) {
            """
            const replyCount = Array.from(document.querySelectorAll('p')).filter(node => node.textContent?.trim().toLowerCase() === 'ios execution ok 20261025').length;
            const complete = replyCount > window.__INK_IOS_TEST_CHAT_OBSERVATION__.baselineReplyCount;
            const failed = Array.from(document.querySelectorAll('button')).some(node => ['Reload conversation','重新加载对话'].includes(node.textContent?.trim()));
            const observation = window.__INK_IOS_TEST_CHAT_OBSERVATION__;
            const stopButton = document.querySelector('button[aria-label="Stop generating"],button[aria-label="停止生成"],button[aria-label="Stopping"],button[aria-label="正在停止"]');
            if (\(stopAtFirstReply ? "true" : "false") && complete && observation.count === 1
                && observation.streamReads > 0 && !observation.streamEof && !observation.automaticStopClicked
                && stopButton && !stopButton.disabled && stopButton.getClientRects().length > 0) {
                observation.automaticStopClicked = true;
                stopButton.click();
            }
            const stopped = observation.stop;
            const stopFinished = stopped.count === 0 || stopped.done === true;
            return stopFinished && (failed || (complete && !stopButton));
            """
            }
        } catch {
            try? await printRecoveryReads(webView)
            try? runEmbeddedPythonQualification("""
            import asyncio, json, sys
            from mobile_runtime import ios
            def _ios_function_chain(value):
                names = []
                while value is not None and len(names) < 24:
                    code = getattr(value, 'cr_code', None) or getattr(value, 'gi_code', None)
                    if code is None:
                        break
                    names.append(code.co_qualname)
                    value = getattr(value, 'cr_await', None) or getattr(value, 'gi_yieldfrom', None)
                return names
            async def _ios_pending_snapshot():
                return [_ios_function_chain(task.get_coro()) for task in asyncio.all_tasks() if not task.done()][:64]
            _ios_diagnostic = {}
            _ios_diagnostic_future = asyncio.run_coroutine_threadsafe(_ios_pending_snapshot(), ios._loop)
            try:
                _ios_diagnostic['tasks'] = _ios_diagnostic_future.result(timeout=3)
            except Exception as failure:
                _ios_diagnostic['snapshot_error'] = type(failure).__name__
                _ios_diagnostic_future.cancel()
            _ios_frames = []
            for frame in sys._current_frames().values():
                chain = []
                while frame is not None and len(chain) < 24:
                    chain.append(frame.f_code.co_qualname)
                    frame = frame.f_back
                _ios_frames.append(chain)
            _ios_diagnostic['threads'] = _ios_frames
            print('IOS_PENDING_RUNTIME_DIAGNOSTICS ' + json.dumps(_ios_diagnostic), flush=True)
            """)
            throw error
        }
        let expectedReply = try await evaluate(webView, """
            const replyCount = Array.from(document.querySelectorAll('p')).filter(node => node.textContent?.trim().toLowerCase() === 'ios execution ok 20261025').length;
            const failed = Array.from(document.querySelectorAll('button')).some(node => ['Reload conversation','重新加载对话'].includes(node.textContent?.trim()));
            return replyCount > window.__INK_IOS_TEST_CHAT_OBSERVATION__.baselineReplyCount && !failed && !document.querySelector('button[aria-label="Stop generating"],button[aria-label="停止生成"],button[aria-label="Stopping"],button[aria-label="正在停止"]');
            """, arguments: [:]) as? Bool
        XCTAssertEqual(expectedReply, true, "Original Chat reached a terminal failure before the expected reply")
        try await printRecoveryReads(webView)
        if stopAtFirstReply {
            let automaticStop = try await evaluate(webView, """
                const value = window.__INK_IOS_TEST_CHAT_OBSERVATION__;
                return {clicked: value.automaticStopClicked, count: value.stop.count};
                """, arguments: [:]) as? [String: Any]
            XCTAssertEqual(automaticStop?["clicked"] as? Bool, true)
            XCTAssertEqual(automaticStop?["count"] as? Int, 1)
            print("IOS_VISIBLE_CHAT_AUTOMATIC_STOP clicked=\(automaticStop?["clicked"] as? Bool ?? false) count=\(automaticStop?["count"] as? Int ?? 0)")
        }
        guard expectedReply == true else { return }
        if renewalThreadId != nil {
            try runEmbeddedPythonQualification("""
            _ios_persistence_rows = [row for row in _ios_grant_probe_records if row['purpose'] == 'server-persistence']
            assert len({row['expiresAt'] for row in _ios_persistence_rows}) > 1
            assert not _ios_persistence_rows[-1]['expired']
            print('IOS_ORIGINAL_GRANT_RENEWAL_PROOF persistenceRenewed=true', flush=True)
            """)
        }
        print("IOS_VISIBLE_CHAT_REPLY_PROOF newExpectedReply=true terminal=true relay=disabled")
    }

    private func installOriginalGrantRenewalTrace(threadId: String) throws {
        try runEmbeddedPythonQualification("""
        from services.admin_data.delegation_keeper import RuntimeGrantKeeper
        _ios_original_grant_tick = RuntimeGrantKeeper.tick
        _ios_grant_probe_seen, _ios_grant_probe_rows, _ios_grant_probe_records = {}, 0, []
        def _ios_report_grant_tick(keeper):
            global _ios_grant_probe_rows
            if keeper._grant.thread_id != '\(threadId)' or _ios_grant_probe_rows >= 32:
                return
            snapshot = keeper.diagnostics()
            purpose = keeper._grant.purpose
            if purpose not in ('server-persistence', 'gateway-cli', 'editor-stdio'):
                return
            error = snapshot.last_error_code
            if error not in (None, 'ADMIN_TIMEOUT', 'ADMIN_UNAVAILABLE', 'ADMIN_RESPONSE_INVALID',
                             'DELEGATION_EXPIRED', 'DELEGATION_BACKGROUND_FAILURE',
                             'DELEGATION_REQUIRED', 'DELEGATION_ENTITY_DENIED'):
                error = 'OTHER_REGISTERED_ERROR'
            row = dict(purpose=purpose, pendingReceipt=snapshot.pending_request_id is not None,
                error=error, expired=snapshot.expired, stopped=snapshot.stopped,
                expiresAt=keeper._grant.expires_at.isoformat(),
                threadAlive=keeper._thread is not None and keeper._thread.is_alive())
            if _ios_grant_probe_seen.get(id(keeper)) != row:
                _ios_grant_probe_seen[id(keeper)] = row
                _ios_grant_probe_rows += 1
                _ios_grant_probe_records.append(row)
                print('IOS_ORIGINAL_GRANT_DIAGNOSTICS ' + json.dumps(row), flush=True)
        def _ios_observed_grant_tick(keeper):
            try:
                return _ios_original_grant_tick(keeper)
            finally:
                try:
                    _ios_report_grant_tick(keeper)
                except Exception:
                    pass
        RuntimeGrantKeeper.tick = _ios_observed_grant_tick
        """)
    }

    private func installOriginalChatStreamTrace() throws {
        try runEmbeddedPythonQualification("""
        from mobile_runtime import ios
        _ios_original_application_stack = ios._app.middleware_stack
        assert _ios_original_application_stack is not None
        async def _ios_observed_application(scope, receive, send):
            global _ios_http_events
            if scope.get('type') != 'http' or scope.get('method') != 'POST' or scope.get('path') != '/api/claude-agent':
                return await _ios_original_application_stack(scope, receive, send)
            _ios_http_events = 0
            started = time.monotonic()
            summary = dict(bodyEvents=0, bodyBytes=0, finishFrame=False, eof=False)
            async def observed_send(event):
                body = event.get('body', b'')
                await send(event)
                if event['type'] == 'http.response.start':
                    print('IOS_ORIGINAL_CHAT_ASGI ' + json.dumps(dict(phase='headers', status=event['status'], elapsedMs=round((time.monotonic()-started)*1000))), flush=True)
                elif event['type'] == 'http.response.body':
                    summary['bodyEvents'] += 1
                    summary['bodyBytes'] += len(body)
                    # Original ChatStreamAdapter emits one complete encoded frame
                    # per ASGI body. Record only its fixed terminal discriminator.
                    if body.startswith(b'data: {"type":"finish",') or body.startswith(b'data: {"type":"finish"}'):
                        summary['finishFrame'] = True
                        print('IOS_ORIGINAL_CHAT_ASGI ' + json.dumps(dict(phase='finish-frame', elapsedMs=round((time.monotonic()-started)*1000))), flush=True)
                    if not event.get('more_body', False):
                        summary['eof'] = True
                        print('IOS_ORIGINAL_CHAT_ASGI ' + json.dumps(dict(phase='eof', elapsedMs=round((time.monotonic()-started)*1000), **summary)), flush=True)
            try:
                return await _ios_original_application_stack(scope, receive, observed_send)
            finally:
                print('IOS_ORIGINAL_CHAT_ASGI ' + json.dumps(dict(phase='returned', elapsedMs=round((time.monotonic()-started)*1000), **summary)), flush=True)
        ios._app.middleware_stack = _ios_observed_application
        """)
    }

    private func installOriginalPythonHTTPTrace(renewalOnly: Bool = false, confirmationOnly: Bool = false) throws {
        try runEmbeddedPythonQualification("""
        import httpx, json, re, time
        _ios_original_http_send = httpx.Client.send
        _ios_http_sequence = 0
        _ios_http_events = 0
        def _ios_http_report(sequence, operation, phase, started, **fields):
            global _ios_http_events
            try:
                if _ios_http_events >= 192:
                    return
                _ios_http_events += 1
                print('IOS_PYTHON_HTTP_PHASE ' + json.dumps(dict(
                    sequence=sequence, operation=operation, phase=phase,
                    elapsedMs=round((time.monotonic()-started)*1000), **fields)), flush=True)
            except Exception:
                pass
        def _ios_observed_http_send(client, request, *args, **kwargs):
            global _ios_http_sequence
            _ios_http_sequence += 1
            sequence, started = _ios_http_sequence, time.monotonic()
            path = request.url.path
            prefix = '/api/internal/dream/v1/operations/'
            operation = path[len(prefix):] if path.startswith(prefix) else {
                '/api/auth/oauth2/token':'service-token',
                '/api/auth/jwks':'jwks',
                '/api/internal/dream/v1/capabilities':'capabilities',
                '/api/runtime-delegations':'runtime-create',
                '/api/runtime-delegations/renew':'runtime-renew',
                '/v1/models':'gateway-models',
            }.get(path, 'other')
            if path.startswith('/api/runtime-delegations/receipts/'):
                operation = 'runtime-receipt'
            if re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', operation) is None:
                operation = 'other'
            if \(renewalOnly ? "True" : "False") and operation not in ('runtime-renew', 'runtime-receipt'):
                return _ios_original_http_send(client, request, *args, **kwargs)
            if \(confirmationOnly ? "True" : "False") and operation not in (
                'story-workspace-confirmation.claim-turn', 'story-workspace-confirmation.lease',
                'story-workspace-confirmation.ack', 'workflow-context.read', 'deck-chat-context.read',
                'system-config.get', 'runtime-create', 'runtime-renew', 'runtime-receipt', 'gateway-models'):
                return _ios_original_http_send(client, request, *args, **kwargs)
            _ios_http_report(sequence, operation, 'start', started)
            try:
                response = _ios_original_http_send(client, request, *args, **kwargs)
            except BaseException as failure:
                _ios_http_report(sequence, operation, 'failed', started, errorClass=type(failure).__name__)
                raise
            _ios_http_report(sequence, operation, 'headers', started, status=response.status_code)
            original_iter = response.iter_bytes
            def observed_iter(*read_args, **read_kwargs):
                try:
                    yield from original_iter(*read_args, **read_kwargs)
                except BaseException as failure:
                    _ios_http_report(sequence, operation, 'body-failed', started, errorClass=type(failure).__name__)
                    raise
                else:
                    _ios_http_report(sequence, operation, 'body-ended', started)
            response.iter_bytes = observed_iter
            return response
        httpx.Client.send = _ios_observed_http_send
        """)
    }

    private func printRecoveryReads(_ webView: WKWebView) async throws {
        let reads = try await evaluate(webView, "return window.__INK_IOS_TEST_CHAT_OBSERVATION__?.reads ?? [];", arguments: [:]) as? [[String: Any]] ?? []
        let data = try JSONSerialization.data(withJSONObject: reads, options: [.sortedKeys])
        print("IOS_VISIBLE_CHAT_RECOVERY_READS \(String(decoding: data, as: UTF8.self))")
        let stream = try await evaluate(webView, """
            const value = window.__INK_IOS_TEST_CHAT_OBSERVATION__;
            return value ? {reads:value.streamReads, bytes:value.streamBytes, eof:value.streamEof, eofMs:value.streamEofMs, error:value.streamReadError} : {};
            """, arguments: [:]) as? [String: Any] ?? [:]
        let streamData = try JSONSerialization.data(withJSONObject: stream, options: [.sortedKeys])
        print("IOS_VISIBLE_CHAT_STREAM_READS \(String(decoding: streamData, as: UTF8.self))")
        let stop = try await evaluate(webView, "return window.__INK_IOS_TEST_CHAT_OBSERVATION__?.stop ?? {};", arguments: [:]) as? [String: Any] ?? [:]
        let stopData = try JSONSerialization.data(withJSONObject: stop, options: [.sortedKeys])
        print("IOS_VISIBLE_CHAT_STOP_RECEIPT \(String(decoding: stopData, as: UTF8.self))")
        if (stop["count"] as? Int ?? 0) > 0 {
            XCTAssertEqual(stop["done"] as? Bool, true)
            XCTAssertEqual(stop["count"] as? Int, 1)
            XCTAssertEqual(stop["status"] as? Int, 200)
            XCTAssertEqual(stop["accepted"] as? Bool, true)
            XCTAssertEqual(stop["threadMatched"] as? Bool, true)
        }
    }

    func testPackagedLocalNextRendersOriginalLoginForm() async throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let webView = try await waitForWebView(timeout: 45)
        try await waitForJavaScript(webView, timeout: 45) {
            "return window.__INK_FRONTEND_VERSION__ === 'next-phase1' && Boolean(document.querySelector('input[name=email]') && document.querySelector('input[name=password]'));"
        }
        XCTAssertTrue(["127.0.0.1", "localhost", "::1", "[::1]"].contains(webView.url?.host ?? ""))
        XCTAssertTrue(webView.configuration.websiteDataStore.isPersistent)
        let observation = try await evaluate(webView, """
            const health = await fetch('/api/health', {cache: 'no-store'});
            const auth = await fetch('/auth/options', {cache: 'no-store'});
            const payload = await auth.json();
            return {service: (await health.json()).service, status: auth.status, detail: payload.detail,
              passwordAction: payload.password_action, googleAction: payload.google_action,
              passwordType: document.querySelector('input[name=password]').type,
              originalForm: document.querySelector('input[name=password]').closest('form').method};
            """, arguments: [:]) as? [String: Any]
        XCTAssertEqual(observation?["service"] as? String, "ink-memory-web")
        let code = (observation?["detail"] as? String) ?? "none"
        print("IOS_NEXT_WEBVIEW_AUTH_STATUS status=\(observation?["status"] as? Int ?? 0) code=\(code) origin=\(webView.url?.host ?? "unknown")")
        let configured = Bundle.main.resourceURL.map {
            FileManager.default.fileExists(atPath: $0.appendingPathComponent("app/.env").path)
        } ?? false
        XCTAssertEqual(observation?["status"] as? Int, configured ? 200 : 503)
        if configured {
            XCTAssertTrue((observation?["passwordAction"] as? String)?.hasSuffix("/auth/dream/password") == true)
            XCTAssertTrue((observation?["googleAction"] as? String)?.hasSuffix("/auth/dream/google") == true)
        } else {
            XCTAssertEqual(observation?["detail"] as? String, "BFF_CONFIGURATION_INVALID")
        }
        XCTAssertEqual(observation?["passwordType"] as? String, "password")
        XCTAssertEqual(observation?["originalForm"] as? String, "post")
        print("IOS_NEXT_WEBVIEW_PROOF originalReactHydrated=true originalPasswordForm=true persistentWebKit=true authConfiguration=\(observation?["status"] as? Int ?? 0) relay=disabled")
    }

    func testPackagedHostLogsInAndCompletesOneChatTurn() async throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let environment = ProcessInfo.processInfo.environment
        let stopAfterFirstReply = environment["INK_DREAM_TEST_STOP_AFTER_FIRST_REPLY"] == "true"
        guard let email = environment["INK_DREAM_TEST_EMAIL"], !email.isEmpty,
              let expectedModel = environment["INK_DREAM_TEST_MODEL_ALIAS"], !expectedModel.isEmpty else {
            throw XCTSkip("The existing account and explicit model were not supplied.")
        }
        let password = environment["INK_DREAM_TEST_PASSWORD"] ?? ""
        let prompt = environment["INK_DREAM_TEST_PROMPT"] ?? "请只回复：iPhone 业务链路正常"
        let expectedReply = environment["INK_DREAM_TEST_EXPECTED_REPLY"] ?? "iPhone 业务链路正常"
        let webView = try await logIn(email: email, password: password)
        if let thread = environment["INK_DREAM_TEST_THREAD_ID"], UUID(uuidString: thread) != nil {
            let selected = try await evaluate(webView, """
                const response = await fetch('/api/claude-agent/threads/' + args.thread + '/messages', {credentials:'same-origin', cache:'no-store'});
                const payload = response.ok ? await response.json() : {};
                if (payload.thread?.id !== args.thread || typeof payload.thread?.title !== 'string') return false;
                window.__INK_RN_RECOVERY_TITLE__ = payload.thread.title;
                return true;
                """, arguments: ["args": ["thread": thread]]) as? Bool
            XCTAssertEqual(selected, true)
            guard selected == true else { return }
            try await waitForJavaScript(webView, timeout: 60) {
                "const target = Array.from(document.querySelectorAll('button[title]')).find(button => button.title === window.__INK_RN_RECOVERY_TITLE__); if (!target) return false; target.click(); return true;"
            }
            let previous = environment["INK_DREAM_TEST_PREVIOUS_REPLY"] ?? ""
            try await waitForJavaScript(webView, timeout: 90, arguments: ["previous": previous]) {
                "return args.previous && Array.from(document.querySelectorAll('p')).some(node => node.textContent?.trim() === args.previous);"
            }
            print("IOS_RN_REOPEN_PROOF originalThread=\(thread) previousAssistantVisible=true appPid=\(ProcessInfo.processInfo.processIdentifier)")
        }
        let modelCheck = try await evaluate(webView, """
            const response = await fetch('/api/system-config', {credentials:'same-origin', cache:'no-store'});
            if (!response.ok) return false;
            const payload = await response.json();
            return (payload.data ?? payload).model === args.model;
            """, arguments: ["args": ["model": expectedModel]]) as? Bool
        XCTAssertEqual(modelCheck, true)
        guard modelCheck == true else { return }
        print("IOS_RN_CHAT_MODEL_SELECTED alias=\(expectedModel) maximumSubmissions=1")
        _ = try await evaluate(webView, """
            const original = window.fetch.bind(window);
            const proof = window.__INK_RN_CHAT_ACCEPTANCE__ = {submissions:0, thread:null, reads:0, bytes:0, eof:false, stopClicked:false, stopCount:0};
            window.fetch = async (input, init) => {
              const path = new URL(typeof input === 'string' ? input : input.url, location.href).pathname;
              const observed = path === '/api/claude-agent' && init?.method?.toUpperCase() === 'POST';
              const stopped = /^\\/api\\/claude-agent\\/threads\\/[^/]+\\/stop$/.test(path) && init?.method?.toUpperCase() === 'POST';
              if (observed) { proof.submissions++; proof.thread = JSON.parse(init.body).id; }
              if (stopped) proof.stopCount++;
              const response = await original(input, init);
              if (stopped) {
                const receipt = await response.clone().json();
                proof.stopStatus = response.status;
                proof.stopAccepted = receipt.ok === true && receipt.stop_requested === true && receipt.thread_id === proof.thread;
              }
              if (observed) {
                proof.status = response.status;
                const reader = response.clone().body?.getReader();
                if (reader) void (async () => {
                  try { while (true) { const next = await reader.read(); if (next.done) { proof.eof = true; break; }
                    proof.reads++; proof.bytes += next.value.byteLength; } }
                  catch { proof.readFailed = true; }
                })();
              }
              return response;
            };
            return true;
            """, arguments: [:])

        _ = try await evaluate(
            webView,
            """
            const editor = document.querySelector('#chat-input');
            if (!editor) throw new Error('CHAT_INPUT_UNAVAILABLE');
            editor.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, args.prompt);
            editor.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: args.prompt}));
            return true;
            """,
            arguments: ["args": ["prompt": prompt]]
        )
        try await waitForJavaScript(webView, timeout: 30) {
            "const send = document.querySelector('button[aria-label=\"Send message\"],button[aria-label=\"发送消息\"]'); return Boolean(send && !send.disabled);"
        }
        _ = try await evaluate(
            webView,
            "document.querySelector('button[aria-label=\"Send message\"],button[aria-label=\"发送消息\"]')?.click(); return true;",
            arguments: [:]
        )

        try await waitForJavaScript(
            webView,
            timeout: 180,
            arguments: ["prompt": prompt, "expectedReply": expectedReply, "stop": stopAfterFirstReply]
        ) {
            """
            const paragraphs = Array.from(document.querySelectorAll('p'));
            const submitted = paragraphs.some(node => node.textContent?.trim() === args.prompt);
            const answered = paragraphs.some(node => node.textContent?.trim() === args.expectedReply);
            const running = Boolean(document.querySelector('button[aria-label="Stop generating"],button[aria-label="停止生成"],button[aria-label="Stopping"],button[aria-label="正在停止"]'));
            const proof = window.__INK_RN_CHAT_ACCEPTANCE__;
            if (args.stop && answered && running && !proof.stopClicked) {
              const stop = document.querySelector('button[aria-label="Stop generating"],button[aria-label="停止生成"]');
              if (stop && !stop.disabled) { proof.stopClicked = true; stop.click(); }
            }
            if (args.stop && (!proof.stopAccepted || !proof.stopClicked)) return false;
            return submitted && answered && !running;
            """
        }
        let proof = try await evaluate(webView, """
            const proof = window.__INK_RN_CHAT_ACCEPTANCE__;
            if (!proof?.thread) return {submissions:proof?.submissions ?? 0};
            const messages = await fetch('/api/claude-agent/threads/' + proof.thread + '/messages', {credentials:'same-origin', cache:'no-store'});
            const payload = messages.ok ? await messages.json() : {};
            const saved = (payload.messages ?? []).filter(message => message.role === 'assistant')
              .some(message => JSON.stringify(message).includes(args.expected));
            return {...proof, messages:messages.status, assistantPersisted:saved};
            """, arguments: ["args": ["expected": expectedReply]]) as? [String: Any] ?? [:]
        XCTAssertEqual(proof["submissions"] as? Int, 1)
        if let thread = environment["INK_DREAM_TEST_THREAD_ID"] { XCTAssertEqual(proof["thread"] as? String, thread) }
        XCTAssertEqual(proof["status"] as? Int, 200)
        XCTAssertGreaterThan(proof["reads"] as? Int ?? 0, 1)
        if stopAfterFirstReply {
            XCTAssertEqual(proof["stopClicked"] as? Bool, true)
            XCTAssertEqual(proof["stopCount"] as? Int, 1)
            XCTAssertEqual(proof["stopStatus"] as? Int, 200)
            XCTAssertEqual(proof["stopAccepted"] as? Bool, true)
        } else {
            XCTAssertEqual(proof["eof"] as? Bool, true)
        }
        XCTAssertEqual(proof["messages"] as? Int, 200)
        XCTAssertEqual(proof["assistantPersisted"] as? Bool, true)
        let receipt = try JSONSerialization.data(withJSONObject: proof, options: [.sortedKeys])
        print("IOS_RN_CHAT_COMPLETION_PROOF \(String(decoding: receipt, as: UTF8.self))")
    }

    func testPackagedHostNormalLoginAndWorkspaceReads() async throws {
        let environment = ProcessInfo.processInfo.environment
        guard let email = environment["INK_DREAM_TEST_EMAIL"], !email.isEmpty else {
            throw XCTSkip("The expected Dream account was not supplied to the test process.")
        }
        let password = environment["INK_DREAM_TEST_PASSWORD"] ?? ""
        let webView = try await logIn(email: email, password: password)
        let result = try await evaluate(webView, """
            const session = await fetch('/auth/session', {credentials: 'same-origin', cache: 'no-store'});
            const payload = await session.json();
            const threads = await fetch('/api/claude-agent/threads', {credentials: 'same-origin', cache: 'no-store'});
            const decks = await fetch('/api/decks', {credentials: 'same-origin', cache: 'no-store'});
            const models = await fetch('/api/gateway/models', {credentials: 'same-origin', cache: 'no-store'});
            const catalog = await models.json();
            const configurationResponse = await fetch('/api/system-config', {credentials:'same-origin', cache:'no-store'});
            const configuration = configurationResponse.ok ? await configurationResponse.json() : {};
            const model = (configuration.data ?? configuration).model;
            const code = async response => {
              if (response.ok) return 'none';
              try {
                const value = (await response.json()).detail;
                return typeof value === 'string' && /^[A-Z0-9_.-]+$/.test(value) ? value : 'unclassified';
              } catch { return 'unclassified'; }
            };
            return {session: session.status, accountMatched: payload.user?.email === args.email,
              csrfPresent: typeof payload.csrf_token === 'string' && payload.csrf_token.length > 0,
              threads: threads.status, decks: decks.status, threadsCode: await code(threads), decksCode: await code(decks),
              models: models.status, selectedModelAlias: typeof model === 'string' ? model : null,
              callableModels: Array.isArray(catalog.data) ? catalog.data.filter(model => model.callable).map(model => model.modelAlias) : [],
              modelCode: typeof catalog.detail?.code === 'string' && /^[A-Z0-9_.-]+$/.test(catalog.detail.code) ? catalog.detail.code : 'none'};
            """, arguments: ["args": ["email": email]]) as? [String: Any]
        XCTAssertEqual(result?["session"] as? Int, 200)
        XCTAssertEqual(result?["accountMatched"] as? Bool, true)
        XCTAssertEqual(result?["csrfPresent"] as? Bool, true)
        XCTAssertEqual(result?["threads"] as? Int, 200)
        XCTAssertEqual(result?["decks"] as? Int, 200)
        XCTAssertEqual(result?["models"] as? Int, 200)
        XCTAssertFalse((result?["callableModels"] as? [String] ?? []).isEmpty)
        print("IOS_WORKSPACE_READ_STATUS threads=\(result?["threads"] as? Int ?? 0) code=\(result?["threadsCode"] as? String ?? "unknown") decks=\(result?["decks"] as? Int ?? 0) code=\(result?["decksCode"] as? String ?? "unknown")")
        print("IOS_MODEL_CATALOG_STATUS status=\(result?["models"] as? Int ?? 0) code=\(result?["modelCode"] as? String ?? "unknown") callable=\((result?["callableModels"] as? [String] ?? []).joined(separator: ","))")
        print("IOS_SELECTED_MODEL_PROOF alias=\(result?["selectedModelAlias"] as? String ?? "missing")")
        if result?["session"] as? Int == 200, result?["accountMatched"] as? Bool == true,
           result?["csrfPresent"] as? Bool == true, result?["threads"] as? Int == 200,
           result?["decks"] as? Int == 200, result?["models"] as? Int == 200,
           !(result?["callableModels"] as? [String] ?? []).isEmpty {
            print("IOS_NORMAL_LOGIN_PROOF accountMatched=true session=200 csrf=true threads=200 decks=200 models=200 relay=disabled")
        }
    }

    private func logIn(email: String, password: String) async throws -> WKWebView {
        let webView = try await waitForWebView(timeout: 120)

        try await waitForJavaScript(webView, timeout: 120) {
            "return Boolean(document.querySelector('input[name=email]') || document.querySelector('#chat-input'));"
        }
        let existing = try await evaluate(webView, """
            if (!document.querySelector('#chat-input')) return false;
            const response = await fetch('/auth/session', {credentials: 'same-origin', cache: 'no-store'});
            if (!response.ok) throw new Error('EXISTING_SESSION_UNAVAILABLE');
            const session = await response.json();
            if (session.user?.email !== args.email) throw new Error('EXISTING_ACCOUNT_MISMATCH');
            return true;
            """, arguments: ["args": ["email": email]]) as? Bool
        if existing == true {
            print("IOS_AUTHENTICATION_CHECKPOINT source=existing-web-session accountMatched=true")
            return webView
        }
        guard !password.isEmpty else {
            throw XCTSkip("The expected Web session is absent and no login password was supplied.")
        }
        try await waitForJavaScript(webView, timeout: 120) {
            "return Boolean(document.querySelector('input[name=email]') && document.querySelector('input[name=password]') && document.querySelector('button[type=submit]:not([disabled])'));"
        }
        _ = try await evaluate(
            webView,
            """
            const email = document.querySelector('input[name=email]');
            const password = document.querySelector('input[name=password]');
            const form = password?.closest('form');
            const submit = form?.querySelector('button[type=submit]');
            if (!email || !password || !form || !submit) throw new Error('LOGIN_FORM_UNAVAILABLE');
            email.value = args.email;
            password.value = args.password;
            form.requestSubmit(submit);
            return true;
            """,
            arguments: ["args": ["email": email, "password": password]]
        )

        let deadline = Date().addingTimeInterval(120)
        var workspaceVisible = false
        repeat {
            let state = try? await evaluate(webView, """
                return {ready: Boolean(document.querySelector('#chat-input') && document.querySelector('button[aria-label="Send message"],button[aria-label="发送消息"]')),
                  rejected: Array.from(document.querySelectorAll('[role=alert]')).some(node => node.textContent?.includes('Login failed.'))};
                """, arguments: [:]) as? [String: Any]
            if state?["rejected"] as? Bool == true {
                throw NSError(domain: "InkMemory.BusinessJourney", code: 2,
                              userInfo: [NSLocalizedDescriptionKey: "The original login form returned a credential rejection."])
            }
            workspaceVisible = state?["ready"] as? Bool == true
            if workspaceVisible { break }
            try await Task.sleep(for: .milliseconds(500))
        } while Date() < deadline
        guard workspaceVisible else {
            throw NSError(domain: "InkMemory.BusinessJourney", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "The original workspace was not reached."])
        }
        let sessionStatus = try await evaluate(
            webView,
            "return (await fetch('/auth/session', {credentials: 'same-origin', cache: 'no-store'})).status;",
            arguments: [:]
        ) as? NSNumber
        XCTAssertEqual(sessionStatus?.intValue, 200)

        return webView
    }

    private func waitForWebView(timeout: TimeInterval) async throws -> WKWebView {
        let deadline = Date().addingTimeInterval(timeout)
        repeat {
            let windows = UIApplication.shared.connectedScenes.compactMap { ($0 as? UIWindowScene)?.windows }.flatMap { $0 }
            for window in windows where !window.isHidden {
                if let webView = findWebView(in: window) { return webView }
            }
            try await Task.sleep(for: .milliseconds(250))
        } while Date() < deadline
        throw XCTSkip("The packaged WKWebView did not become available.")
    }

    private func findWebView(in view: UIView) -> WKWebView? {
        if let webView = view as? WKWebView { return webView }
        for child in view.subviews {
            if let webView = findWebView(in: child) { return webView }
        }
        return nil
    }

    private func waitForJavaScript(
        _ webView: WKWebView,
        timeout: TimeInterval,
        arguments: [String: Any] = [:],
        script: () -> String
    ) async throws {
        let deadline = Date().addingTimeInterval(timeout)
        repeat {
            do {
                let value = try await evaluate(
                    webView,
                    script(),
                    arguments: ["args": arguments]
                )
                if value as? Bool == true { return }
            } catch {
                // A top-level form navigation temporarily invalidates the page context.
            }
            try await Task.sleep(for: .milliseconds(500))
        } while Date() < deadline
        XCTFail("The packaged Web business state did not reach its expected condition.")
        throw NSError(domain: "InkMemory.BusinessJourney", code: 1,
                      userInfo: [NSLocalizedDescriptionKey: "The expected visible state was not reached."])
    }

    private func evaluate(_ webView: WKWebView, _ script: String, arguments: [String: Any]) async throws -> Any? {
        try await withCheckedThrowingContinuation { continuation in
            webView.callAsyncJavaScript(script, arguments: arguments, in: nil, in: .page) { result in
                continuation.resume(with: result)
            }
        }
    }
}
