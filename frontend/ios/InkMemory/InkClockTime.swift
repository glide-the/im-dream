// [Input] Device-local dates and the preceding whole-second observation.
// [Output] Discrete hand positions and at most one forward step per time boundary.
// [Pos] Shared clock arithmetic; no timers, animation, tasks or business state.
import Foundation

struct InkClockTime {
    let second: Int
    let minute: Int
    let hour: Int
    let epochSecond: Int
    init(_ date: Date, calendar: Calendar = .current) {
        let parts = calendar.dateComponents([.second, .minute, .hour], from: date)
        second = parts.second ?? 0; minute = parts.minute ?? 0; hour = parts.hour ?? 0
        epochSecond = Int(floor(date.timeIntervalSince1970))
    }
    var angles: [Double] { [Double(hour % 12) * 30, Double(minute) * 6, Double(second) * 6] }
    func steps(after previous: InkClockTime?) -> [Bool]? {
        guard let previous, epochSecond - previous.epochSecond == 1 else { return nil }
        guard second == (previous.second + 1) % 60 else { return nil }
        if minute != previous.minute && (second != 0 || minute != (previous.minute + 1) % 60) { return nil }
        if hour != previous.hour && (second != 0 || minute != 0 || hour != (previous.hour + 1) % 24) { return nil }
        return [hour != previous.hour, minute != previous.minute, true]
    }
}
