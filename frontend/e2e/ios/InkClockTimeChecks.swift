// [Input] Production InkClockTime compiled directly with a controlled date/calendar.
// [Output] Whole-second, minute/hour, midnight, suspended and timezone-correction assertions.
// [Pos] Provider-free graphics arithmetic qualification; no UI, services, model or state injection.
import Foundation
@main
struct InkClockTimeChecks {
    static func main() {
        var calendar = Calendar(identifier:.gregorian); calendar.timeZone = TimeZone(secondsFromGMT:0)!
        let formatter = ISO8601DateFormatter()
        func reading(_ time: String) -> InkClockTime { InkClockTime(formatter.date(from:"2026-11-03T" + time + "Z")!,calendar:calendar) }
        let a=reading("12:58:58"),b=reading("12:58:59"),c=reading("12:59:00"),d=reading("12:59:59"),e=reading("13:00:00")
        precondition(b.steps(after:a) == [false,false,true])
        precondition(b.angles == [0,348,354])
        precondition(c.steps(after:b) == [false,true,true])
        precondition(c.angles == [0,354,0])
        precondition(e.steps(after:d) == [true,true,true])
        precondition(e.angles == [30,0,0])
        let midnight = InkClockTime(formatter.date(from:"2026-11-04T00:00:00Z")!,calendar:calendar)
        precondition(midnight.steps(after:reading("23:59:59")) == [true,true,true])
        precondition(midnight.angles == [0,0,0])
        precondition(a.steps(after:nil) == nil)
        precondition(reading("12:59:04").steps(after:c) == nil)
        precondition(a.steps(after:b) == nil)
        let old=reading("12:58:58")
        calendar.timeZone=TimeZone(secondsFromGMT:3600)!
        precondition(reading("12:58:59").steps(after:old) == nil)
        print("Clock arithmetic: second, minute, hour, midnight, initial, skipped, reverse and timezone cases passed")
    }
}
