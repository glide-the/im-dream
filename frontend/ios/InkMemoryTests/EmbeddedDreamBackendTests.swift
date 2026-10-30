// [Sync] 2026-10-25: qualify configured original login actions without changing user authentication.
// [Input] App-bundled iOS CPython, native pydantic-core and the shared Dream router.
// [Output] Execution evidence from the actual native interpreter and ASGI application.
// [Pos] Embedded backend technical tests; configured login-action checks use the original Admin boundary without an account or model.
// [Sync] 2026-10-25: execute native pull streaming/cancellation and the original Dream Runner inside the application.
// [Sync] 2026-10-25: execute the target interpreter's subprocess boundary before claiming CLI compatibility.
// [Sync] 2026-10-25: qualify the original SDK/Runtime initialize protocol inside the application's Node worker.
// [Sync] 2026-10-25: execute existing business configuration and retain original authentication failures.
// [Sync] 2026-10-25: qualify original Next/ASGI HTTP inside the same application without a Mac relay.
// [Sync] 2026-10-25: import the original memory provider and load the original Dream source contracts from target resources.
// [Sync] 2026-10-25: share the existing target-interpreter qualification helper with bounded timeout diagnostics.
// [Sync] 2026-10-25: qualify incremental SSE and terminal EOF through the original Next API proxy.
// [Sync] 2026-10-25: allow configured Admin-backed startup before provider-free Runtime qualification.
// [Sync] 2026-10-25: compare bounded public Admin GETs in the target interpreter without account or model calls.
// [Sync] 2026-10-25: compare original httpx/requests transports and classify nested errors without URLs, credentials or bodies.
// [Sync] 2026-10-25: qualify packaged command startup, login-shell redirection and original App paths without a Provider.
// [Sync] 2026-10-26: use POSIX path resolution for command probes on physical iPhone container aliases.
// [Sync] 2026-10-26: verify immutable bundled plugins with original CLI receipts and fixed validation-field diagnostics inside the App.
// [Sync] 2026-10-26: qualify the packaged plugin Python interpreter alongside the existing command startup cases.
// [Sync] 2026-10-26: verify original confirmation composition is bound without starting a global claim scanner.
// [Sync] 2026-10-26: time one packaged command across an explicit manual lifecycle transition without a model or CLI deadline override.
// [Sync] 2026-10-26: await backend startup asynchronously in the main-actor lifecycle probe and synchronize notification tracing.
import Darwin
import UIKit
import XCTest
@testable import InkMemory

func runEmbeddedPythonQualification(_ source: String) throws {
        typealias EnsureGIL = @convention(c) () -> Int32
        typealias ReleaseGIL = @convention(c) (Int32) -> Void
        typealias RunPython = @convention(c) (UnsafePointer<CChar>, UnsafeMutableRawPointer?) -> Int32
        let handle = try XCTUnwrap(dlopen(nil, RTLD_NOW))
        defer { dlclose(handle) }
        let ensure = unsafeBitCast(try XCTUnwrap(dlsym(handle, "PyGILState_Ensure")), to: EnsureGIL.self)
        let release = unsafeBitCast(try XCTUnwrap(dlsym(handle, "PyGILState_Release")), to: ReleaseGIL.self)
        let run = unsafeBitCast(try XCTUnwrap(dlsym(handle, "PyRun_SimpleStringFlags")), to: RunPython.self)
        let gil = ensure()
        defer { release(gil) }
        let result = source.withCString { run($0, nil) }
        guard result == 0 else {
            XCTFail("Embedded Python qualification failed: exit \(result)")
            throw NSError(domain: "InkMemoryTests.Python", code: Int(result))
        }
}

private final class PackagedCommandExit {
    let finished = DispatchSemaphore(value: 0)
    var status: Int32 = -1
    var uptime: TimeInterval = 0

    func pollFinished() -> Bool {
        finished.wait(timeout: .now()) == .success
    }
}

// The lock protects every access to the notification trace.
private final class PackagedCommandLifecycleTrace: @unchecked Sendable {
    private let lock = NSLock()
    private var events: [[String: Any]] = []

    func record(_ name: String) {
        let event: [String: Any] = ["event": name,
            "uptimeMs": Int64(ProcessInfo.processInfo.systemUptime * 1000),
            "epochMs": Int64(Date().timeIntervalSince1970 * 1000)]
        lock.lock()
        let accepted = events.count < 16
        if accepted { events.append(event) }
        lock.unlock()
        if accepted, let data = try? JSONSerialization.data(withJSONObject: event, options: [.sortedKeys]) {
            print("IOS_PACKAGED_COMMAND_LIFECYCLE \(String(decoding: data, as: UTF8.self))")
        }
    }

    func snapshot() -> [[String: Any]] {
        lock.lock()
        defer { lock.unlock() }
        return events
    }
}

private func canonicalCommandDirectory(_ path: String) throws -> URL {
    guard let resolved = realpath(path, nil) else {
        throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EINVAL)
    }
    defer { free(resolved) }
    return URL(fileURLWithPath: String(cString: resolved), isDirectory: true)
}

final class EmbeddedDreamBackendTests: XCTestCase {
    @MainActor
    func testPackagedCommandAcrossManualLifecycleTransition() async throws {
        guard ProcessInfo.processInfo.environment["INK_DREAM_TEST_MANUAL_LIFECYCLE"] == "1" else {
            throw XCTSkip("Explicit manual lifecycle qualification was not selected.")
        }
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let startupFinished = expectation(description: "Lifecycle qualification backend startup")
        var startup: Result<[String: Any], Error>?
        EmbeddedDreamBackend.shared.start { result in
            startup = result
            startupFinished.fulfill()
        }
        await fulfillment(of: [startupFinished], timeout: 120)
        _ = try XCTUnwrap(startup).get()
        var error: NSError?
        let endpoint = try XCTUnwrap(IMDreamNodeStart(try XCTUnwrap(Bundle.main.resourcePath), &error))
        let resources = try canonicalCommandDirectory(try XCTUnwrap(Bundle.main.resourcePath))
        let data = try canonicalCommandDirectory(NSHomeDirectory())
        let manifest = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: resources.appendingPathComponent("guest/manifest.json"))) as? [String: Any])
        let digest = try XCTUnwrap(manifest["rootDigest"] as? String)
        let runtime = try canonicalCommandDirectory(URL(fileURLWithPath: endpoint).deletingLastPathComponent().path)
        XCTAssertEqual(IMDreamGuestInitialize(runtime.appendingPathComponent("guest/" + digest).path, data.path, resources.path), 0)
        let workspace = runtime.appendingPathComponent("workspaces/command-lifecycle-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: false)
        let temporary = workspace.appendingPathComponent(".claude-tmp")
        try FileManager.default.createDirectory(at: temporary, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        let trace = PackagedCommandLifecycleTrace()
        let notifications: [(Notification.Name, String)] = [
            (UIApplication.willResignActiveNotification, "willResignActive"),
            (UIApplication.didEnterBackgroundNotification, "didEnterBackground"),
            (UIApplication.didBecomeActiveNotification, "didBecomeActive")]
        let observers = notifications.map { notification, name in
            NotificationCenter.default.addObserver(forName: notification, object: nil, queue: .main) { _ in trace.record(name) }
        }
        defer { observers.forEach(NotificationCenter.default.removeObserver) }
        let outputPath = workspace.appendingPathComponent("command-output")
        let output = open(outputPath.path, O_WRONLY | O_CREAT | O_EXCL, 0o600)
        XCTAssertGreaterThanOrEqual(output, 0)
        guard output >= 0 else { return }
        var descriptors: [Int32] = [open("/dev/null", O_RDONLY), dup(output), dup(output)]
        close(output)
        let arguments = ["/bin/bash", "--noprofile", "--norc", "-c", "printf lifecycle-start; sleep 45; printf lifecycle-end"]
        let argv = arguments.joined(separator: "\0") + "\0"
        let environment = ["PATH=/usr/local/bin:/usr/bin:/bin", "HOME=" + workspace.path, "TMPDIR=" + temporary.path].joined(separator: "\0") + "\0"
        let exit = PackagedCommandExit()
        let context = Unmanaged.passRetained(exit).toOpaque()
        var pid: Int32 = 0
        var generation: UInt32 = 0
        let startedAt = ProcessInfo.processInfo.systemUptime
        let started = argv.withCString { argumentsPointer in
            environment.withCString { environmentPointer in
                IMDreamGuestSpawn(arguments[0], Int32(arguments.count), argumentsPointer, argv.utf8.count + 1,
                    environmentPointer, environment.utf8.count + 1, workspace.path, &descriptors,
                    { context, status in
                        let value = Unmanaged<PackagedCommandExit>.fromOpaque(context!).takeRetainedValue()
                        value.status = status
                        value.uptime = ProcessInfo.processInfo.systemUptime
                        value.finished.signal()
                    }, context, &pid, &generation)
            }
        }
        var finished = false
        var completed = false
        defer {
            if started == 0 && !finished { _ = IMDreamGuestKillGroup(pid, 9, generation) }
            if completed { try? FileManager.default.removeItem(at: workspace) }
        }
        XCTAssertEqual(started, 0)
        guard started == 0 else { return }
        print("IOS_PACKAGED_COMMAND_LIFECYCLE_READY commandSeconds=45 modelCalls=0 relay=disabled")
        var previousTick = ProcessInfo.processInfo.systemUptime
        var maximumGap: TimeInterval = 0
        let deadline = previousTick + 180
        while ProcessInfo.processInfo.systemUptime < deadline {
            let now = ProcessInfo.processInfo.systemUptime
            maximumGap = max(maximumGap, now - previousTick)
            previousTick = now
            if !finished { finished = exit.pollFinished() }
            let events = trace.snapshot()
            if finished, let background = events.firstIndex(where: { $0["event"] as? String == "didEnterBackground" }),
               events.dropFirst(background + 1).contains(where: { $0["event"] as? String == "didBecomeActive" }) { break }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        XCTAssertTrue(finished, "Packaged command did not finish within the qualification window")
        guard finished else { return }
        let events = trace.snapshot()
        let background = events.firstIndex(where: { $0["event"] as? String == "didEnterBackground" })
        let returned = background.map { events.dropFirst($0 + 1).contains(where: { $0["event"] as? String == "didBecomeActive" }) } ?? false
        XCTAssertNotNil(background, "Manual background transition was not observed")
        XCTAssertTrue(returned, "Manual foreground transition was not observed")
        let backgroundUptime = background.flatMap { events[$0]["uptimeMs"] as? Int64 }
        XCTAssertLessThanOrEqual(try XCTUnwrap(backgroundUptime), Int64(exit.uptime * 1000), "The command finished before the manual background transition")
        XCTAssertEqual(exit.status, 0)
        let text = try String(contentsOf: outputPath, encoding: .utf8)
        XCTAssertEqual(text, "lifecycle-startlifecycle-end")
        let result: [String: Any] = ["status": exit.status, "commandElapsedMs": Int64((exit.uptime - startedAt) * 1000),
            "maximumMainLoopGapMs": Int64(maximumGap * 1000), "foregroundReturned": returned,
            "events": events, "modelCalls": 0]
        let resultData = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print("IOS_PACKAGED_COMMAND_TIMING_PROOF \(String(decoding: resultData, as: UTF8.self))")
        completed = returned && backgroundUptime != nil && exit.status == 0 && text == "lifecycle-startlifecycle-end"
    }

    func testPackagedCommandStartupAndSharedFiles() throws {
        _ = try execute(timeout: 120) { EmbeddedDreamBackend.shared.start(completion: $0) }
        var error: NSError?
        let endpoint = try XCTUnwrap(IMDreamNodeStart(try XCTUnwrap(Bundle.main.resourcePath), &error))
        let resources = try canonicalCommandDirectory(try XCTUnwrap(Bundle.main.resourcePath))
        let data = try canonicalCommandDirectory(NSHomeDirectory())
        let manifest = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: resources.appendingPathComponent("guest/manifest.json"))) as? [String: Any])
        let digest = try XCTUnwrap(manifest["rootDigest"] as? String)
        let runtime = try canonicalCommandDirectory(URL(fileURLWithPath: endpoint).deletingLastPathComponent().path)
        let root = runtime.appendingPathComponent("guest/" + digest)
        XCTAssertEqual(IMDreamGuestInitialize(root.path, data.path, resources.path), 0)
        let originalRoot = URL(fileURLWithPath: endpoint).deletingLastPathComponent().appendingPathComponent("guest/" + digest)
        XCTAssertEqual(IMDreamGuestInitialize(originalRoot.path, NSHomeDirectory(), try XCTUnwrap(Bundle.main.resourcePath)), 0)
        let workspace = runtime.appendingPathComponent("workspaces/command-startup-" + UUID().uuidString + "-项目😀")
        try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: false)
        let temporary = workspace.appendingPathComponent(".claude-tmp")
        try FileManager.default.createDirectory(at: temporary, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        var completed = false
        defer { if completed { try? FileManager.default.removeItem(at: workspace) } }
        for (index, arguments) in [
            ["/bin/bash", "--version"],
            ["/bin/bash", "--noprofile", "--norc", "-c", "printf native-shared > command-written.txt; cat command-written.txt; printf native-ok; pwd -P"],
            ["/bin/bash", "-c", "-l", "shopt -u extglob 2>/dev/null || true && printf login-ok && pwd -P > \"$TMPDIR/cwd\""],
            ["/usr/bin/python3", "-c", "import sys, ssl, venv, ensurepip; assert sys.version_info >= (3, 11); print('plugin-python-ok')"]
        ].enumerated() {
            let outputPath = workspace.appendingPathComponent("output-\(index)")
            let output = open(outputPath.path, O_WRONLY | O_CREAT | O_EXCL, 0o600)
            XCTAssertGreaterThanOrEqual(output, 0)
            var descriptors: [Int32] = [open("/dev/null", O_RDONLY), dup(output), dup(output)]
            close(output)
            let argv = arguments.joined(separator: "\0") + "\0"
            let environment = ["PATH=/usr/local/bin:/usr/bin:/bin", "HOME=" + workspace.path, "TMPDIR=" + temporary.path].joined(separator: "\0") + "\0"
            let exit = PackagedCommandExit()
            let context = Unmanaged.passRetained(exit).toOpaque()
            var pid: Int32 = 0
            var generation: UInt32 = 0
            let started = argv.withCString { argumentsPointer in
                environment.withCString { environmentPointer in
                    IMDreamGuestSpawn(arguments[0], Int32(arguments.count), argumentsPointer, argv.utf8.count + 1,
                        environmentPointer, environment.utf8.count + 1, workspace.path, &descriptors,
                        { context, status in
                            let value = Unmanaged<PackagedCommandExit>.fromOpaque(context!).takeRetainedValue()
                            value.status = status
                            value.finished.signal()
                        }, context, &pid, &generation)
                }
            }
            XCTAssertEqual(started, 0, "command phase \(index)")
            if exit.finished.wait(timeout: .now() + (index == 3 ? 30 : 8)) != .success {
                _ = IMDreamGuestKillGroup(pid, 9, generation)
                XCTFail("Packaged command phase \(index) timed out")
                return
            }
            let text = try String(contentsOf: outputPath, encoding: .utf8)
            print("IOS_COMMAND_STARTUP phase=\(index) status=\(exit.status) bytes=\(text.utf8.count)")
            XCTAssertEqual(exit.status, 0, text)
            if index == 0 { XCTAssertTrue(text.contains("GNU bash"), text) }
            if index == 1 { XCTAssertTrue(text.contains("native-sharednative-ok"), text) }
            if index == 2 { XCTAssertTrue(text.contains("login-ok"), text) }
            if index == 3 { XCTAssertTrue(text.contains("plugin-python-ok"), text) }
        }
        XCTAssertEqual(try String(contentsOf: workspace.appendingPathComponent("command-written.txt"), encoding: .utf8), "native-shared")
        XCTAssertEqual(try String(contentsOf: temporary.appendingPathComponent("cwd"), encoding: .utf8).trimmingCharacters(in: .newlines), workspace.path)
        completed = true
    }

    func testConfiguredAdminPublicHttpTransport() throws {
        _ = try execute(timeout: 120) { EmbeddedDreamBackend.shared.start(completion: $0) }
        try runPython("""
        import httpx, json, requests, ssl, time
        from services.admin_data.config import AdminDataConfig
        from services.admin_gateway.config import AdminGatewayConfig
        _ios_probe_config = AdminDataConfig.from_env()
        assert AdminGatewayConfig.from_environment().base_url == _ios_probe_config.transport_origin
        _ios_probe_url = _ios_probe_config.transport_origin + '/auth/sign-in'
        _ios_probe_results = []
        _ios_probe_error_types = frozenset(('ConnectionError', 'ConnectError', 'ConnectTimeout',
            'ConnectTimeoutError', 'ConnectionResetError', 'TimeoutError', 'ReadTimeout',
            'ReadTimeoutError', 'Timeout', 'SSLError', 'SSLCertVerificationError', 'CertificateError',
            'ProtocolError', 'RemoteProtocolError', 'RemoteDisconnected', 'MaxRetryError', 'ProxyError',
            'NewConnectionError', 'NameResolutionError', 'gaierror', 'IncompleteRead',
            'ChunkedEncodingError', 'ContentDecodingError', 'BrokenPipeError', 'OSError', 'EOFError',
            'ValueError', 'InvalidURL', 'UnsupportedProtocol'))
        _ios_probe_ssl_reasons = frozenset(('CERTIFICATE_VERIFY_FAILED', 'TLSV1_ALERT_DECODE_ERROR',
            'DECRYPTION_FAILED_OR_BAD_RECORD_MAC', 'UNEXPECTED_EOF_WHILE_READING',
            'SSLV3_ALERT_HANDSHAKE_FAILURE', 'TLSV1_ALERT_INTERNAL_ERROR', 'WRONG_VERSION_NUMBER',
            'UNSUPPORTED_PROTOCOL', 'TLSV1_ALERT_PROTOCOL_VERSION', 'TLSV1_ALERT_DECRYPT_ERROR',
            'SSLV3_ALERT_BAD_RECORD_MAC'))
        def _ios_probe_failure_metadata(failure):
            pending, seen, rows = [failure], set(), []
            while pending and len(rows) < 8:
                current = pending.pop(0)
                if id(current) in seen:
                    continue
                seen.add(id(current))
                name = type(current).__name__
                row = {'type': name if name in _ios_probe_error_types else 'OTHER_EXCEPTION'}
                number = getattr(current, 'errno', None)
                if type(number) is int and -4096 <= number <= 65535:
                    row['errno'] = number
                if isinstance(current, ssl.SSLError):
                    reason = getattr(current, 'reason', None)
                    row['ssl_reason'] = reason if reason in _ios_probe_ssl_reasons else 'other'
                rows.append(row)
                nested = [current.__cause__, current.__context__, getattr(current, 'reason', None),
                    *current.args]
                pending.extend(value for value in nested if isinstance(value, BaseException))
            return rows
        _ios_probe_timeout = min(10.0, _ios_probe_config.timeout_seconds)
        with httpx.Client(timeout=_ios_probe_timeout, follow_redirects=False, trust_env=False) as _ios_probe_client:
            for _ios_probe_mode in ('httpx', 'requests'):
                for _ios_probe_index in range(3):
                    _ios_probe_started = time.monotonic()
                    _ios_probe_status, _ios_probe_errors = 0, []
                    try:
                        if _ios_probe_mode == 'httpx':
                            with _ios_probe_client.stream('GET', _ios_probe_url) as _ios_probe_response:
                                _ios_probe_status = _ios_probe_response.status_code
                                for _ios_probe_chunk in _ios_probe_response.iter_bytes():
                                    pass
                        else:
                            with requests.get(_ios_probe_url, timeout=_ios_probe_timeout, allow_redirects=False) as _ios_probe_response:
                                _ios_probe_status = _ios_probe_response.status_code
                    except (httpx.HTTPError, requests.RequestException) as _ios_probe_failure:
                        _ios_probe_errors = _ios_probe_failure_metadata(_ios_probe_failure)
                    _ios_probe_result = {'mode': _ios_probe_mode, 'index': _ios_probe_index + 1,
                        'status': _ios_probe_status, 'errors': _ios_probe_errors,
                        'elapsed_ms': round((time.monotonic() - _ios_probe_started) * 1000, 1)}
                    _ios_probe_results.append(_ios_probe_result)
                    print('IOS_ADMIN_PUBLIC_HTTP_PROBE ' + json.dumps(_ios_probe_result), flush=True)
        assert len(_ios_probe_results) == 6
        assert all(row['status'] == 200 and not row['errors'] for row in _ios_probe_results)
        print('IOS_ADMIN_PUBLIC_HTTP_PROOF requests=6 accountRequests=0 modelRequests=0', flush=True)
        """)
    }

    private func runPython(_ source: String) throws {
        try runEmbeddedPythonQualification(source)
    }

    private func execute(timeout: TimeInterval = 30, _ operation: (@escaping (Result<[String: Any], Error>) -> Void) -> Void) throws -> [String: Any] {
        let completed = expectation(description: "Embedded Python returned")
        var response: Result<[String: Any], Error>?
        operation { value in response = value; completed.fulfill() }
        wait(for: [completed], timeout: timeout)
        return try XCTUnwrap(response).get()
    }

    func testBundledPluginsWithOriginalCLI() throws {
        _ = try execute(timeout: 120) { EmbeddedDreamBackend.shared.start(completion: $0) }
        try runEmbeddedPythonQualification("""
        import json
        import re
        from pathlib import Path
        from mobile_runtime import ios
        from services.claude_plugin import artifact_store, cli, runtime
        bundle = Path(ios.__file__).parents[2] / 'plugin-artifacts'
        records = json.loads((bundle / 'manifest.json').read_text())
        assert records, 'IOS_PLUGIN_ARTIFACTS_MISSING'
        version = cli.get_cli_version()
        assert version and version != 'unknown', 'IOS_PLUGIN_CLI_VERSION_INVALID'
        failures = []
        for record in records:
            artifact = artifact_store.get_artifact(record['package_name'], record['marketplace'], record['digest'])
            result = cli.run_claude(['plugin', 'validate', str(artifact.path)], cwd=runtime.get_install_workspace(), timeout_seconds=30)
            fields = re.findall(r'^  [^A-Za-z0-9]*([A-Za-z0-9_.\\[\\]-]+):', result.stdout, re.M)
            print('IOS_PLUGIN_CLI_RECEIPT ' + json.dumps(dict(package=record['package_name'], digest=record['digest'], exitCode=result.exit_code, timedOut=result.timed_out, fields=fields)), flush=True)
            if not result.ok:
                failures.append(record['package_name'])
        assert not failures, 'IOS_PLUGIN_CLI_VALIDATE_FAILED ' + ','.join(failures)
        print('IOS_ORIGINAL_PLUGIN_PROOF ' + json.dumps(dict(artifactCount=len(records), originalCLI=True, versionAndHelp=True, validated=True, modelRequests=0)), flush=True)
        """)
    }

    func testManagedPluginPythonWithOriginalRequirements() throws {
        _ = try execute(timeout: 120) { EmbeddedDreamBackend.shared.start(completion: $0) }
        try runEmbeddedPythonQualification("""
        import json
        from pathlib import Path
        from mobile_runtime import ios, ios_plugin_runtime
        from services.claude_plugin import artifact_store, runtime, workspace_init
        resources = Path(ios.__file__).parents[2]
        records = json.loads((resources / 'plugin-artifacts/manifest.json').read_text())
        count = 0
        cli_count = 0
        for record in records:
            artifact = artifact_store.get_artifact(record['package_name'], record['marketplace'], record['digest'])
            profile = workspace_init.load_init_profile(artifact.path)
            if profile is None or profile.python is None:
                continue
            print('IOS_PLUGIN_PYTHON_STAGE ' + json.dumps(dict(package=record['package_name'], phase='ensure-venv')), flush=True)
            venv = workspace_init.ensure_plugin_venv(runtime.get_runtime_root(), record['digest'], artifact.path, profile.python)
            result = ios_plugin_runtime._run_native_python(ios._claude_endpoint,
                [str(venv / 'bin/python3'), '-c', 'import yaml, frontmatter, markdown_it, click, rich, jsonschema, jinja2, rapidfuzz, watchdog; print("plugin-imports-ok")'],
                capture_output=True, text=True, timeout=90, check=False)
            assert result.returncode == 0 and 'plugin-imports-ok' in result.stdout, 'IOS_PLUGIN_PYTHON_IMPORT_FAILED'
            script = artifact.path / 'scripts/dramaforge.py'
            if script.is_file():
                command = ios_plugin_runtime._run_native_python(ios._claude_endpoint,
                    [str(venv / 'bin/python3'), str(script), '--help'],
                    capture_output=True, text=True, timeout=90, check=False)
                assert command.returncode == 0 and 'usage:' in command.stdout, 'IOS_PLUGIN_PYTHON_CLI_FAILED'
                cli_count += 1
            count += 1
        assert count > 0, 'IOS_PLUGIN_PYTHON_PROFILE_MISSING'
        assert cli_count > 0, 'IOS_PLUGIN_PYTHON_CLI_MISSING'
        print('IOS_PLUGIN_PYTHON_PROOF ' + json.dumps(dict(pluginCount=count, originalRequirements=True, managedVenv=True, offlineWheels=True, imports=True, originalCLISmoke=cli_count, modelRequests=0)), flush=True)
        """)
    }

    func testActualIOSPythonAndSharedDreamHandlers() throws {
        let backend = EmbeddedDreamBackend.shared
        let startup = try execute { backend.start(completion: $0) }
        XCTAssertEqual(startup["platform"] as? String, "ios")
        XCTAssertEqual(startup["pythonVersion"] as? String, "3.13.17")
#if targetEnvironment(simulator)
        XCTAssertEqual(startup["simulator"] as? Bool, true)
#else
        XCTAssertEqual(startup["simulator"] as? Bool, false)
#endif
        XCTAssertEqual(startup["businessReady"] as? Bool, false)
        XCTAssertEqual((startup["health"] as? [String: Any])?["status"] as? String, "ok")

        let health = try execute { backend.request(method: "GET", path: "/api/health", completion: $0) }
        XCTAssertEqual(health["status"] as? Int, 200)
        let body = try XCTUnwrap(health["body"] as? String)
        let json = try JSONSerialization.jsonObject(with: Data(body.utf8)) as? [String: Any]
        XCTAssertEqual(json?["version"] as? String, "0.1.4")
        let content = try execute { backend.request(method: "GET", path: "/llms.txt", completion: $0) }
        XCTAssertEqual(content["status"] as? Int, 200)
        XCTAssertTrue((content["body"] as? String)?.contains("Ink & Memory") == true)
        let missing = try execute { backend.request(method: "GET", path: "/api/not-mounted", completion: $0) }
        XCTAssertEqual(missing["status"] as? Int, 404)
        XCTAssertEqual((startup["businessRouterModules"] as? [String])?.count, 24)
        try runPython("""
        import sys
        from services.memory.behavior import MemoryTurnProvider
        from services.memory.documents import POLICIES, REVISION
        assert REVISION in POLICIES and len(POLICIES) == 2
        from story_workspace.dream_workbench_context import load_dream_workbench_contract, load_dream_asset_collaboration_contract
        assert load_dream_workbench_contract().strip()
        assert load_dream_asset_collaboration_contract().strip()
        from mobile_runtime.ios_resources import read_ios_resource_snapshot
        from claude_agent.runtime_owner import get_thread_factory
        from claude_agent.thread_factory import ClaudeAgentThreadFactory
        assert 'agent_factory' not in sys.modules
        assert isinstance(get_thread_factory(), ClaudeAgentThreadFactory)
        from services.deck.story_workflow_application import story_workspace_get_dream_confirmation_coordinator
        from services.admin_data.story_workspace_confirmation_data import AdminStoryWorkspaceConfirmationWorkerData
        coordinator = story_workspace_get_dream_confirmation_coordinator()
        assert isinstance(coordinator._worker, AdminStoryWorkspaceConfirmationWorkerData)
        assert coordinator._loop_task is None
        available = read_ios_resource_snapshot().host_available_bytes
        assert isinstance(available, int) and available > 0
        print('IOS_MEMORY_PROOF headroomBytes=' + str(available), flush=True)
        """)
        let defaults = try execute { backend.request(method: "GET", path: "/api/default-voices", completion: $0) }
        XCTAssertEqual(defaults["status"] as? Int, 200)
        let defaultsBody = try XCTUnwrap(defaults["body"] as? String)
        let voices = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(defaultsBody.utf8)) as? [String: [String: Any]])
        XCTAssertEqual(voices.count, 5)
        XCTAssertTrue(voices.values.allSatisfy { !(($0["systemPrompt"] as? String) ?? "").isEmpty })
        for path in ["/api/me", "/api/sessions?limit=2", "/api/decks", "/api/preferences", "/api/reports"] {
            let response = try execute { backend.request(method: "GET", path: path, completion: $0) }
            XCTAssertEqual(response["status"] as? Int, 401, path)
        }
        let protectedWrite = try execute {
            backend.request(method: "POST", path: "/api/sessions", headers: ["Content-Type": "application/json"],
                            body: Data("{}".utf8), completion: $0)
        }
        XCTAssertEqual(protectedWrite["status"] as? Int, 401)
        XCTAssertThrowsError(try execute { backend.request(method: "GET", path: "/api/me", headers: ["Authorization": "not-a-credential"], completion: $0) })
        let reopened = try execute { backend.start(completion: $0) }
        XCTAssertEqual(reopened["pythonVersion"] as? String, startup["pythonVersion"] as? String)
        print("EMBEDDED_DREAM_PROOF platform=ios python=3.13.17 businessModules=24 defaults=200 protectedReadWrite=401 missing=404 businessReady=false")
    }

    func testTargetInterpreterProcessExecutionBoundary() throws {
        let startup = try execute { EmbeddedDreamBackend.shared.start(completion: $0) }
        XCTAssertEqual(startup["platform"] as? String, "ios")

        // Keep introspection in the test bundle; application code exposes no eval entry.
        typealias EnsureGIL = @convention(c) () -> Int32
        typealias ReleaseGIL = @convention(c) (Int32) -> Void
        typealias RunPython = @convention(c) (UnsafePointer<CChar>, UnsafeMutableRawPointer?) -> Int32
        let handle = try XCTUnwrap(dlopen(nil, RTLD_NOW))
        defer { dlclose(handle) }
        let ensure = unsafeBitCast(try XCTUnwrap(dlsym(handle, "PyGILState_Ensure")), to: EnsureGIL.self)
        let release = unsafeBitCast(try XCTUnwrap(dlsym(handle, "PyGILState_Release")), to: ReleaseGIL.self)
        let run = unsafeBitCast(try XCTUnwrap(dlsym(handle, "PyRun_SimpleStringFlags")), to: RunPython.self)
        let gil = ensure()
        defer { release(gil) }
        let probe = """
        import json, subprocess, sys
        assert sys.platform == 'ios', 'Target interpreter required'
        proof = {'platform': sys.platform, 'canForkExec': subprocess._can_fork_exec}
        assert proof['canForkExec'] is False, 'Reassess process support before executing this probe'
        try:
            subprocess.run([sys.executable, '--version'], capture_output=True, timeout=2, check=True)
        except OSError as failure:
            proof.update(errorType=type(failure).__name__, errno=failure.errno, message=str(failure))
        else:
            raise AssertionError('The target unexpectedly created a child process')
        print('IOS_PROCESS_EXECUTION_PROOF ' + json.dumps(proof, sort_keys=True), flush=True)
        """
        XCTAssertEqual(probe.withCString { run($0, nil) }, 0)
    }

    func testTargetCryptoAndImageCodecs() throws {
        _ = try execute { EmbeddedDreamBackend.shared.start(completion: $0) }
        try runPython("""
        import io, json
        import jwt
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from PIL import Image
        key = ec.generate_private_key(ec.SECP256R1())
        token = jwt.encode({'sub': 'target-codec-fixture', 'aud': 'codec-fixture'}, key, algorithm='ES256')
        assert jwt.decode(token, key.public_key(), algorithms=['ES256'], audience='codec-fixture')['sub'] == 'target-codec-fixture'
        cipher = AESGCM(AESGCM.generate_key(bit_length=256))
        nonce, clear, aad = b'\\0' * 12, b'codec-fixture', b'target'
        encrypted = cipher.encrypt(nonce, clear, aad)
        assert cipher.decrypt(nonce, encrypted, aad) == clear
        try:
            cipher.decrypt(nonce, encrypted[:-1] + bytes([encrypted[-1] ^ 1]), aad)
            raise AssertionError('Modified ciphertext must be rejected')
        except InvalidTag:
            pass
        for format in ('PNG', 'JPEG', 'WEBP'):
            data = io.BytesIO()
            Image.new('RGB', (2, 2), (12, 24, 36)).save(data, format=format)
            data.seek(0)
            with Image.open(data) as restored:
                restored.load()
                assert restored.size == (2, 2) and restored.format == format
        print('IOS_CODEC_PROOF es256=true aesGcm=true tamperRejected=true png=true jpeg=true webp=true', flush=True)
        """)
    }

    func testOriginalASGIOverApplicationHTTP() throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let startup = try execute { EmbeddedDreamBackend.shared.start(completion: $0) }
        let origin = try XCTUnwrap(startup["localBackendOrigin"] as? String)
        XCTAssertTrue(origin.hasPrefix("http://127.0.0.1:"))
        try runPython("""
        import asyncio, httpx, json
        from mobile_runtime import ios
        from starlette.responses import StreamingResponse
        async def http_stream_content():
            try:
                yield b'data: application-http\\n\\n'
                await asyncio.Future()
            finally:
                http_stream_disconnected.set()
        async def http_stream_route():
            return StreamingResponse(http_stream_content(), media_type='text/event-stream')
        async def qualify_http():
            global http_stream_disconnected
            http_stream_disconnected = asyncio.Event()
            assert ios._http_owner._app is ios._app
            assert not ios._http_owner._task.done()
            ios._app.add_api_route('/__ios_http_stream_qualification', http_stream_route, methods=['GET'])
            async with httpx.AsyncClient(base_url=ios._http_owner.origin, trust_env=False, timeout=5) as client:
                assert (await client.get('/api/health')).json()['status'] == 'ok'
                voices = await client.get('/api/default-voices')
                assert voices.status_code == 200 and len(voices.json()) == 5
                assert (await client.get('/api/claude-agent/threads')).status_code == 401
                assert (await client.post('/api/sessions', json={})).status_code == 401
                async with client.stream('GET', '/__ios_http_stream_qualification') as stream:
                    assert stream.status_code == 200
                    assert await asyncio.wait_for(anext(stream.aiter_bytes()), timeout=2) == b'data: application-http\\n\\n'
                await asyncio.wait_for(http_stream_disconnected.wait(), timeout=2)
            print('IOS_APPLICATION_HTTP_PROOF sameASGI=true health=200 defaults=200 protectedReadWrite=401 incrementalSse=true disconnect=true relay=disabled', flush=True)
        ios._submit(qualify_http())
        """)
    }

    func testOriginalNextStandaloneInApplicationProcess() throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        let resources = try XCTUnwrap(Bundle.main.resourceURL)
        XCTAssertFalse(FileManager.default.fileExists(atPath: resources.appendingPathComponent("web/index.html").path))
        let startup = try execute { EmbeddedDreamBackend.shared.start(completion: $0) }
        let origin = URL(string: try XCTUnwrap(startup["localWebOrigin"] as? String))
        XCTAssertEqual(origin?.scheme, "http")
        XCTAssertTrue(["127.0.0.1", "localhost", "::1", "[::1]"].contains(origin?.host ?? ""))
        try runPython("""
        import httpx, json, re
        from pathlib import Path
        from mobile_runtime import ios
        from mobile_runtime.ios_claude_transport import query_native_status
        async def qualify_original_next():
            status = await query_native_status(ios._claude_endpoint)
            web = status['web']
            assert status['platform'] == 'ios' and status['execution'] == 'application-process'
            assert web['state'] == 'listening' and web['origin'] == ios._web_origin
            assert web['backendOrigin'] == ios._http_owner.origin
            async with httpx.AsyncClient(base_url=ios._web_origin, trust_env=False, timeout=10) as client:
                page = await client.get('/')
                assert page.status_code == 200 and '<html' in page.text
                assets = {value for value in re.findall(r'(?:src|href)="([^"]+)"', page.text) if value.startswith('/_next/static/')}
                assert len(assets) >= 2, 'Original Next page must reference actual web assets'
                for asset in sorted(assets):
                    resource = await client.get(asset)
                    assert resource.status_code == 200 and resource.content, asset
                health = await client.get('/api/health')
                assert health.status_code == 200 and health.json()['service'] == 'ink-memory-web'
                backend_resource = await client.get('/llms.txt')
                assert backend_resource.status_code == 200 and 'Ink & Memory' in backend_resource.text
                auth = await client.get('/auth/options')
                configured = (Path(ios.__file__).parents[1] / '.env').is_file()
                assert auth.status_code == (200 if configured else 503)
                if configured:
                    assert set(auth.json()) == {'password_action', 'google_action'}
                    assert auth.json()['password_action'].endswith('/auth/dream/password')
                    assert auth.json()['google_action'].endswith('/auth/dream/google')
                else:
                    assert auth.json()['detail'] == 'BFF_CONFIGURATION_INVALID'
            print(f'IOS_NEXT_HTTP_PROOF sameApplicationProcess=true platform=ios originalPage=200 originalAssets=200 originalHealth=200 originalBackendProxy=200 authConfiguration={auth.status_code} relay=disabled', flush=True)
        ios._submit(qualify_original_next())
        """)
    }

    func testOriginalNextStreamingProxyCompletes() throws {
        _ = try execute { EmbeddedDreamBackend.shared.start(completion: $0) }
        try runPython("""
        import asyncio, httpx
        from starlette.requests import Request
        from mobile_runtime import ios
        from claude_agent.sse import encode_json_sse, streaming_sse_response
        async def qualify_next_sse():
            gate = asyncio.Event()
            async def content():
                yield encode_json_sse('text-start', {'id': 'ios-next-fixture'})
                await gate.wait()
                yield encode_json_sse('text-delta', {'id': 'ios-next-fixture', 'delta': 'stream fixture'})
                yield encode_json_sse('text-end', {'id': 'ios-next-fixture'})
                yield encode_json_sse('finish', {'finishReason': 'stop'})
            async def endpoint(request: Request):
                assert request.headers.get('authorization') == 'Bearer ios-next-stream-fixture'
                return streaming_sse_response(content())
            path = '/api/__ios_next_stream_fixture'
            ios._app.add_api_route(path, endpoint, methods=['GET'])
            fixture_route = ios._app.router.routes[-1]
            try:
                async with httpx.AsyncClient(base_url=ios._web_origin, trust_env=False, timeout=5) as client:
                    async with client.stream('GET', path, headers={'authorization': 'Bearer ios-next-stream-fixture'}) as response:
                        assert response.status_code == 200, response.status_code
                        assert response.headers['content-type'].startswith('text/event-stream')
                        chunks = response.aiter_bytes()
                        first = await asyncio.wait_for(anext(chunks), timeout=5)
                        assert first.decode() == encode_json_sse('text-start', {'id': 'ios-next-fixture'})
                        gate.set()
                        async def read_tail():
                            return b''.join([chunk async for chunk in chunks])
                        tail = (await asyncio.wait_for(read_tail(), timeout=5)).decode()
                        assert tail.endswith(encode_json_sse('finish', {'finishReason': 'stop'}))
                print('IOS_NEXT_SSE_PROOF originalProxy=true incremental=true terminalEof=true modelRequests=0', flush=True)
            finally:
                gate.set()
                ios._app.router.routes.remove(fixture_route)
        ios._submit(qualify_next_sse())
        """)
    }

    func testOriginalRuntimeInitializesInApplicationProcess() throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        _ = try execute { EmbeddedDreamBackend.shared.start(completion: $0) }
        var failure: NSError?
        let endpoint = try XCTUnwrap(IMDreamNodeStart(try XCTUnwrap(Bundle.main.resourcePath), &failure))
        let deadline = Date().addingTimeInterval(15)
        while !FileManager.default.fileExists(atPath: endpoint) && Date() < deadline { Thread.sleep(forTimeInterval: 0.05) }
        XCTAssertTrue(FileManager.default.fileExists(atPath: endpoint), "The embedded Node library must publish its own endpoint")
        let literal = String(decoding: try JSONSerialization.data(withJSONObject: endpoint, options: [.fragmentsAllowed, .withoutEscapingSlashes]), as: UTF8.self)
        try runPython("""
        import json, os, shutil, sys, uuid
        from pathlib import Path
        import anyio
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        from mobile_runtime.ios_claude_transport import IOSClaudeTransport, read_native_endpoint
        endpoint_path = \(literal)
        endpoint = read_native_endpoint(endpoint_path)
        assert endpoint['pid'] == os.getpid()
        assert sys.platform == 'ios'
        workspace = Path(endpoint['workspaceRoot']) / ('qualification-' + uuid.uuid4().hex)
        workspace.mkdir(mode=0o700)
        home = workspace / '.home'
        home.mkdir(mode=0o700)
        tmp = workspace / '.claude-tmp'
        tmp.mkdir(mode=0o700)
        async def qualify():
            options = ClaudeAgentOptions(cwd=str(workspace), tools=[], env={
                'HOME': str(home), 'CLAUDE_CONFIG_DIR': str(home / '.claude'),
                'CLAUDE_CODE_TMPDIR': str(tmp), 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
            }, stderr=lambda line: print('IOS_RUNTIME_STDERR ' + line, flush=True))
            transport = IOSClaudeTransport(endpoint_path=endpoint_path, options=options)
            with anyio.fail_after(25):
                async with ClaudeSDKClient(options=options, transport=transport) as client:
                    info = await client.get_server_info()
                    assert isinstance(info, dict), 'Original SDK initialize response required'
                    print('IOS_ORIGINAL_RUNTIME_PROOF ' + json.dumps({
                        'platform': sys.platform, 'nodeVersion': endpoint['nodeVersion'],
                        'sameApplicationProcess': endpoint['pid'] == os.getpid(),
                        'initializeKeys': sorted(info), 'commandCount': len(info.get('commands', [])),
                    }), flush=True)
        try:
            anyio.run(qualify)
        finally:
            shutil.rmtree(workspace)
        """)
    }

    func testOriginalRuntimeProtocolWithoutExternalProvider() throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        // Startup retains configured service-token/capability/policy reads.
        // Their original deadlines can exceed the old public-only 30s budget.
        let startup = try execute(timeout: 120) { EmbeddedDreamBackend.shared.start(completion: $0) }
        XCTAssertEqual((startup["embeddedNode"] as? [String: Any])?["execution"] as? String, "application-process")
        var failure: NSError?
        let endpoint = try XCTUnwrap(IMDreamNodeStart(try XCTUnwrap(Bundle.main.resourcePath), &failure))
        let fixture = try XCTUnwrap(Bundle(for: EmbeddedDreamBackendTests.self).path(forResource: "ios_runtime_qualification", ofType: "py"))
        func literal(_ value: String) throws -> String {
            String(decoding: try JSONSerialization.data(withJSONObject: value, options: [.fragmentsAllowed, .withoutEscapingSlashes]), as: UTF8.self)
        }
        try runPython("import runpy; runpy.run_path(\(try literal(fixture)))['run'](\(try literal(endpoint)))")
    }

    func testOriginalDreamRunnerWithoutExternalProvider() throws {
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "InkDreamDevelopmentHost") as? String ?? "", "")
        _ = try execute(timeout: 120) { EmbeddedDreamBackend.shared.start(completion: $0) }
        var failure: NSError?
        let endpoint = try XCTUnwrap(IMDreamNodeStart(try XCTUnwrap(Bundle.main.resourcePath), &failure))
        let fixture = try XCTUnwrap(Bundle(for: EmbeddedDreamBackendTests.self).path(forResource: "ios_runtime_qualification", ofType: "py"))
        func literal(_ value: String) throws -> String {
            String(decoding: try JSONSerialization.data(withJSONObject: value, options: [.fragmentsAllowed, .withoutEscapingSlashes]), as: UTF8.self)
        }
        try runPython("import runpy; runpy.run_path(\(try literal(fixture)))['run_runner'](\(try literal(endpoint)))")
    }

    func testNativePullStreamAndConcurrentCancellation() throws {
        let backend = EmbeddedDreamBackend.shared
        _ = try execute { backend.start(completion: $0) }
        try runPython("""
        import asyncio
        from mobile_runtime import ios
        from starlette.responses import StreamingResponse
        async def _ios_fixture_content():
            yield b'data: ios-stream\\n\\n'
            await asyncio.Future()
        async def _ios_fixture_route():
            return StreamingResponse(_ios_fixture_content(), media_type='text/event-stream')
        ios._app.add_api_route('/__ios_transport_qualification', _ios_fixture_route, methods=['GET'])
        """)
        let generation = "test_" + UUID().uuidString
        let identifier = "request_" + UUID().uuidString
        let head = try execute {
            backend.bridge(MobileBridgeRequest(id: "open", pageGeneration: generation, method: "runtime.request", params: [
                "clientRequestId": identifier, "method": "GET", "path": "/__ios_transport_qualification",
            ]), completion: $0)
        }
        XCTAssertEqual(head["status"] as? Int, 200)
        let stream = try XCTUnwrap(head["streamId"] as? String)
        let params: [String: Any] = ["requestId": identifier, "streamId": stream]
        let first = try execute {
            backend.bridge(MobileBridgeRequest(id: "first", pageGeneration: generation, method: "runtime.response.read", params: params), completion: $0)
        }
        XCTAssertEqual(first["done"] as? Bool, false)
        XCTAssertEqual(Data(base64Encoded: try XCTUnwrap(first["dataBase64"] as? String)), Data("data: ios-stream\n\n".utf8))
        let pending = expectation(description: "Pending read is released")
        let cancelled = expectation(description: "Cancellation executes beside pending read")
        backend.bridge(MobileBridgeRequest(id: "pending", pageGeneration: generation, method: "runtime.response.read", params: params)) { result in
            if case .success = result { XCTFail("Cancelled stream returned a successful read") }
            pending.fulfill()
        }
        try runPython("""
        async def _ios_wait_for_pending_read():
            for _ in range(200):
                if any(state.reading for state in ios._transport.responses.values()):
                    return
                await asyncio.sleep(0.01)
            raise AssertionError('Native read did not enter the persistent event loop')
        ios._submit(_ios_wait_for_pending_read())
        """)
        backend.bridge(MobileBridgeRequest(id: "cancel", pageGeneration: generation, method: "runtime.cancel", params: params)) { result in
            do { XCTAssertEqual(try result.get()["cancelled"] as? Bool, true) }
            catch { XCTFail("Native cancellation failed: \(error)") }
            cancelled.fulfill()
        }
        wait(for: [pending, cancelled], timeout: 10)
        backend.closeDocument(generation)
        try runPython("ios._app.router.routes[:] = [route for route in ios._app.router.routes if route.path != '/__ios_transport_qualification']")
        print("IOS_NATIVE_STREAM_PROOF head=200 body=incremental pendingRead=cancelled relay=disabled")
    }
}
