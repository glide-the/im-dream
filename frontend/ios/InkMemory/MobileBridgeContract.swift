// [Input] v1 bridge request dictionaries and app-owned method/event inventory.
// [Output] Strict generation-aware requests, a document-generation gate, correlated responses, and sequenced events.
// [Pos] iOS source mirror of mobile/shared/bridge/contract.json.
// [Sync] 2026-10-25: remove native authentication operations; retain the existing web login boundary.
// [Sync] 2026-10-24: retain document-generation checks and remove the unused platform result abstraction.
// [Sync] 2026-10-24: add pull-stream, page-generation, and event-sequence fields.

import Foundation

enum MobileBridgeContract {
    static let version = "1.0"
    static let methods: Set<String> = [
        "app.getInfo", "runtime.getCapabilities", "runtime.request", "runtime.response.read", "runtime.cancel",
        "lifecycle.getState",
        "file.pick", "file.save", "share.open", "external.open",
    ]
    static let events: Set<String> = [
        "lifecycle.changed", "network.changed", "runtime.changed",
    ]
    static let requestID = try! NSRegularExpression(pattern: "^[A-Za-z0-9_-]{1,96}$")

    static func parse(_ body: Any) throws -> MobileBridgeRequest {
        guard let object = body as? [String: Any] else {
            throw MobileBridgeFailure(code: "BAD_REQUEST", message: "Bridge request must be an object.")
        }
        guard object["version"] as? String == version else {
            throw MobileBridgeFailure(code: "PROTOCOL_MISMATCH", message: "Bridge protocol version is unsupported.")
        }
        guard let id = object["id"] as? String,
              requestID.firstMatch(in: id, range: NSRange(id.startIndex..., in: id)) != nil else {
            throw MobileBridgeFailure(code: "BAD_REQUEST", message: "Bridge request identifier is invalid.")
        }
        guard let pageGeneration = object["pageGeneration"] as? String,
              requestID.firstMatch(in: pageGeneration, range: NSRange(pageGeneration.startIndex..., in: pageGeneration)) != nil else {
            throw MobileBridgeFailure(code: "BAD_REQUEST", message: "Bridge page generation is invalid.")
        }
        guard let method = object["method"] as? String, methods.contains(method) else {
            throw MobileBridgeFailure(code: "FORBIDDEN", message: "Bridge method is not allowlisted.")
        }
        guard let params = object["params"] as? [String: Any] else {
            throw MobileBridgeFailure(code: "BAD_REQUEST", message: "Bridge params must be an object.")
        }
        return MobileBridgeRequest(id: id, pageGeneration: pageGeneration, method: method, params: params)
    }

    static func success(request: MobileBridgeRequest, result: Any) -> [String: Any] {
        ["version": version, "id": request.id, "pageGeneration": request.pageGeneration, "ok": true, "result": result]
    }

    static func failure(request: MobileBridgeRequest, code: String, message: String) -> [String: Any] {
        failure(id: request.id, pageGeneration: request.pageGeneration, code: code, message: message)
    }

    static func failure(id: String, pageGeneration: String, code: String, message: String) -> [String: Any] {
        ["version": version, "id": id, "pageGeneration": pageGeneration, "ok": false, "error": ["code": code, "message": message]]
    }

    static func event(name: String, payload: Any, pageGeneration: String, sequence: UInt64) -> [String: Any]? {
        guard events.contains(name) else { return nil }
        return ["version": version, "pageGeneration": pageGeneration, "sequence": String(sequence), "event": name, "payload": payload]
    }
}

struct MobileBridgeRequest {
    let id: String
    let pageGeneration: String
    let method: String
    let params: [String: Any]
}

struct MobilePageGenerationGate {
    private(set) var activeGeneration: String?
    private(set) var eventSequence: UInt64 = 0

    mutating func accept(_ generation: String) -> Bool {
        if let activeGeneration { return activeGeneration == generation }
        activeGeneration = generation
        return true
    }

    func isCurrent(_ generation: String) -> Bool {
        activeGeneration == generation
    }

    mutating func nextEvent() -> (generation: String, sequence: UInt64)? {
        guard let activeGeneration else { return nil }
        eventSequence &+= 1
        return (activeGeneration, eventSequence)
    }

    mutating func reset() {
        activeGeneration = nil
        eventSequence = 0
    }
}

struct MobileBridgeFailure: Error {
    let code: String
    let message: String
}
