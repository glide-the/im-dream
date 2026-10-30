// [Input] RN application runtime startup request.
// [Output] Explicit unavailable result until embedded Python/Claude Android qualification completes.
// [Pos] Android native module; no remote execution fallback or simulated business result.
package com.inkmemory.mobile
import com.facebook.react.ReactPackage
import com.facebook.react.bridge.*
import com.facebook.react.uimanager.ViewManager
class InkRuntimePackage : ReactPackage {
    override fun createNativeModules(context: ReactApplicationContext) = listOf(InkRuntime(context))
    override fun createViewManagers(context: ReactApplicationContext): List<ViewManager<*, *>> = emptyList()
}
class InkRuntime(context: ReactApplicationContext) : ReactContextBaseJavaModule(context) {
    override fun getName() = "InkRuntime"
    @ReactMethod fun ensureStarted(promise: Promise) {
        promise.reject("CAPABILITY_UNAVAILABLE", "Android 端侧 Python 和 Claude 运行库等待资格验证。")
    }
}
