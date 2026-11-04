// [Input] Application-owned guest root, argv/env/cwd and private descriptors.
// [Output] Native command lifecycle and generation-bound stop operations.
// [Pos] iOS execution API; no per-command sandbox policy.
// [Sync] 2026-11-03: expose bounded read-only activity from the original invocation list and its actual host thread IDs.
#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef void (*IMDreamGuestExitCallback)(void *,int);
typedef struct { uint64_t thread_id; uint32_t generation; int32_t pid; int32_t started; } IMDreamGuestActivity;
// Returns 0 when copied, EBUSY when the original invocation lock is held.
// total is observed count, capped at capacity+1 to signal an incomplete list.
int IMDreamGuestCopyActivity(IMDreamGuestActivity *items,size_t capacity,size_t *total);
int IMDreamGuestInitialize(const char *root,const char *data,const char *resources);
int IMDreamGuestSpawn(const char *file,int argc,const char *argv,size_t argv_size,
    const char *environment,size_t environment_size,const char *cwd,const int descriptors[3],
    IMDreamGuestExitCallback callback,void *context,int *pid,uint32_t *generation);
int IMDreamGuestKillGroup(int pid,int signal,uint32_t generation);
int IMDreamGuestKillProcess(int pid,int signal,uint32_t generation);
#ifdef __cplusplus
}
#endif
