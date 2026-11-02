// [Sync] 2026-10-28: expose image-only leased bytes to the original DOM long-image renderer.
// [Sync] 2026-10-28: system directory selection copies scoped regular files with relative paths; the same multipart writer handles original batch uploads.
// [Sync] 2026-10-28: reuse opaque file leases for downloaded Workspace bytes and UTF-8 document reads.
// [Input] User-selected document URLs and the original upload fields.
// [Output] Opaque picked-file handles and streamed multipart bodies with explicit ownership and cleanup.
// [Pos] iOS file-resource adapter; authentication and upload strategy remain in the original BFF/frontend.
// [Sync] 2026-10-28: import the local sketch editor's PNG as an opaque upload handle with the same lease cleanup.
import Foundation
import UIKit
import UniformTypeIdentifiers

enum NativeFileError: Error { case invalidFile, tooLarge, unavailable }
struct NativePickedFile {
    let id: String
    let url: URL
    let name: String
    let type: String
    let size: Int
    var metadata: [String: Any] { ["id": id, "name": name, "type": type, "size": size, "uri": url.absoluteString] }
}
final class NativePickedFileStore {
    private let root: URL
    private let lock = NSLock()
    private var files: [String: NativePickedFile] = [:]
    private var users: [String: Int] = [:]
    private var released = Set<String>()
    init() throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent("ink-picked-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
    }
    func importFile(_ source: URL, maxBytes: Int) throws -> NativePickedFile {
        let scope = source.startAccessingSecurityScopedResource()
        defer { if scope { source.stopAccessingSecurityScopedResource() } }
        let values = try source.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey, .contentTypeKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true, let size = values.fileSize else { throw NativeFileError.invalidFile }
        guard size <= maxBytes else { throw NativeFileError.tooLarge }
        let id = UUID().uuidString
        let destination = root.appendingPathComponent(id)
        do {
            try FileManager.default.copyItem(at: source, to: destination)
            let copied = try destination.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey, .isSymbolicLinkKey])
            guard copied.isRegularFile == true, copied.isSymbolicLink != true else { throw NativeFileError.invalidFile }
            guard let copiedSize = copied.fileSize, copiedSize <= maxBytes else { throw NativeFileError.tooLarge }
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: destination.path)
        }
        catch { try? FileManager.default.removeItem(at: destination); throw error }
        let file = NativePickedFile(id: id, url: destination, name: source.lastPathComponent, type: values.contentType?.preferredMIMEType ?? "application/octet-stream", size: size)
        lock.lock(); files[id] = file; lock.unlock()
        return file
    }
    func importDirectory(_ source: URL, maxBytes: Int) throws -> [[String: Any]] {
        let scope = source.startAccessingSecurityScopedResource()
        defer { if scope { source.stopAccessingSecurityScopedResource() } }
        let values = try source.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        guard values.isDirectory == true, values.isSymbolicLink != true else { throw NativeFileError.invalidFile }
        var coordinationError: NSError?, result: Result<[[String: Any]], Error>?
        NSFileCoordinator().coordinate(readingItemAt: source, options: [], error: &coordinationError) { directory in
            var owned: [NativePickedFile] = []
            do {
                let root = directory.standardizedFileURL
                var enumerationError: Error?
                guard let entries = FileManager.default.enumerator(at: root, includingPropertiesForKeys: [.isRegularFileKey, .isDirectoryKey, .isSymbolicLinkKey], options: [], errorHandler: { _, error in enumerationError = error; return false }) else { throw NativeFileError.unavailable }
                var files: [[String: Any]] = []
                for case let url as URL in entries {
                    let info = try url.resourceValues(forKeys: [.isRegularFileKey, .isDirectoryKey, .isSymbolicLinkKey])
                    guard info.isSymbolicLink != true else { throw NativeFileError.invalidFile }
                    if info.isDirectory == true { continue }
                    guard info.isRegularFile == true, url.standardizedFileURL.path.hasPrefix(root.path + "/") else { throw NativeFileError.invalidFile }
                    let file = try self.importFile(url, maxBytes: maxBytes); owned.append(file)
                    var metadata = file.metadata
                    metadata["relativePath"] = root.lastPathComponent + "/" + String(url.standardizedFileURL.path.dropFirst(root.path.count + 1))
                    files.append(metadata)
                }
                if let enumerationError { throw enumerationError }
                result = .success(files)
            } catch { owned.forEach { self.release($0.id) }; result = .failure(error) }
        }
        if let coordinationError {
            if case .success(let files)? = result { files.compactMap { $0["id"] as? String }.forEach { self.release($0) } }
            throw coordinationError
        }
        guard let result else { throw NativeFileError.unavailable }
        return try result.get()
    }
    func importDownloadedFile(_ source: URL, name: String, type: String) throws -> NativePickedFile {
        let imported = try importFile(source, maxBytes: Int.max)
        let file = NativePickedFile(id: imported.id, url: imported.url, name: NativeWorkspaceFileRequest.filename(name), type: type, size: imported.size)
        lock.lock(); files[file.id] = file; lock.unlock()
        return file
    }
    func readText(_ id: String) throws -> String {
        let file = try acquire(id); defer { finish(id) }
        guard ["text/plain", "text/markdown"].contains(file.type), let text = String(data: try Data(contentsOf: file.url), encoding: .utf8) else { throw NativeWorkspaceFileError.invalidText }
        return text
    }
    func acquire(_ id: String) throws -> NativePickedFile {
        lock.lock(); defer { lock.unlock() }
        guard !released.contains(id), let file = files[id] else { throw NativeFileError.invalidFile }
        users[id, default: 0] += 1
        return file
    }
    func importSketch(base64: String, name: String, maxBytes: Int) throws -> NativePickedFile {
        guard maxBytes > 0, maxBytes <= (Int.max / 4 - 1) * 3,
              base64.utf8.count <= ((maxBytes + 2) / 3) * 4,
              !name.isEmpty, name == (name as NSString).lastPathComponent,
              !name.contains("\\"), !name.contains("\0"), !name.contains("\r"), !name.contains("\n"),
              name.lowercased().hasSuffix(".png"), let data = Data(base64Encoded: base64),
              !data.isEmpty, data.count <= maxBytes,
              data.starts(with: [137, 80, 78, 71, 13, 10, 26, 10]),
              UIImage(data: data) != nil else { throw NativeFileError.invalidFile }
        let id = UUID().uuidString, destination = root.appendingPathComponent(UUID().uuidString)
        do {
            try data.write(to: destination, options: .atomic)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: destination.path)
        } catch { try? FileManager.default.removeItem(at: destination); throw error }
        let file = NativePickedFile(id: id, url: destination, name: name, type: "image/png", size: data.count)
        lock.lock(); files[id] = file; lock.unlock()
        return file
    }
    // Only a leased image can cross the DOM export boundary; callers supply no file path.
    func readImageData(_ id: String) throws -> [String: String] {
        let file = try acquire(id)
        defer { finish(id) }
        guard file.type.hasPrefix("image/") else { throw NativeFileError.invalidFile }
        let data = try Data(contentsOf: file.url, options: .mappedIfSafe)
        guard data.count == file.size else { throw NativeFileError.invalidFile }
        return ["type": file.type, "base64": data.base64EncodedString()]
    }
    func finish(_ id: String) { lock.lock(); defer { lock.unlock() }; users[id] = max(0, (users[id] ?? 0) - 1); purge(id) }
    func release(_ id: String) { lock.lock(); defer { lock.unlock() }; released.insert(id); purge(id) }
    private func purge(_ id: String) {
        guard released.contains(id), users[id, default: 0] == 0 else { return }
        if let file = files.removeValue(forKey: id) { try? FileManager.default.removeItem(at: file.url) }
        users.removeValue(forKey: id); released.remove(id)
    }
    deinit { try? FileManager.default.removeItem(at: root) }
}

final class NativeFilePicker: NSObject, UIDocumentPickerDelegate, UIAdaptivePresentationControllerDelegate {
    private let store: NativePickedFileStore
    private let maxBytes: Int
    private let directory: Bool
    private let completion: (Result<[String: Any], Error>) -> Void
    private var completed = false
    init(store: NativePickedFileStore, maxBytes: Int, directory: Bool = false, completion: @escaping (Result<[String: Any], Error>) -> Void) {
        self.store = store; self.maxBytes = maxBytes; self.directory = directory; self.completion = completion
    }
    func present(from controller: UIViewController) {
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: directory ? [.folder] : [.item], asCopy: !directory)
        picker.allowsMultipleSelection = !directory; picker.delegate = self
        controller.present(picker, animated: true) { picker.presentationController?.delegate = self }
    }
    private func finish(_ result: Result<[String: Any], Error>) {
        guard !completed else {
            if case .success(let selection) = result { (selection["files"] as? [[String: Any]] ?? []).compactMap { $0["id"] as? String }.forEach { store.release($0) } }
            return
        }
        completed = true; completion(result)
    }
    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) { finish(.success(["files": [], "rejected": []])) }
    func presentationControllerDidDismiss(_ presentationController: UIPresentationController) { finish(.success(["files": [], "rejected": []])) }
    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        DispatchQueue.global(qos: .userInitiated).async {
            var files: [[String: Any]] = []
            var rejected: [[String: Any]] = []
            do {
                for url in urls {
                    do {
                        if self.directory { files.append(contentsOf: try self.store.importDirectory(url, maxBytes: self.maxBytes)) }
                        else { files.append(try self.store.importFile(url, maxBytes: self.maxBytes).metadata) }
                    }
                    catch NativeFileError.tooLarge { rejected.append(["name": url.lastPathComponent]) }
                }
                DispatchQueue.main.async { self.finish(.success(["files": files, "rejected": rejected])) }
            } catch {
                files.compactMap { $0["id"] as? String }.forEach { self.store.release($0) }
                DispatchQueue.main.async { self.finish(.failure(error)) }
            }
        }
    }
}

struct NativeMultipartFile {
    let url: URL
    let contentType: String
    func remove() { try? FileManager.default.removeItem(at: url) }
    static func make(file: NativePickedFile, filename: String, fields: [String: String]) throws -> NativeMultipartFile {
        try make(files: [file], filenames: [filename], relativePaths: nil, fields: fields)
    }
    static func make(files: [NativePickedFile], filenames: [String]? = nil, relativePaths: [String]? = nil, fields: [String: String]) throws -> NativeMultipartFile {
        guard !files.isEmpty, filenames == nil || filenames!.count == files.count, relativePaths == nil || relativePaths!.count == files.count else { throw NativeFileError.invalidFile }
        let boundary = "InkUpload-" + UUID().uuidString
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("ink-multipart-" + UUID().uuidString)
        guard FileManager.default.createFile(atPath: url.path, contents: nil, attributes: [.posixPermissions: 0o600]) else { throw NativeFileError.unavailable }
        do {
            let output = try FileHandle(forWritingTo: url); defer { try? output.close() }
            func write(_ text: String) throws { try output.write(contentsOf: Data(text.utf8)) }
            func quote(_ text: String) -> String { text.replacingOccurrences(of: "\r", with: "%0D").replacingOccurrences(of: "\n", with: "%0A").replacingOccurrences(of: "\"", with: "%22") }
            for key in fields.keys.sorted() { try write("--\(boundary)\r\nContent-Disposition: form-data; name=\"\(quote(key))\"\r\n\r\n\(fields[key]!)\r\n") }
            for (index, file) in files.enumerated() {
                if let relativePaths { try write("--\(boundary)\r\nContent-Disposition: form-data; name=\"relativePath\"\r\n\r\n\(relativePaths[index])\r\n") }
                let filename = filenames?[index] ?? file.name
                try write("--\(boundary)\r\nContent-Disposition: form-data; name=\"file\"; filename=\"\(quote(filename))\"\r\nContent-Type: \(file.type.replacingOccurrences(of: "\r", with: "").replacingOccurrences(of: "\n", with: ""))\r\n\r\n")
                let input = try FileHandle(forReadingFrom: file.url); defer { try? input.close() }
                while let bytes = try input.read(upToCount: 64 * 1024), !bytes.isEmpty { try output.write(contentsOf: bytes) }
                try write("\r\n")
            }
            try write("--\(boundary)--\r\n")
            return NativeMultipartFile(url: url, contentType: "multipart/form-data; boundary=\(boundary)")
        } catch { try? FileManager.default.removeItem(at: url); throw error }
    }
}

enum NativeUploadRequest {
    static func local(origin: URL, options: NSDictionary) throws -> URLRequest {
        guard let path = options["path"] as? String,
              path.hasPrefix("/api/") || path == "/auth/session" || path == "/auth/logout",
              let url = URL(string: path, relativeTo: origin)?.absoluteURL,
              url.scheme == origin.scheme, url.host == origin.host, url.port == origin.port else { throw NativeFileError.invalidFile }
        var request = URLRequest(url: url)
        request.httpMethod = options["method"] as? String ?? "GET"
        applyHeaders(options["headers"] as? [String: String] ?? [:], to: &request)
        request.setValue(origin.absoluteString, forHTTPHeaderField: "Origin")
        if let body = options["body"] as? String { request.httpBody = body.data(using: .utf8) }
        return request
    }
    static func direct(options: NSDictionary) throws -> URLRequest {
        guard let raw = options["url"] as? String, let url = URL(string: raw), url.scheme == "https", url.host != nil,
              url.user == nil, url.password == nil, let method = options["method"] as? String, ["PUT", "POST"].contains(method) else { throw NativeFileError.invalidFile }
        var request = URLRequest(url: url); request.httpMethod = method
        applyHeaders(options["headers"] as? [String: String] ?? [:], to: &request)
        return request
    }
    private static func applyHeaders(_ headers: [String: String], to request: inout URLRequest) {
        for (key, value) in headers where !["cookie", "authorization", "host", "origin", "service-authorization", "x-service-authorization", "content-length"].contains(key.lowercased()) { request.setValue(value, forHTTPHeaderField: key) }
    }
}
