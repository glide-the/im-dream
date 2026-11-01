// [Input] Private Admin HTTP request JSON and caller-owned cancellation.
// [Output] Bounded response bytes or a closed transport error; caller frees the returned string.
// [Pos] Shared iOS URLSession boundary for embedded Node and CPython.
// [Sync] 2026-11-01: cancellation callback returns 0 for active, 1 for cancellation and 2 for caller timeout.
#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef int32_t (*IMDreamHTTPCancelled)(void *context);
char *IMDreamHTTPPerform(const char *payload, IMDreamHTTPCancelled cancelled, void *context);
#ifdef __cplusplus
}
#endif
