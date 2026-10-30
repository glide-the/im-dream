// [Input] Literal normalized paths from the original sandbox filesystem projection.
// [Output] Per-invocation filesystem checks through the existing realfs operations.
// [Pos] Native qualification adapter, including the proc path gate; no production entry.
#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct InkGuestPaths { const char *const *items; size_t count; };
struct InkGuestFilesystemRules {
    struct InkGuestPaths denyRead, allowRead, allowWrite, denyWrite;
};
struct fs_ops;
const struct fs_ops *InkNodeGuestFilesystem(void);
const struct InkGuestFilesystemRules *InkNodeGuestFilesystemRulesForScope(uint32_t scope);
int InkNodeGuestCopyFilesystemRules(struct InkGuestFilesystemRules *target,
    const struct InkGuestFilesystemRules *source);
void InkNodeGuestFreeFilesystemRules(struct InkGuestFilesystemRules *rules);
int InkNodeGuestInheritedFileAllowed(const char *root, uint32_t scope, int fd, int writing);
int InkNodeGuestFilesystemPathAllowed(uint32_t scope, const char *path, int writing);
#ifdef __cplusplus
}
#endif
