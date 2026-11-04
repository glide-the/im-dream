// [Input] Public Darwin own-process/thread CPU counters and original request/command activity projections.
// [Output] A single bounded iOS CPU/thermal sample with collection cost; no timers, business calls or temperature inference.
// [Pos] Called on the existing InkRuntime's utility queue while a diagnostics view requests samples.
import Foundation
import Darwin

enum NativeRuntimePerformance {
    static let threadLimit = 256
    static let commandLimit = 64
    static let requestLimit = 32

    private static func cpu(_ port: thread_t) -> Double? {
        var info = thread_basic_info()
        var count = mach_msg_type_number_t(MemoryLayout<thread_basic_info>.size / MemoryLayout<integer_t>.size)
        let result = withUnsafeMutablePointer(to: &info) { pointer in
            pointer.withMemoryRebound(to: integer_t.self, capacity: Int(count)) { thread_info(port, thread_flavor_t(THREAD_BASIC_INFO), $0, &count) }
        }
        guard result == KERN_SUCCESS else { return nil }
        return Double(info.user_time.seconds + info.system_time.seconds) * 1000 + Double(info.user_time.microseconds + info.system_time.microseconds) / 1000
    }

    private static func identifier(_ port: thread_t) -> UInt64? {
        var info = thread_identifier_info()
        var count = mach_msg_type_number_t(MemoryLayout<thread_identifier_info>.size / MemoryLayout<integer_t>.size)
        let result = withUnsafeMutablePointer(to: &info) { pointer in
            pointer.withMemoryRebound(to: integer_t.self, capacity: Int(count)) { thread_info(port, thread_flavor_t(THREAD_IDENTIFIER_INFO), $0, &count) }
        }
        return result == KERN_SUCCESS ? info.thread_id : nil
    }

    private static func label(_ port: thread_t, id: UInt64, main: UInt64, sampler: UInt64) -> String {
        if id == main { return "主线程（共享）" }
        if id == sampler { return "本次采样线程" }
        if let thread = pthread_from_mach_thread_np(port) {
            var name = [CChar](repeating: 0, count: 64)
            let capacity = name.count
            if pthread_getname_np(thread, &name, capacity) == 0 {
                switch String(cString: name) {
                case "DreamNode": return "Node主循环（共享）"
                case "com.facebook.react.runtime.JavaScript", "com.facebook.react.JavaScript": return "React Native JS（共享）"
                default: break
                }
            }
        }
        return "其他App线程"
    }

    static func collect(mainThreadID: UInt64, requests: [[String: Any]], requestsTruncated: Bool) throws -> [String: Any] {
        let started = ProcessInfo.processInfo.systemUptime
        let ownPort = pthread_mach_thread_np(pthread_self())
        let ownBefore = cpu(ownPort)
        var usage = rusage()
        guard getrusage(RUSAGE_SELF, &usage) == 0 else { throw NSError(domain: "InkMemory.CPU", code: Int(errno)) }
        let tick = ProcessInfo.processInfo.systemUptime * 1000
        let at = Date().timeIntervalSince1970 * 1000
        let processCPU = Double(usage.ru_utime.tv_sec + usage.ru_stime.tv_sec) * 1000 + Double(usage.ru_utime.tv_usec + usage.ru_stime.tv_usec) / 1000
        var ownID: UInt64 = 0
        pthread_threadid_np(nil, &ownID)
        var ports: thread_act_array_t?
        var count: mach_msg_type_number_t = 0
        var threads: [[String: Any]] = []
        let result = task_threads(mach_task_self_, &ports, &count)
        if result == KERN_SUCCESS, let ports {
            defer {
                for index in 0..<Int(count) { mach_port_deallocate(mach_task_self_, ports[index]) }
                vm_deallocate(mach_task_self_, vm_address_t(UInt(bitPattern: ports)), vm_size_t(Int(count) * MemoryLayout<thread_t>.stride))
            }
            for index in 0..<min(Int(count), threadLimit) {
                let port = ports[index]
                if let id = identifier(port), let value = cpu(port) {
                    threads.append(["id": String(id), "label": label(port, id: id, main: mainThreadID, sampler: ownID), "cpuMs": value])
                }
            }
        }
        var commands = [IMDreamGuestActivity](repeating: IMDreamGuestActivity(), count: commandLimit)
        let commandCapacity = commands.count
        var commandCount = 0
        let commandResult = IMDreamGuestCopyActivity(&commands, commandCapacity, &commandCount)
        var activities = requests
        if commandResult == 0 {
            for command in commands.prefix(min(commandCount, commandLimit)) {
                var entry: [String: Any] = ["id": "guest:\(command.pid):\(command.generation)", "kind": "command", "label": "命令实例 \(command.pid) / \(command.generation)", "phase": command.started != 0 ? "executing" : "starting"]
                if command.thread_id != 0 { entry["threadId"] = String(command.thread_id) }
                activities.append(entry)
            }
        }
        let thermal: String
        switch ProcessInfo.processInfo.thermalState {
        case .nominal: thermal = "nominal"
        case .fair: thermal = "fair"
        case .serious: thermal = "serious"
        case .critical: thermal = "critical"
        @unknown default: thermal = "unknown"
        }
        #if targetEnvironment(simulator)
        let simulator = true
        #else
        let simulator = false
        #endif
        let ownAfter = cpu(ownPort)
        let collectionCPU: Any
        if let before = ownBefore, let after = ownAfter, after >= before { collectionCPU = after - before }
        else { collectionCPU = NSNull() }
        return ["pid": ProcessInfo.processInfo.processIdentifier, "monotonicMs": tick, "timestampMs": at, "cpuMs": processCPU, "cores": ProcessInfo.processInfo.processorCount, "thermal": thermal, "simulator": simulator,
                "collectionWallMs": max(0, (ProcessInfo.processInfo.systemUptime - started) * 1000), "collectionCpuMs": collectionCPU,
                "threads": threads, "threadsState": result == KERN_SUCCESS ? "available" : "unavailable", "threadsTotal": Int(count), "threadsTruncated": Int(count) > threadLimit || threads.count < Int(count),
                "activities": activities, "commandsState": commandResult == 0 ? "available" : "busy", "activitiesTruncated": requestsTruncated || commandCount > commandLimit]
    }
}
