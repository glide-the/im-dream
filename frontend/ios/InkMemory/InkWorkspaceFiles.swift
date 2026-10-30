// [Input] Existing Thread-owned Workspace GET requests, URLSession bytes and the native picked-file lease store.
// [Output] Streamed private binary resources, MIME metadata and temporary export copies without JS byte conversion.
// [Pos] iOS Workspace resource adapter; backend ownership, mode, paths and credentials retain their current owners.
import Foundation

enum NativeWorkspaceFileError: Error { case invalidRequest, invalidText, http(Int) }
enum NativeWorkspaceFileRequest {
    static func make(origin: URL, options: NSDictionary) throws -> URLRequest {
        var request = try NativeUploadRequest.local(origin: origin, options: options)
        guard request.httpMethod == "GET", request.httpBody == nil, let url = request.url,
              ["/api/workspace/files/content", "/api/workspace/files/download"].contains(url.path),
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { throw NativeWorkspaceFileError.invalidRequest }
        let query = components.queryItems ?? []
        guard query.filter({ $0.name == "sessionId" && !($0.value ?? "").isEmpty }).count == 1,
              query.filter({ $0.name == "path" && !($0.value ?? "").isEmpty }).count == 1,
              query.filter({ $0.name == "sessionId" }).count == 1,
              query.filter({ $0.name == "path" }).count == 1 else { throw NativeWorkspaceFileError.invalidRequest }
        request.cachePolicy = .reloadIgnoringLocalCacheData
        return request
    }
    static func filename(_ proposed: String) -> String {
        let name = (proposed as NSString).lastPathComponent
        return name.isEmpty || name == "." || name == ".." || name.contains("\\") || name.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }) ? "download" : name
    }
}

final class NativeWorkspaceFileRead: NSObject, URLSessionDataDelegate {
    private let request: URLRequest
    private let store: NativePickedFileStore
    private let configuration: URLSessionConfiguration
    private let completion: (Result<NativePickedFile, Error>) -> Void
    private let directory: URL
    private let temporaryFile: URL
    private var output: FileHandle?
    private var session: URLSession?
    private var task: URLSessionDataTask?
    private var failure: Error?
    private var response: HTTPURLResponse?
    private var finished = false
    init(request: URLRequest, store: NativePickedFileStore, configuration: URLSessionConfiguration = .default, completion: @escaping (Result<NativePickedFile, Error>) -> Void) throws {
        self.request = request; self.store = store; self.configuration = configuration; self.completion = completion
        directory = FileManager.default.temporaryDirectory.appendingPathComponent("ink-workspace-read-" + UUID().uuidString, isDirectory: true)
        temporaryFile = directory.appendingPathComponent("body")
        super.init()
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
            guard FileManager.default.createFile(atPath: temporaryFile.path, contents: nil, attributes: [.posixPermissions: 0o600]) else { throw NativeFileError.unavailable }
            output = try FileHandle(forWritingTo: temporaryFile)
        } catch { try? FileManager.default.removeItem(at: directory); throw error }
    }
    func start() {
        configuration.httpCookieStorage = .shared; configuration.httpShouldSetCookies = true
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        let queue = OperationQueue(); queue.maxConcurrentOperationCount = 1; queue.qualityOfService = .userInitiated
        session = URLSession(configuration: configuration, delegate: self, delegateQueue: queue)
        task = session?.dataTask(with: request); task?.resume()
    }
    func cancel() { task?.cancel(); session?.invalidateAndCancel() }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse, completionHandler: @escaping (URLSession.ResponseDisposition) -> Void) {
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            failure = NativeWorkspaceFileError.http((response as? HTTPURLResponse)?.statusCode ?? 0); completionHandler(.cancel); return
        }
        self.response = http; completionHandler(.allow)
    }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        guard failure == nil else { return }
        do { try output?.write(contentsOf: data) } catch { failure = error; dataTask.cancel() }
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        guard !finished else { return }; finished = true
        do {
            try output?.close(); output = nil
            if let failure = failure ?? error { throw failure }
            guard let response else { throw NativeWorkspaceFileError.invalidRequest }
            let fallback = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == "path" })?.value ?? "download"
            let proposed = response.value(forHTTPHeaderField: "Content-Disposition") == nil ? fallback : response.suggestedFilename ?? fallback
            let file = try store.importDownloadedFile(temporaryFile, name: NativeWorkspaceFileRequest.filename(proposed), type: response.mimeType?.lowercased() ?? "application/octet-stream")
            completion(.success(file))
        } catch { completion(.failure(error)) }
        try? FileManager.default.removeItem(at: directory)
        session.finishTasksAndInvalidate(); self.session = nil; self.task = nil
    }
    deinit { try? output?.close(); try? FileManager.default.removeItem(at: directory) }
}

struct NativeWorkspaceExportCopy {
    let directory: URL
    let url: URL
    static func make(file: NativePickedFile) throws -> NativeWorkspaceExportCopy {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ink-export-" + UUID().uuidString, isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
            let url = directory.appendingPathComponent(NativeWorkspaceFileRequest.filename(file.name))
            try FileManager.default.copyItem(at: file.url, to: url)
            return NativeWorkspaceExportCopy(directory: directory, url: url)
        } catch { try? FileManager.default.removeItem(at: directory); throw error }
    }
    func remove() { try? FileManager.default.removeItem(at: directory) }
}
