# [Input] Current native Admin transport source and isolated Foundation URLProtocol fixtures.
# [Output] Executed byte/deadline/cancellation and fixed authentication recovery contracts, without external requests.
# [Pos] Explicit macOS source-contract validation; iPhone business acceptance remains independent.
# [Sync] 2026-10-31: cover one pre-header read recovery, preserved deadlines and single-dispatch write boundaries.
# [Sync] 2026-11-01: verify failed-pool retirement, deadline hints and draining concurrent tasks through the current source.
from pathlib import Path
import json, subprocess, hashlib
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',required=True)
stage=Path(parser.parse_args().output_dir).resolve()
stage.mkdir(parents=True,exist_ok=True)
source=(Path(__file__).resolve().parents[1]/'InkMemory/InkReactNative.swift').read_text()
actual=source[source.index('final class NativeHTTPResponse:'):]
prelude='''import Foundation
import Darwin
typealias RCTPromiseRejectBlock = (String?, String?, Error?) -> Void
typealias RCTPromiseResolveBlock = (Any?) -> Void
final class UIApplication {
    static let shared = UIApplication()
    let applicationState = State()
    struct State { let rawValue = 0 }
}
'''
fixture=r'''
final class FixtureProtocol: URLProtocol {
    static let lock = NSLock()
    static var calls: [(String, String)] = []
    static var cases: [String: Int] = [:]
    override class func canInit(with request: URLRequest) -> Bool { request.url?.host == "native-admin.invalid" }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let path = request.url!.path
        let mode = request.value(forHTTPHeaderField: "X-Fixture-Case") ?? ""
        Self.lock.lock(); Self.calls.append((path, request.httpMethod ?? "GET")); Self.cases[mode, default: 0] += 1; let attempt = Self.cases[mode]!; Self.lock.unlock()
        if mode == "headers-lost" {
            client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: ["Content-Length":"5", "Content-Type":"application/octet-stream"])!, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: Data([65]))
            // Let URLSession deliver the head and accept .allow before failing
            // the body; an immediate fixture failure can discard its own head.
            DispatchQueue.main.asyncAfter(deadline: .now()+0.05) { self.client?.urlProtocol(self, didFailWithError: URLError(.networkConnectionLost)) }
            return
        }
        if mode == "deadline-recovery" {
            if attempt == 1 { DispatchQueue.main.asyncAfter(deadline: .now()+1.3) { self.client?.urlProtocol(self, didFailWithError: URLError(.networkConnectionLost)) } }
            return
        }
        if mode.contains("always-lost") || (mode.contains("lost-once") && attempt == 1) {
            client?.urlProtocol(self, didFailWithError: URLError(.networkConnectionLost)); return
        }
        if path == "/slow" { return }
        if path == "/drain" {
            DispatchQueue.main.asyncAfter(deadline: .now()+0.15) {
                self.client?.urlProtocol(self, didReceive: HTTPURLResponse(url: self.request.url!, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: ["Content-Type":"application/octet-stream"])!, cacheStoragePolicy: .notAllowed)
                self.client?.urlProtocol(self, didLoad: Data([65]))
                self.client?.urlProtocolDidFinishLoading(self)
            }
            return
        }
        let headers = ["Content-Type": "application/octet-stream", "Retry-After": "3", "Set-Cookie": "fixture=not-a-real-session; Secure"]
        if path == "/redirect" {
            let response = HTTPURLResponse(url: request.url!, statusCode: 302, httpVersion: "HTTP/1.1", headerFields: ["Location": "https://native-admin.invalid/trap"])!
            client?.urlProtocol(self, wasRedirectedTo: URLRequest(url: URL(string: "https://native-admin.invalid/trap")!), redirectResponse: response)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocolDidFinishLoading(self)
            return
        }
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!, cacheStoragePolicy: .notAllowed)
        if path == "/text" {
            for byte in "中🙂".data(using: .utf8)! { client?.urlProtocol(self, didLoad: Data([byte])) }
        } else {
            client?.urlProtocol(self, didLoad: Data([255, 0, 195, 40, 65]))
        }
        if path != "/held" { client?.urlProtocolDidFinishLoading(self) }
    }
    override func stopLoading() {}
}
final class CancellationFlag {
    private let lock = NSLock(); private var value = false
    func cancel() { lock.lock(); value = true; lock.unlock() }
    func read() -> Bool { lock.lock(); defer { lock.unlock() }; return value }
}
func configuration() -> URLSessionConfiguration {
    let config = URLSessionConfiguration.ephemeral; config.protocolClasses = [FixtureProtocol.self]; return config
}
func run(_ path: String, maximum: Int = 100, headers: [String: String] = [:], method: String = "GET", sharedSession: URLSession? = nil, sessionProvider: (() -> URLSession)? = nil, sessionFailed: ((URLSession) -> Void)? = nil, cancelled: @escaping () -> Bool = { false }, timedOut: @escaping () -> Bool = { false }) -> [String: Any] {
    let payload: [String: Any] = ["url": "https://native-admin.invalid" + path, "method": method, "headers": headers, "timeoutSeconds": 2, "maxResponseBytes": maximum, "traceId": UUID().uuidString]
    let config = configuration()
    let text = performNativeAdminHTTP(String(decoding: try! JSONSerialization.data(withJSONObject: payload), as: UTF8.self), cancelled: cancelled, configuration: config, sharedSession: sharedSession, sessionProvider: sessionProvider, sessionFailed: sessionFailed, timedOut: timedOut)
    guard let result = try! JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] else { fatalError("invalid result envelope") }
    if result["ok"] as? Bool == true { precondition(config.httpCookieStorage == nil && !config.httpShouldSetCookies) }
    return result
}
DispatchQueue.global().asyncAfter(deadline: .now() + 20) { fputs("native fixture deadline exceeded\n", stderr); exit(1) }
DispatchQueue.global().async {
    let bytes = run("/bytes")
    precondition(bytes["ok"] as? Bool == true && bytes["status"] as? Int == 200)
    precondition(Data(base64Encoded: bytes["bodyBase64"] as! String) == Data([255, 0, 195, 40, 65]))
    let projected = bytes["headers"] as! [String: String]
    precondition(projected["retry-after"] == "3" && projected["set-cookie"] == nil)
    let limited = run("/bytes", maximum: 2)
    precondition(Data(base64Encoded: limited["bodyBase64"] as! String) == Data([255, 0, 195]))
    let before = FixtureProtocol.calls.count
    precondition(run("/bytes", headers: ["Cookie": "fixture"])["error"] as? String == "configuration")
    precondition(run("/bytes", cancelled: { true })["error"] as? String == "cancelled")
    precondition(FixtureProtocol.calls.count == before)
    let redirected = run("/redirect", method: "POST")
    precondition(redirected["status"] as? Int == 302)
    precondition(!FixtureProtocol.calls.contains(where: { $0.0 == "/trap" }))
    let flag = CancellationFlag()
    DispatchQueue.global().asyncAfter(deadline: .now() + 0.15) { flag.cancel() }
    let started = ProcessInfo.processInfo.systemUptime
    precondition(run("/slow", cancelled: flag.read)["error"] as? String == "cancelled")
    precondition(ProcessInfo.processInfo.systemUptime - started < 3)
    let deadlineStart = ProcessInfo.processInfo.systemUptime
    precondition(run("/slow")["error"] as? String == "timeout")
    precondition(ProcessInfo.processInfo.systemUptime - deadlineStart < 3)
    let pool = URLSession(configuration: configuration(), delegate: nil, delegateQueue: .main)
    let pooledCancellation = CancellationFlag()
    DispatchQueue.global().asyncAfter(deadline: .now()+0.1) { pooledCancellation.cancel() }
    precondition(run("/slow", sharedSession: pool, cancelled: pooledCancellation.read)["error"] as? String == "cancelled")
    precondition(run("/bytes", sharedSession: pool)["status"] as? Int == 200)
    precondition(run("/bytes", sharedSession: pool)["status"] as? Int == 200)
    pool.finishTasksAndInvalidate()
    let capabilities = "/api/internal/dream/v1/capabilities"
    let resolve = "/api/internal/dream/v1/browser-sessions/resolve"
    let profile = "/api/internal/dream/v1/operations/user-profile.current"
    precondition(run(capabilities, headers: ["X-Fixture-Case":"capabilities-lost-once"])["status"] as? Int == 200)
    precondition(FixtureProtocol.cases["capabilities-lost-once"] == 2, "fixture cases: \(FixtureProtocol.cases)")
    precondition(run(resolve, headers: ["X-Fixture-Case":"resolve-lost-once"], method:"POST")["status"] as? Int == 200)
    precondition(FixtureProtocol.cases["resolve-lost-once"] == 2, "fixture cases: \(FixtureProtocol.cases)")
    precondition(run(profile, headers: ["X-Fixture-Case":"profile-always-lost"], method:"POST")["error"] as? String == "transport")
    precondition(FixtureProtocol.cases["profile-always-lost"] == 2, "fixture cases: \(FixtureProtocol.cases)")
    for (label,path) in [("token-always-lost","/api/auth/oauth2/token"),("exchange-always-lost","/api/internal/dream/v1/browser-sessions/exchange"),("write-always-lost","/api/internal/dream/v1/operations/user-system-config.patch")] {
        precondition(run(path, headers:["X-Fixture-Case":label], method:"POST")["error"] as? String == "transport")
        precondition(FixtureProtocol.cases[label] == 1, "fixture cases: \(FixtureProtocol.cases)")
    }
    precondition(run(capabilities,headers:["X-Fixture-Case":"headers-lost"])["error"] as? String == "transport")
    precondition(FixtureProtocol.cases["headers-lost"] == 1, "fixture cases: \(FixtureProtocol.cases)")
    let recoveryStart = ProcessInfo.processInfo.systemUptime
    precondition(run(capabilities,headers:["X-Fixture-Case":"deadline-recovery"])["error"] as? String == "timeout")
    precondition(FixtureProtocol.cases["deadline-recovery"] == 2, "fixture cases: \(FixtureProtocol.cases)")
    precondition(ProcessInfo.processInfo.systemUptime-recoveryStart < 2.8)
    let managedPool = NativeAdminConnectionPool(configuration: configuration())
    var acquired: [ObjectIdentifier] = []
    // Retain test sessions so ObjectIdentifier cannot be reused by allocation.
    var retained: [URLSession] = []
    let acquire = { () -> URLSession in
        let value = managedPool.acquire(); retained.append(value); acquired.append(ObjectIdentifier(value)); return value
    }
    let retire = { (value: URLSession) in managedPool.retire(value) }
    precondition(run("/bytes", sessionProvider: acquire, sessionFailed: retire)["status"] as? Int == 200)
    let normal = acquired.last!
    precondition(run("/slow", sessionProvider: acquire, sessionFailed: retire)["error"] as? String == "timeout")
    precondition(acquired.last! == normal)
    precondition(run("/bytes", sessionProvider: acquire, sessionFailed: retire)["status"] as? Int == 200)
    let afterTimeout = acquired.last!; precondition(afterTimeout != normal)
    let hint = CancellationFlag()
    DispatchQueue.global().asyncAfter(deadline: .now()+0.1) { hint.cancel() }
    precondition(run("/slow", sessionProvider: acquire, sessionFailed: retire, cancelled: hint.read, timedOut: hint.read)["error"] as? String == "timeout")
    precondition(run("/bytes", sessionProvider: acquire, sessionFailed: retire)["status"] as? Int == 200)
    let afterHint = acquired.last!; precondition(afterHint != afterTimeout)
    let ordinary = CancellationFlag()
    DispatchQueue.global().asyncAfter(deadline: .now()+0.1) { ordinary.cancel() }
    precondition(run("/slow", sessionProvider: acquire, sessionFailed: retire, cancelled: ordinary.read)["error"] as? String == "cancelled")
    precondition(run("/bytes", sessionProvider: acquire, sessionFailed: retire)["status"] as? Int == 200)
    precondition(acquired.last! == afterHint)
    let beforeRecovery = acquired.count
    precondition(run(capabilities, headers: ["X-Fixture-Case":"managed-lost-once"], sessionProvider: acquire, sessionFailed: retire)["status"] as? Int == 200)
    precondition(acquired.count == beforeRecovery + 2 && acquired[beforeRecovery] != acquired[beforeRecovery+1])
    let drainFinished = DispatchSemaphore(value: 0)
    DispatchQueue.main.async {
        let old = managedPool.acquire()
        var transfer: NativeHTTPResponse?
        func receive() {
            transfer?.readBytes(resolve: { _, done in
                if done { transfer = nil; drainFinished.signal() }
                else { DispatchQueue.main.async { receive() } }
            }, reject: { _, _, _ in fatalError("retirement cancelled another transfer") })
        }
        transfer = NativeHTTPResponse(request: URLRequest(url: URL(string: "https://native-admin.invalid/drain")!), cookies: false, sharedSession: old,
            resolve: { _ in DispatchQueue.main.async { receive() } }, reject: { _, _, _ in fatalError("retirement cancelled another transfer head") })
        transfer?.start()
        managedPool.retire(old)
        let fresh = managedPool.acquire(); precondition(fresh !== old)
        managedPool.retire(old); precondition(managedPool.acquire() === fresh)
        managedPool.retire(fresh)
    }
    precondition(drainFinished.wait(timeout: .now()+3) == .success)
    let drained = DispatchSemaphore(value: 0)
    DispatchQueue.main.async {
        var held: NativeHTTPResponse?
        held = NativeHTTPResponse(request: URLRequest(url: URL(string: "https://native-admin.invalid/held")!), cookies: false, configuration: configuration(), resolve: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now()+0.15) {
                let optionalTask = Mirror(reflecting: held!).children.first(where: { $0.label == "task" })!.value
                let task = Mirror(reflecting: optionalTask).children.first!.value as! URLSessionTask
                precondition(task.state == .suspended)
                held?.readBytes(resolve: { bytes, done in precondition(bytes == Data([255, 0, 195, 40, 65]) && !done) }, reject: { _, _, _ in fatalError("drain failed") })
                precondition(task.state == .running)
                held?.cancel(); held = nil; drained.signal()
            }
        }, reject: { _, _, _ in fatalError("held head failed") })
        held?.start()
    }
    precondition(drained.wait(timeout: .now()+3) == .success)
    DispatchQueue.main.async {
        var response: NativeHTTPResponse?
        var text = ""
        func pull() {
            response?.read(resolve: { value in
                let chunk = value as! [String: Any]; text += chunk["text"] as! String
                if chunk["done"] as! Bool {
                    precondition(text == "中🙂")
                    DispatchQueue.main.async {
                        response?.cancel(); print("native_source_checks=24 network_calls=0 model_calls=0 target=macOS_Foundation_source_contract")
                        exit(0)
                    }
                } else { DispatchQueue.main.async { pull() } }
            }, reject: { _, _, _ in fatalError("UTF8 read regression") })
        }
        response = NativeHTTPResponse(request: URLRequest(url: URL(string: "https://native-admin.invalid/text")!), cookies: false, configuration: configuration(), resolve: { _ in DispatchQueue.main.async { pull() } }, reject: { _, _, _ in fatalError("UTF8 head regression") })
        response?.start()
    }
}
dispatchMain()
'''
file=stage/'native-admin-http-main.swift';file.write_text(prelude+actual+fixture)
binary=stage/'native-admin-http-check'
facts={'source':'frontend/ios/InkMemory/InkReactNative.swift','sourceSliceSha256':hashlib.sha256(actual.encode()).hexdigest(),'fixtureNetworkCalls':0,'modelCalls':0,'target':'macOS Foundation source contract; iOS device qualification separate'}
with (stage/'native-admin-http-compile.log').open('w') as out:
 r=subprocess.run(['xcrun','swiftc','-swift-version','5',str(file),'-o',str(binary)],stdout=out,stderr=subprocess.STDOUT)
facts['compileExit']=r.returncode
if r.returncode==0:
 with (stage/'native-admin-http-run.log').open('w') as out:
  r=subprocess.run([str(binary)],stdout=out,stderr=subprocess.STDOUT,timeout=30)
 facts['runExit']=r.returncode
(stage/'native-admin-http-receipt.json').write_text(json.dumps(facts,indent=2));print(json.dumps(facts))
raise SystemExit(r.returncode)
