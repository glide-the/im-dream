// [Input] ActivityKit binary content and the existing StartupArtwork asset.
// [Output] Lock Screen and Dynamic Island presence with the system's default App opening.
// [Pos] SwiftUI widget extension; the application owns observation and task execution.
import ActivityKit
import SwiftUI
import WidgetKit

@main
struct ThreadActivityBundle: WidgetBundle {
    var body: some Widget { ThreadActivityWidget() }
}

struct ThreadActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: ThreadActivityAttributes.self) { context in
            HStack(spacing: 16) {
                Image("StartupArtwork").resizable().scaledToFit().frame(width: 56, height: 56)
                VStack(alignment: .leading, spacing: 5) {
                    Text("Kastention").font(.headline)
                    Text("最近确认 · 活跃 Thread").font(.caption)
                }
                Spacer()
                Text(context.state.hasActiveThread ? "有" : "无").font(.title2.bold())
            }
            .padding(16)
            .activityBackgroundTint(Color(uiColor: .secondarySystemBackground))
            .accessibilityElement(children: .combine)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Image("StartupArtwork").resizable().scaledToFit().frame(width: 40, height: 40)
                }
                DynamicIslandExpandedRegion(.center) {
                    Text("活跃 Thread：" + (context.state.hasActiveThread ? "有" : "无"))
                }
                DynamicIslandExpandedRegion(.bottom) { Text("最近确认 · Kastention").font(.caption) }
            } compactLeading: {
                Image("StartupArtwork").resizable().scaledToFit()
            } compactTrailing: {
                Text(context.state.hasActiveThread ? "有" : "无")
            } minimal: {
                Text(context.state.hasActiveThread ? "有" : "无")
            }
        }
    }
}
