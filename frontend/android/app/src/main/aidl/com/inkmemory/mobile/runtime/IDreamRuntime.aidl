// [Input] Strict bridge request envelopes serialized as JSON.
// [Output] Capability snapshot and fail-closed runtime operation callbacks.
// [Pos] Sole Binder API exposed by the non-exported Android Dream runtime service.
// [Sync] 2026-10-24: define request, pull-read, and cancellation boundaries.

package com.inkmemory.mobile.runtime;

import com.inkmemory.mobile.runtime.IDreamRuntimeCallback;

interface IDreamRuntime {
    String getCapabilities();
    void request(String requestJson, IDreamRuntimeCallback callback);
    void readResponse(String requestJson, IDreamRuntimeCallback callback);
    void cancel(String requestJson, IDreamRuntimeCallback callback);
}

