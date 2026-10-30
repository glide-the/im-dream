// [Input] Production binary Workspace reader/request policy, private lease store and export-copy adapter.
// [Output] Binary integrity, MIME/filename, cancellation, status isolation and lease cleanup with synthetic URLProtocol only.
// [Pos] Native technical tests; no real account, backend, credential, model or user files.
import XCTest
@testable import InkMemory

private final class WorkspaceFixtureProtocol: URLProtocol {
    static var bytes = Data([0, 255, 128, 195, 40, 80, 75])
    static var status = 200
    static var mime = "application/zip"
    static var filename: String? = "folder.zip"
    static var hold = false
    static var began: (() -> Void)?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.began?(); if Self.hold { return }
        var headers = ["Content-Type": Self.mime]
        if let filename = Self.filename { headers["Content-Disposition"] = "attachment; filename=\"\(filename)\"" }
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: Self.status, httpVersion: nil, headerFields: headers)!, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Self.bytes.prefix(2)); client?.urlProtocol(self, didLoad: Self.bytes.dropFirst(2))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}
final class NativeWorkspaceFileTests: XCTestCase {
    private let origin = URL(string: "http://localhost:5173")!
    override func setUp() { super.setUp(); WorkspaceFixtureProtocol.status=200; WorkspaceFixtureProtocol.mime="application/zip"; WorkspaceFixtureProtocol.filename="folder.zip"; WorkspaceFixtureProtocol.hold=false; WorkspaceFixtureProtocol.began=nil; WorkspaceFixtureProtocol.bytes=Data([0,255,128,195,40,80,75]) }
    private func request(_ endpoint:String="download",path:String="files/folder") throws -> URLRequest {
        var parts=URLComponents();parts.queryItems=[URLQueryItem(name:"sessionId",value:"fixture-thread"),URLQueryItem(name:"path",value:path)]
        return try NativeWorkspaceFileRequest.make(origin:origin,options:["path":"/api/workspace/files/\(endpoint)?\(parts.percentEncodedQuery!)","method":"GET","headers":["x-ink-csrf":String(repeating:"a",count:43),"Authorization":"Bearer fixture-forbidden","Cookie":"fixture-forbidden"]])
    }
    private func read(_ request:URLRequest,store:NativePickedFileStore,completion:@escaping(Result<NativePickedFile,Error>)->Void) throws -> NativeWorkspaceFileRead {
        let config=URLSessionConfiguration.ephemeral;config.protocolClasses=[WorkspaceFixtureProtocol.self]
        return try NativeWorkspaceFileRead(request:request,store:store,configuration:config,completion:completion)
    }
    func testRequestStaysGetOnlySameOriginAndExcludesClientCredentials() throws {
        let valid=try request();XCTAssertEqual(valid.httpMethod,"GET");XCTAssertNil(valid.httpBody);XCTAssertEqual(valid.value(forHTTPHeaderField:"x-ink-csrf"),String(repeating:"a",count:43));XCTAssertNil(valid.value(forHTTPHeaderField:"Authorization"));XCTAssertNil(valid.value(forHTTPHeaderField:"Cookie"))
        for path in ["https://example.invalid/api/workspace/files/content?sessionId=x&path=files/a", "/api/claude-agent?sessionId=x&path=files/a", "/api/workspace/files/content?sessionId=x&sessionId=y&path=files/a"] { XCTAssertThrowsError(try NativeWorkspaceFileRequest.make(origin:origin,options:["path":path])) }
        XCTAssertThrowsError(try NativeWorkspaceFileRequest.make(origin:origin,options:["path":"/api/workspace/files/content?sessionId=x&path=files/a","method":"POST"]))
    }
    func testBinaryZipBytesNeverRequireUtf8AndFilenameIsPreserved() throws {
        let done=expectation(description:"binary complete"),store=try NativePickedFileStore(),expected=WorkspaceFixtureProtocol.bytes
        var asset:NativePickedFile?
        let operation=try read(request(),store:store){result in do{let file=try result.get();asset=file;XCTAssertEqual(try Data(contentsOf:file.url),expected);XCTAssertEqual(file.name,"folder.zip");XCTAssertEqual(file.type,"application/zip");done.fulfill()}catch{XCTFail("binary read failed");done.fulfill()}}
        operation.start();wait(for:[done],timeout:5);let file=try XCTUnwrap(asset);store.release(file.id);XCTAssertFalse(FileManager.default.fileExists(atPath:file.url.path));withExtendedLifetime(operation){}
    }
    func testUnicodeMarkdownFallbackNameAndTextUseOriginalQueryPath() throws {
        WorkspaceFixtureProtocol.mime="text/markdown";WorkspaceFixtureProtocol.filename=nil;WorkspaceFixtureProtocol.bytes=Data("# 原文\n正文🙂".utf8)
        let done=expectation(description:"text complete"),store=try NativePickedFileStore()
        let operation=try read(request("content",path:"files/中文报告.md"),store:store){result in do{let file=try result.get();XCTAssertEqual(file.name,"中文报告.md");XCTAssertEqual(try store.readText(file.id),"# 原文\n正文🙂");store.release(file.id)}catch{XCTFail("text read failed")};done.fulfill()}
        operation.start();wait(for:[done],timeout:5);withExtendedLifetime(operation){}
    }
    func testHttpFailureDoesNotPublishAFileHandle() throws {
        WorkspaceFixtureProtocol.status=403;let done=expectation(description:"denied"),store=try NativePickedFileStore()
        let operation=try read(request(),store:store){result in if case .failure(NativeWorkspaceFileError.http(let status))=result{XCTAssertEqual(status,403)}else{XCTFail("wrong failure")};done.fulfill()}
        operation.start();wait(for:[done],timeout:5);withExtendedLifetime(operation){}
    }
    func testCancellationTerminatesHeldReadWithoutPublishingBytes() throws {
        WorkspaceFixtureProtocol.hold=true;let began=expectation(description:"started"),done=expectation(description:"cancelled"),store=try NativePickedFileStore();WorkspaceFixtureProtocol.began={began.fulfill()}
        let operation=try read(request(),store:store){result in if case .success = result{XCTFail("cancelled read published a handle")};done.fulfill()}
        operation.start();wait(for:[began],timeout:5);operation.cancel();wait(for:[done],timeout:5);withExtendedLifetime(operation){}
    }
    func testExportCopySurvivesSourceReleaseAndCleansOnlyItsDirectory() throws {
        let root=FileManager.default.temporaryDirectory.appendingPathComponent("ink-workspace-test-"+UUID().uuidString,isDirectory:true);try FileManager.default.createDirectory(at:root,withIntermediateDirectories:false);defer{try? FileManager.default.removeItem(at:root)}
        let source=root.appendingPathComponent("fixture");let bytes=Data([0,255,128,1]);try bytes.write(to:source)
        let store=try NativePickedFileStore(),file=try store.importDownloadedFile(source,name:"导出.zip",type:"application/zip")
        let leased=try store.acquire(file.id),copy=try NativeWorkspaceExportCopy.make(file:leased);store.release(file.id)
        XCTAssertTrue(FileManager.default.fileExists(atPath:file.url.path));XCTAssertEqual(copy.url.lastPathComponent,"导出.zip");XCTAssertEqual(try Data(contentsOf:copy.url),bytes)
        store.finish(file.id);XCTAssertFalse(FileManager.default.fileExists(atPath:file.url.path));XCTAssertEqual(try Data(contentsOf:copy.url),bytes)
        copy.remove();XCTAssertFalse(FileManager.default.fileExists(atPath:copy.directory.path));XCTAssertTrue(FileManager.default.fileExists(atPath:source.path))
    }
    func testIndependentMaterialCopyRetainsBytesAfterOriginalRelease() throws {
        let source=FileManager.default.temporaryDirectory.appendingPathComponent("ink-workspace-test-"+UUID().uuidString);try Data("fixture".utf8).write(to:source);defer{try? FileManager.default.removeItem(at:source)}
        let store=try NativePickedFileStore(),first=try store.importDownloadedFile(source,name:"image.png",type:"image/png"),copy=try store.importDownloadedFile(first.url,name:first.name,type:first.type)
        XCTAssertNotEqual(copy.id,first.id);store.release(first.id);XCTAssertEqual(try Data(contentsOf:copy.url),Data("fixture".utf8));XCTAssertThrowsError(try store.readText(copy.id));store.release(copy.id)
    }
}
