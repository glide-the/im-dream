// [Input] Bundled shared React Native application.
// [Output] Native application screen; original Kotlin runtime services remain platform-owned.
// [Pos] Android React Native entry.
package com.inkmemory.mobile
import com.facebook.react.ReactActivity
class MainActivity : ReactActivity() {
    override fun getMainComponentName(): String = "InkMemory"
}
