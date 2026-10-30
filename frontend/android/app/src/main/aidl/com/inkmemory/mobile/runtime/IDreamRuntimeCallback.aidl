// [Input] One runtime response envelope serialized as JSON.
// [Output] One callback across the private process Binder boundary.
// [Pos] Android runtime-process callback contract.
// [Sync] 2026-10-24: define the first private runtime callback.

package com.inkmemory.mobile.runtime;

oneway interface IDreamRuntimeCallback {
    void onResult(String responseJson);
}

