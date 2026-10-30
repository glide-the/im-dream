// [Sync] 2026-10-29: real URLSession response metadata retains Retry-After/Content-Type and excludes credential headers.
// [Sync] 2026-10-28: image-only export reads preserve PNG bytes and reject released/nonimage handles.
// [Sync] 2026-10-28: directory security scope/copy paths and original multi-file multipart order are validated with owned fixture files.
// [Input] Production picked-file store, multipart writer, request policy and URLSession reader.
// [Output] Isolated file ownership/bytes/auth-header/cancellation evidence using fixture files and URLProtocol.
// [Pos] Native technical tests; no picker automation, real accounts, backend, network provider or models.
import XCTest
import UIKit
@testable import InkMemory

private final class UploadFixtureProtocol: URLProtocol {
    static var hold = false
    static var observed: ((URLRequest) -> Void)?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.observed?(request)
        if Self.hold { return }
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: ["Content-Type": "application/json", "Retry-After": "60", "Set-Cookie": "fixture-cookie=private", "Authorization": "fixture-private"])!, cacheStoragePolicy: .notAllowed)
        let bytes = Array("中".utf8)
        client?.urlProtocol(self, didLoad: Data(bytes.prefix(1)))
        client?.urlProtocol(self, didLoad: Data(bytes.dropFirst()))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
final class NativeFileUploadTests: XCTestCase {
    private var root: URL!
    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent("ink-upload-test-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        UploadFixtureProtocol.hold = false; UploadFixtureProtocol.observed = nil
    }
    override func tearDownWithError() throws { UploadFixtureProtocol.observed = nil; try FileManager.default.removeItem(at: root) }
    private func source(_ bytes: Data = Data("fixture".utf8)) throws -> URL { let url = root.appendingPathComponent("说明.txt"); try bytes.write(to: url); return url }
    func testPickedCopyAndLeaseCleanupPreserveSource() throws {
        let original = try source(), store = try NativePickedFileStore()
        let file = try store.importFile(original, maxBytes: 32)
        XCTAssertNotEqual(file.url, original); XCTAssertEqual(file.name, "说明.txt"); XCTAssertEqual(file.size, 7)
        let permissions = try FileManager.default.attributesOfItem(atPath: file.url.path)[.posixPermissions] as? NSNumber
        XCTAssertEqual(permissions?.intValue, 0o600)
        _ = try store.acquire(file.id); store.release(file.id)
        XCTAssertTrue(FileManager.default.fileExists(atPath: file.url.path)); XCTAssertThrowsError(try store.acquire(file.id))
        store.finish(file.id)
        XCTAssertFalse(FileManager.default.fileExists(atPath: file.url.path)); XCTAssertEqual(try Data(contentsOf: original), Data("fixture".utf8))
    }
    func testDirectoryCopiesPreserveRelativePathsAndReleasePrivateFiles() throws {
        let folder = root.appendingPathComponent("Folder", isDirectory: true), nested = folder.appendingPathComponent("场景", isDirectory: true)
        try FileManager.default.createDirectory(at: nested, withIntermediateDirectories: true)
        try Data("source".utf8).write(to: folder.appendingPathComponent("root.txt"))
        try Data([0, 255, 128]).write(to: nested.appendingPathComponent("二进制.bin"))
        let store = try NativePickedFileStore(), files = try store.importDirectory(folder, maxBytes: 64)
        XCTAssertEqual(Set(files.compactMap { $0["relativePath"] as? String }), Set(["Folder/root.txt", "Folder/场景/二进制.bin"]))
        for metadata in files {
            let id = try XCTUnwrap(metadata["id"] as? String), url = try XCTUnwrap(URL(string: try XCTUnwrap(metadata["uri"] as? String)))
            XCTAssertTrue(FileManager.default.fileExists(atPath: url.path)); store.release(id)
            XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
        }
        XCTAssertEqual(try Data(contentsOf: folder.appendingPathComponent("root.txt")), Data("source".utf8))
    }
    func testDirectoryRejectsSymlinkAndOversizeWithoutFollowingExternalFiles() throws {
        let folder = root.appendingPathComponent("Folder", isDirectory: true)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        let external = try source(Data("external".utf8))
        let link = folder.appendingPathComponent("linked.txt")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: external)
        let store = try NativePickedFileStore()
        XCTAssertThrowsError(try store.importDirectory(folder, maxBytes: 64))
        try FileManager.default.removeItem(at: link)
        try Data("oversize".utf8).write(to: folder.appendingPathComponent("large.txt"))
        XCTAssertThrowsError(try store.importDirectory(folder, maxBytes: 1))
        XCTAssertEqual(try Data(contentsOf: external), Data("external".utf8))
    }
    func testMultipartBatchKeepsFileAndRelativePathOrdering() throws {
        let store = try NativePickedFileStore(), first = try store.importFile(source(Data([0, 255])), maxBytes: 64)
        let secondSource = root.appendingPathComponent("second.txt"); try Data("second".utf8).write(to: secondSource)
        let second = try store.importFile(secondSource, maxBytes: 64)
        defer { store.release(first.id); store.release(second.id) }
        let body = try NativeMultipartFile.make(files: [first, second], relativePaths: ["Folder/a.bin", "Folder/场景/second.txt"], fields: ["sessionId": "fixture-thread", "path": "project"])
        defer { body.remove() }
        let bytes = try Data(contentsOf: body.url)
        XCTAssertNotNil(bytes.range(of: Data([0, 255])))
        let text = String(decoding: bytes, as: UTF8.self)
        XCTAssertEqual(text.components(separatedBy: "name=\"file\"").count - 1, 2)
        XCTAssertEqual(text.components(separatedBy: "name=\"relativePath\"").count - 1, 2)
        let firstRange = try XCTUnwrap(text.range(of: "Folder/a.bin")), secondRange = try XCTUnwrap(text.range(of: "Folder/场景/second.txt"))
        XCTAssertLessThan(firstRange.lowerBound, secondRange.lowerBound)
        XCTAssertThrowsError(try NativeMultipartFile.make(files: [first, second], relativePaths: ["only-one"], fields: [:]))
    }
    func testPickerStoreRejectsOversizeDirectoryAndSymlink() throws {
        let original = try source(), store = try NativePickedFileStore()
        XCTAssertThrowsError(try store.importFile(original, maxBytes: 1))
        XCTAssertThrowsError(try store.importFile(root, maxBytes: 32))
        let link = root.appendingPathComponent("link"); try FileManager.default.createSymbolicLink(at: link, withDestinationURL: original)
        XCTAssertThrowsError(try store.importFile(link, maxBytes: 32))
    }
    private func sketchPNG() throws -> Data {
        let image = UIGraphicsImageRenderer(size: CGSize(width: 2, height: 2)).image { context in
            UIColor.black.setFill(); context.fill(CGRect(x: 0, y: 0, width: 2, height: 2))
        }
        return try XCTUnwrap(image.pngData())
    }
    func testSketchPNGUsesOpaqueFileAndExistingLeaseCleanup() throws {
        let bytes = try sketchPNG(), store = try NativePickedFileStore()
        let file = try store.importSketch(base64: bytes.base64EncodedString(), name: "草图.png", maxBytes: bytes.count)
        XCTAssertEqual(file.name, "草图.png"); XCTAssertEqual(file.type, "image/png"); XCTAssertEqual(file.size, bytes.count)
        XCTAssertEqual(try Data(contentsOf: file.url), bytes)
        XCTAssertEqual((try FileManager.default.attributesOfItem(atPath: file.url.path)[.posixPermissions] as? NSNumber)?.intValue, 0o600)
        _ = try store.acquire(file.id); store.release(file.id)
        XCTAssertTrue(FileManager.default.fileExists(atPath: file.url.path)); XCTAssertThrowsError(try store.acquire(file.id))
        store.finish(file.id); XCTAssertFalse(FileManager.default.fileExists(atPath: file.url.path))
    }
    func testExportImageBytesRequireALiveImageLeaseAndPreserveTheOriginalPNG() throws {
        let bytes = try sketchPNG(), store = try NativePickedFileStore()
        let image = try store.importSketch(base64: bytes.base64EncodedString(), name: "share.png", maxBytes: bytes.count)
        let result = try store.readImageData(image.id)
        XCTAssertEqual(result["type"], "image/png")
        XCTAssertEqual(Data(base64Encoded: try XCTUnwrap(result["base64"])), bytes)
        store.release(image.id)
        XCTAssertThrowsError(try store.readImageData(image.id))
        XCTAssertFalse(FileManager.default.fileExists(atPath: image.url.path))
        let text = root.appendingPathComponent("private.txt")
        try Data("Keep this text out of the image bridge".utf8).write(to: text)
        let file = try store.importFile(text, maxBytes: 1024)
        XCTAssertThrowsError(try store.readImageData(file.id))
        store.release(file.id)
        XCTAssertFalse(FileManager.default.fileExists(atPath: file.url.path))
    }
    func testSketchRejectsMalformedPNGPathsAndOversizeBytes() throws {
        let bytes = try sketchPNG(), store = try NativePickedFileStore()
        for name in ["../draft.png", "folder/draft.png", "folder\\draft.png", "draft\n.png", "draft.txt", ""] {
            XCTAssertThrowsError(try store.importSketch(base64: bytes.base64EncodedString(), name: name, maxBytes: bytes.count))
        }
        for data in ["invalid", Data("fixture".utf8).base64EncodedString(), Data([137, 80, 78, 71, 13, 10, 26, 10]).base64EncodedString()] {
            XCTAssertThrowsError(try store.importSketch(base64: data, name: "draft.png", maxBytes: bytes.count))
        }
        XCTAssertThrowsError(try store.importSketch(base64: bytes.base64EncodedString(), name: "draft.png", maxBytes: bytes.count - 1))
        XCTAssertThrowsError(try store.importSketch(base64: bytes.base64EncodedString(), name: "draft.png", maxBytes: 0))
    }
    func testMultipartRetainsBinaryWorkspaceFieldsAndEscapesFilename() throws {
        let bytes = Data([0, 255, 13, 10, 42]), store = try NativePickedFileStore()
        let file = try store.importFile(try source(bytes), maxBytes: 32)
        let body = try NativeMultipartFile.make(file: file, filename: "说明\"\r\n.txt", fields: ["sessionId": "fixture-session", "path": "files"])
        defer { body.remove(); store.release(file.id) }
        let data = try Data(contentsOf: body.url)
        XCTAssertNotNil(data.range(of: bytes))
        XCTAssertNotNil(data.range(of: Data("name=\"sessionId\"\r\n\r\nfixture-session".utf8)))
        XCTAssertNotNil(data.range(of: Data("filename=\"说明%22%0D%0A.txt\"".utf8)))
        XCTAssertTrue(body.contentType.hasPrefix("multipart/form-data; boundary=InkUpload-"))
    }
    func testLocalRequestsRetainCsrfAndRejectOriginChange() throws {
        let origin = URL(string: "http://localhost:5173")!
        let request = try NativeUploadRequest.local(origin: origin, options: ["path": "/api/storage/upload", "method": "POST", "headers": ["Cookie": "fixture", "Authorization": "fixture", "x-ink-csrf": "fixture-csrf", "Origin": "https://invalid.example"]])
        XCTAssertEqual(request.value(forHTTPHeaderField: "Origin"), origin.absoluteString)
        XCTAssertEqual(request.value(forHTTPHeaderField: "x-ink-csrf"), "fixture-csrf")
        XCTAssertNil(request.value(forHTTPHeaderField: "Cookie")); XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        for path in ["//invalid.example/api/upload", "https://invalid.example/api/upload", "/auth/start"] { XCTAssertThrowsError(try NativeUploadRequest.local(origin: origin, options: ["path": path])) }
    }
    func testDirectRequestDoesNotCarryAmbientCredentials() throws {
        let request = try NativeUploadRequest.direct(options: ["url": "https://storage.example/fixture", "method": "PUT", "headers": ["Cookie": "fixture", "Authorization": "fixture", "Content-Type": "text/plain"]])
        XCTAssertNil(request.value(forHTTPHeaderField: "Cookie")); XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "text/plain")
        for raw in ["http://storage.example/file", "https://user:pass@storage.example/file"] { XCTAssertThrowsError(try NativeUploadRequest.direct(options: ["url": raw, "method": "PUT"])) }
    }
    func testURLSessionUploadRetainsSplitUtf8AndCleansOnce() throws {
        let done = expectation(description: "EOF"), original = try source()
        let configuration = URLSessionConfiguration.ephemeral; configuration.protocolClasses = [UploadFixtureProtocol.self]
        var closed = 0, text = ""
        var response: NativeHTTPResponse!
        func read() { response.read(resolve: { value in
            let value = value as! [String: Any]; text += value["text"] as? String ?? ""
            if value["done"] as? Bool == true { done.fulfill() } else { DispatchQueue.main.async { read() } }
        }, reject: { code, _, _ in XCTFail(code ?? "HTTP_FAILED"); done.fulfill() }) }
        var request = URLRequest(url: URL(string: "https://storage.example/fixture")!); request.httpMethod = "PUT"
        response = NativeHTTPResponse(request: request, uploadFile: original, cookies: false, configuration: configuration, close: { closed += 1 }, resolve: { status in XCTAssertEqual(status, 200); DispatchQueue.main.async { read() } }, reject: { code, _, _ in XCTFail(code ?? "HTTP_FAILED"); done.fulfill() })
        response.start(); XCTAssertNil(configuration.httpCookieStorage); XCTAssertNil(configuration.urlCredentialStorage)
        wait(for: [done], timeout: 10); response.cancel()
        XCTAssertEqual(text, "中"); XCTAssertEqual(closed, 1)
        XCTAssertEqual(response.readableHeaders, ["content-type": "application/json", "retry-after": "60"])
    }
    func testCancellationBeforeHeadersClosesUploadOnce() throws {
        UploadFixtureProtocol.hold = true
        let started = expectation(description: "started"), cancelled = expectation(description: "cancelled")
        UploadFixtureProtocol.observed = { _ in started.fulfill() }
        let configuration = URLSessionConfiguration.ephemeral; configuration.protocolClasses = [UploadFixtureProtocol.self]
        var closed = 0
        let response = NativeHTTPResponse(request: URLRequest(url: URL(string: "https://storage.example/fixture")!), uploadFile: try source(), cookies: false, configuration: configuration, close: { closed += 1 }, resolve: { _ in XCTFail("Unexpected headers") }, reject: { _, _, _ in cancelled.fulfill() })
        response.start(); wait(for: [started], timeout: 10); response.cancel(); response.cancel()
        wait(for: [cancelled], timeout: 10); XCTAssertEqual(closed, 1)
    }
}
