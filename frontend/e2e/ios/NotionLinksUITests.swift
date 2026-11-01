// [Input] Explicit simulator fixture bundle and the original React Native link controls.
// [Output] Before/after crash evidence, default Safari handoff and in-App failure recovery.
// [Pos] Provider-free native UI test; the fixture contains no real account or authorization session.
import XCTest

@MainActor
final class NotionLinksUITests: XCTestCase {
    func testNotionAuthorizationDefaultBrowserAndRecovery() throws {
        continueAfterFailure = false
        let target = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_NOTION_LINK_TARGET"])
        let expectCrash = ProcessInfo.processInfo.environment["INK_NOTION_LINK_EXPECT_CRASH"] == "1"
        let app = XCUIApplication(bundleIdentifier: target)
        app.launch()
        let open = app.buttons["打开验证页"]
        XCTAssertTrue(open.waitForExistence(timeout: 20))
        open.tap()
        if expectCrash {
            XCTAssertTrue(app.wait(for: .notRunning, timeout: 15), "The original default callback must reproduce the reported fatal error")
            return
        }
        let browser = XCUIApplication(bundleIdentifier: "com.apple.mobilesafari")
        XCTAssertTrue(browser.wait(for: .runningForeground, timeout: 20), "The simulator default browser must receive the authorization link")
        app.activate()
        XCTAssertTrue(open.waitForExistence(timeout: 10))
        app.buttons["Test failure"].tap()
        app.buttons["打开验证页"].tap()
        XCTAssertTrue(app.staticTexts["链接暂时无法打开，请重试。"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.state, .runningForeground)
        app.buttons["Test about"].tap()
        let repository = app.links["GitHub Repository"]
        for _ in 0..<10 {
            if repository.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(repository.isHittable)
        repository.tap()
        XCTAssertTrue(browser.wait(for: .runningForeground, timeout: 15))
        app.activate()
        XCTAssertEqual(app.state, .runningForeground)
    }
}
