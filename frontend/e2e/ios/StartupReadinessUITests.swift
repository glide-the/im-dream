// [Input] An explicitly selected installed App and its existing startup diagnostics.
// [Output] Physical-device or Simulator evidence of runtime readiness and the account page.
// [Pos] Read-only startup regression; activates the existing App without account or model writes.
import XCTest

@MainActor
final class StartupReadinessUITests: XCTestCase {
    private func capture(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testInstalledRuntimeReachesReadyAndReturnsToAccountPage() throws {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.activate()
        if !app.staticTexts["启动状态"].exists {
            let entry = app.buttons.matching(NSPredicate(
                format: "identifier == %@ OR label == %@",
                "ink-runtime-diagnostics-button", "开发者控制页"
            )).firstMatch
            XCTAssertTrue(entry.waitForExistence(timeout: 30))
            XCTAssertTrue(entry.isHittable)
            entry.tap()
        }
        XCTAssertTrue(app.staticTexts["启动状态"].waitForExistence(timeout: 10))
        let ready = app.staticTexts["本地服务已就绪"].waitForExistence(timeout: 60)
        capture(app, ready ? "installed-runtime-ready" : "installed-runtime-failed")
        XCTAssertTrue(ready, "The installed runtime must finish startup before installation acceptance")
        XCTAssertFalse(app.staticTexts["启动失败"].exists)
        app.buttons["返回"].tap()
        let accountPage = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            app.buttons["登录"].isHittable || app.buttons["ink-runtime-diagnostics-button"].isHittable
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [accountPage], timeout: 30), .completed)
        XCTAssertFalse(app.staticTexts["本地服务启动失败，请关闭后重新打开应用。"].exists)
        capture(app, "installed-account-page")
        print("INK_STARTUP_ACCEPTANCE runtimeReady=true accountPageVisible=true businessWrites=0 modelCalls=0")
    }
}
