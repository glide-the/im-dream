// [Input] A build-supplied Mac LAN host and a connection to iPhone loopback port 5173.
// [Output] A byte-transparent TCP relay to the existing Dream Web/BFF service on the Mac.
// [Pos] Development topology adapter; authentication and business behavior remain owned by the Web services.
// [Sync] 2026-10-25: relay only Dream Web/BFF after Admin browser authentication moved to its public HTTPS authority.
// [Sync] 2026-10-25: connect the packaged iOS host to normal localhost Web authentication over the paired LAN.

import Foundation
import Network

struct LocalDevelopmentTopology {
    static let infoKey = "InkDreamDevelopmentHost"
    let upstreamHost: String

    static func from(bundle: Bundle = .main) -> LocalDevelopmentTopology? {
        guard let raw = bundle.object(forInfoDictionaryKey: infoKey) as? String else { return nil }
        let host = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !host.isEmpty, host.count <= 253,
              host.rangeOfCharacter(from: .whitespacesAndNewlines) == nil,
              !host.contains("/"), !host.contains(":"), !host.contains("@"),
              !host.contains("[") && !host.contains("]") else { return nil }
        return LocalDevelopmentTopology(upstreamHost: host)
    }

    static func isLoopbackWebURL(_ url: URL?) -> Bool {
        guard let url, url.scheme == "http", url.user == nil, url.password == nil else { return false }
        return ["localhost", "127.0.0.1", "[::1]"].contains(url.host?.lowercased() ?? "")
    }
}

final class LocalDevelopmentRelay {
    private let queue = DispatchQueue(label: "com.inkmemory.mobile.local-relay")
    private let topology: LocalDevelopmentTopology
    private var tunnels: [LocalPortTunnel] = []
    private var completionDelivered = false

    init(topology: LocalDevelopmentTopology) {
        self.topology = topology
    }

    func start(completion: @escaping (Result<Void, Error>) -> Void) {
        queue.async {
            let ports: [UInt16] = [5173]
            var ready = Set<UInt16>()
            self.tunnels = ports.compactMap { port in
                guard let endpointPort = NWEndpoint.Port(rawValue: port) else { return nil }
                return LocalPortTunnel(localPort: endpointPort, upstreamHost: self.topology.upstreamHost,
                                       upstreamPort: endpointPort, queue: self.queue) { result in
                    guard !self.completionDelivered else { return }
                    switch result {
                    case .success:
                        ready.insert(port)
                        if ready.count == ports.count {
                            self.completionDelivered = true
                            DispatchQueue.main.async { completion(.success(())) }
                        }
                    case .failure(let error):
                        self.completionDelivered = true
                        self.tunnels.forEach { $0.cancel() }
                        DispatchQueue.main.async { completion(.failure(error)) }
                    }
                }
            }
            if self.tunnels.count != ports.count {
                self.completionDelivered = true
                DispatchQueue.main.async { completion(.failure(LocalDevelopmentRelayError.invalidPort)) }
                return
            }
            self.tunnels.forEach { $0.start() }
        }
    }

    func cancel() {
        queue.async {
            self.tunnels.forEach { $0.cancel() }
            self.tunnels.removeAll()
        }
    }
}

private enum LocalDevelopmentRelayError: LocalizedError {
    case invalidPort
    case listener(String)

    var errorDescription: String? {
        switch self {
        case .invalidPort: return "The local Web relay port is invalid."
        case .listener(let message): return "The local Web relay could not start: \(message)"
        }
    }
}

private final class LocalPortTunnel {
    private let localPort: NWEndpoint.Port
    private let upstreamHost: NWEndpoint.Host
    private let upstreamPort: NWEndpoint.Port
    private let queue: DispatchQueue
    private let readiness: (Result<Void, Error>) -> Void
    private var listener: NWListener?
    private var connections: [ObjectIdentifier: RelayConnectionPair] = [:]

    init(localPort: NWEndpoint.Port, upstreamHost: String, upstreamPort: NWEndpoint.Port,
         queue: DispatchQueue, readiness: @escaping (Result<Void, Error>) -> Void) {
        self.localPort = localPort
        self.upstreamHost = NWEndpoint.Host(upstreamHost)
        self.upstreamPort = upstreamPort
        self.queue = queue
        self.readiness = readiness
    }

    func start() {
        do {
            let parameters = NWParameters.tcp
            parameters.requiredLocalEndpoint = .hostPort(host: NWEndpoint.Host("127.0.0.1"), port: localPort)
            let listener = try NWListener(using: parameters)
            self.listener = listener
            listener.stateUpdateHandler = { [weak self] state in
                guard let self else { return }
                switch state {
                case .ready: self.readiness(.success(()))
                case .failed(let error): self.readiness(.failure(LocalDevelopmentRelayError.listener(error.localizedDescription)))
                default: break
                }
            }
            listener.newConnectionHandler = { [weak self] local in self?.accept(local) }
            listener.start(queue: queue)
        } catch {
            readiness(.failure(error))
        }
    }

    func cancel() {
        listener?.cancel()
        listener = nil
        connections.values.forEach { $0.cancel() }
        connections.removeAll()
    }

    private func accept(_ local: NWConnection) {
        let remote = NWConnection(host: upstreamHost, port: upstreamPort, using: .tcp)
        let pair = RelayConnectionPair(local: local, remote: remote, queue: queue) { [weak self] identity in
            self?.connections.removeValue(forKey: identity)
        }
        connections[ObjectIdentifier(pair)] = pair
        pair.start()
    }
}

private final class RelayConnectionPair {
    private let local: NWConnection
    private let remote: NWConnection
    private let queue: DispatchQueue
    private let stopped: (ObjectIdentifier) -> Void
    private var finished = false

    init(local: NWConnection, remote: NWConnection, queue: DispatchQueue,
         stopped: @escaping (ObjectIdentifier) -> Void) {
        self.local = local
        self.remote = remote
        self.queue = queue
        self.stopped = stopped
    }

    func start() {
        local.start(queue: queue)
        remote.start(queue: queue)
        pump(from: local, to: remote)
        pump(from: remote, to: local)
    }

    func cancel() {
        guard !finished else { return }
        finished = true
        local.cancel()
        remote.cancel()
        stopped(ObjectIdentifier(self))
    }

    private func pump(from source: NWConnection, to destination: NWConnection) {
        source.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self] data, _, complete, error in
            guard let self, !self.finished else { return }
            if let error {
                self.cancel()
                _ = error
                return
            }
            if let data, !data.isEmpty {
                destination.send(content: data, completion: .contentProcessed { [weak self] sendError in
                    guard let self else { return }
                    if sendError != nil || complete { self.cancel() }
                    else { self.pump(from: source, to: destination) }
                })
            } else if complete {
                self.cancel()
            } else {
                self.pump(from: source, to: destination)
            }
        }
    }
}
