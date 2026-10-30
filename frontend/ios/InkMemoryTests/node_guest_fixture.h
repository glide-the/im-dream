// [Input] Named qualification root, argv/env bytes and private stdio descriptors.
// [Output] Actual guest process startup, exit and group-signal results.
// [Pos] Isolated native compatibility fixture, excluded from production targets.
// [Sync] 2026-10-25: assign invocation generations and validate native PID/group signals against their scope.
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "node_guest_filesystem_fixture.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef void (*InkGuestExitCallback)(void *, int);
int InkNodeGuestInitialize(const char *root);
uint32_t InkNodeGuestExecutionScope(uint16_t http_proxy_port, uint16_t socks_proxy_port,
    const struct InkGuestFilesystemRules *filesystem);
int InkNodeGuestCheckInheritedFD(uint32_t scope, int fd, int writing);
int InkNodeGuestSpawn(const char *file, int argc, const char *argv, size_t argv_size,
    const char *environment, size_t environment_size, const char *cwd,
    const int descriptors[3], uint32_t scope_id,
    InkGuestExitCallback callback, void *context, int *pid, uint32_t *invocation_scope);
int InkNodeGuestKillGroup(int pid, int signal_number, uint32_t scope);
int InkNodeGuestKillProcess(int pid, int signal_number, uint32_t scope);
#ifdef __cplusplus
}
#endif
