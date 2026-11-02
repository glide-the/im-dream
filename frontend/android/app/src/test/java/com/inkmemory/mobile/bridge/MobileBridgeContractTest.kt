// [Input] Representative bridge JSON for active, stale, and disallowed requests.
// [Output] Regression checks for allowlisting and page-generation correlation.
// [Pos] Local unit tests for the Android bridge contract.
// [Sync] 2026-10-24: add first Android bridge protocol tests.

package com.inkmemory.mobile.bridge

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class MobileBridgeContractTest {
    @Test
    fun parsesAllowlistedRequestForActiveGeneration() {
        val request = MobileBridgeContract.parse(
            JSONObject()
                .put("version", "1.0")
                .put("id", "request_1")
                .put("pageGeneration", "page_1")
                .put("method", "runtime.response.read")
                .put("params", JSONObject().put("streamId", "stream_1"))
                .toString(),
            "page_1",
        )

        assertEquals("runtime.response.read", request.method)
        assertEquals("stream_1", request.params.getString("streamId"))
    }

    @Test
    fun rejectsStaleGeneration() {
        val failure = assertThrows(MobileBridgeContract.ProtocolFailure::class.java) {
            MobileBridgeContract.parse(
                JSONObject()
                    .put("version", "1.0")
                    .put("id", "request_1")
                    .put("pageGeneration", "old_page")
                    .put("method", "app.getInfo")
                    .put("params", JSONObject())
                    .toString(),
                "new_page",
            )
        }

        assertEquals("PROTOCOL_MISMATCH", failure.code)
    }

    @Test
    fun rejectsMethodOutsideSharedInventory() {
        val failure = assertThrows(MobileBridgeContract.ProtocolFailure::class.java) {
            MobileBridgeContract.parse(
                JSONObject()
                    .put("version", "1.0")
                    .put("id", "request_1")
                    .put("pageGeneration", "page_1")
                    .put("method", "shell.execute")
                    .put("params", JSONObject())
                    .toString(),
                "page_1",
            )
        }

        assertEquals("FORBIDDEN", failure.code)
    }

    @Test
    fun capabilitySnapshotKeepsUnqualifiedRuntimeUnavailable() {
        val capabilities = MobileBridgeContract.capabilitySnapshot().getJSONObject("capabilities")

        assertEquals("unavailable", capabilities.getJSONObject("python").getString("state"))
        assertEquals("PYTHON_EMBEDDED_BUILD_UNQUALIFIED", capabilities.getJSONObject("python").getString("reasonCode"))
        assertEquals("unavailable", capabilities.getJSONObject("claudeRuntime").getString("state"))
        assertEquals("CLAUDE_CLI_UNSUPPORTED_ANDROID", capabilities.getJSONObject("claudeRuntime").getString("reasonCode"))
        assertEquals("unavailable", capabilities.getJSONObject("localTransport").getString("state"))
        assertEquals("unavailable", capabilities.getJSONObject("files").getString("state"))
    }

    @Test
    fun eventCarriesDecimalSequenceAndGeneration() {
        val event = MobileBridgeContract.event("network.changed", "page_1", 4, JSONObject().put("reachable", true))!!

        assertEquals("page_1", event.getString("pageGeneration"))
        assertEquals("4", event.getString("sequence"))
        assertTrue(event.getJSONObject("payload").getBoolean("reachable"))
        assertFalse(event.has("id"))
    }
}

