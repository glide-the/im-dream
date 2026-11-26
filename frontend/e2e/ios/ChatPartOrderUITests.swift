// [Input] Explicit isolated Simulator fixture with production message and tool components.
// [Output] Actual native ordering, geometry, cancellation and historical-process assertions.
// [Pos] Provider-free presentation qualification; production accounts and services remain unused.
// [Sync] 2026-11-14: assert source order, fixed text geometry, history disclosure and return to latest content on Simulator.
import XCTest

@MainActor
final class ChatPartOrderUITests: XCTestCase {
    let intro = "我先读取这份文档，再整理相关设计。"
    let middle = "文档已读完，接下来搜索相关记录。"
    let final = "整理完成，已保留原文中的设计依据。"
    func target() throws -> XCUIApplication {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_CHAT_ORDER_UI_TARGET"])
        XCTAssertEqual(bundle, "com.inkmemory.chatorderqualification")
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.launch()
        XCTAssertTrue(app.staticTexts[intro].waitForExistence(timeout: 20))
        return app
    }
    func shot(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    func advance(_ app: XCUIApplication, _ count: Int = 1) {
        for _ in 0..<count { app.buttons["Next part"].tap() }
    }
    func assertBefore(_ first: XCUIElement, _ second: XCUIElement, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertTrue(first.exists, file: file, line: line)
        XCTAssertTrue(second.exists, file: file, line: line)
        XCTAssertLessThanOrEqual(first.frame.maxY, second.frame.minY, "Parts must retain their source order", file: file, line: line)
    }
    func testLiveTextAndToolsKeepSourceOrder() throws {
        let app = try target(), text = app.staticTexts[intro]
        let initialY = text.frame.minY
        advance(app)
        let read = app.otherElements["order-tool-order-read"]
        XCTAssertTrue(read.waitForExistence(timeout: 5))
        shot(app, "live-read-order")
        print("CHAT_ORDER_INITIAL text=\(text.frame) read=\(read.frame)")
        assertBefore(text, read)
        XCTAssertEqual(text.frame.minY, initialY, accuracy: 2)
        advance(app)
        assertBefore(text, read)
        advance(app)
        let nextText = app.staticTexts[middle]
        assertBefore(text, read); assertBefore(read, nextText)
        let middleY = nextText.frame.minY
        advance(app)
        let search = app.otherElements["order-tool-order-search"]
        assertBefore(nextText, search)
        for _ in 0..<3 { app.buttons["Tool update"].tap() }
        assertBefore(text, read); assertBefore(read, nextText); assertBefore(nextText, search)
        XCTAssertEqual(text.frame.minY, initialY, accuracy: 2)
        XCTAssertEqual(nextText.frame.minY, middleY, accuracy: 2)
        var positions: [CGFloat] = []
        for _ in 0..<12 {
            positions.append(nextText.frame.minY)
            RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.1))
        }
        XCTAssertLessThanOrEqual((positions.max() ?? 0) - (positions.min() ?? 0), 2)
        shot(app, "live-interleaved-order")
        advance(app)
        assertBefore(text, read); assertBefore(read, nextText)
        assertBefore(nextText, search); assertBefore(search, app.staticTexts[final])
        app.buttons["Dark"].tap(); shot(app, "completed-live-dark")
        app.buttons["Light"].tap(); shot(app, "completed-live-light")
        print("CHAT_ORDER_LIVE ordered=true introY=\(text.frame.minY) middleY=\(positions) updates=3")
    }
    func testCompletedHistoryKeepsDisclosureAndFinalText() throws {
        let app = try target()
        advance(app, 5)
        app.buttons["History"].tap()
        let disclosure = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", "process")).firstMatch
        XCTAssertTrue(disclosure.waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts[final].isHittable)
        XCTAssertFalse(app.staticTexts[intro].exists)
        XCTAssertFalse(app.otherElements["order-tool-order-read"].exists)
        shot(app, "history-collapsed")
        disclosure.tap()
        assertBefore(app.staticTexts[intro], app.otherElements["order-tool-order-read"])
        assertBefore(app.otherElements["order-tool-order-read"], app.staticTexts[middle])
        assertBefore(app.staticTexts[middle], app.otherElements["order-tool-order-search"])
        assertBefore(app.otherElements["order-tool-order-search"], app.staticTexts[final])
        shot(app, "history-expanded")
        disclosure.tap()
        XCTAssertFalse(app.staticTexts[intro].exists)
        XCTAssertTrue(app.staticTexts[final].isHittable)
    }
    func testCancelledHistoryKeepsInterleavedParts() throws {
        let app = try target()
        advance(app, 4)
        app.buttons["Cancel"].tap()
        assertBefore(app.staticTexts[intro], app.otherElements["order-tool-order-read"])
        assertBefore(app.otherElements["order-tool-order-read"], app.staticTexts[middle])
        assertBefore(app.staticTexts[middle], app.otherElements["order-tool-order-search"])
        XCTAssertTrue(app.staticTexts[middle].isHittable)
        shot(app, "cancelled-history-order")
    }
    func testLongHistoryRetainsReadingPositionDuringUpdates() throws {
        let app = try target()
        app.buttons["Long history"].tap()
        advance(app, 4)
        let list = app.otherElements["native-chat-messages-scroll"].scrollViews.firstMatch
        XCTAssertTrue(list.exists)
        list.swipeDown()
        let earlier = try XCTUnwrap(app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Earlier note ")).allElementsBoundByIndex.first { $0.isHittable })
        let readingY = earlier.frame.minY
        for _ in 0..<3 { app.buttons["Tool update"].tap() }
        XCTAssertEqual(earlier.frame.minY, readingY, accuracy: 2)
        advance(app)
        XCTAssertEqual(earlier.frame.minY, readingY, accuracy: 2)
        let retainedY = earlier.frame.minY
        let jump = app.buttons["Scroll to bottom"]
        XCTAssertTrue(jump.isHittable)
        shot(app, "history-reading-position")
        jump.tap()
        XCTAssertTrue(app.staticTexts[final].isHittable)
        shot(app, "history-return-to-latest")
        print("CHAT_ORDER_READING initialY=\(readingY) retainedY=\(retainedY) jump=true")
    }
}
