/* [Input] Fixed test-only ntn argv; no credential, content or remote I/O.
 * [Output] Constant fake tool result for production Runner/Runtime sandbox tests.
 * [Pos] Native fixture only, compiled in a test-owned directory outside workspace.
 * [Sync] 2026-09-13: preserve native executable policy rather than admit script shadows.
 */
#include <stdio.h>

int main(void) {
    puts("{\"fake_ntn\":\"ok\"}");
    return 0;
}
