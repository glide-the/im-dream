/* [Input] Fixed test-only ntn argv; no credential, content or remote I/O.
 * [Output] Constant fake tool result for production Runner/Runtime sandbox tests.
 * [Pos] Native fixture only, compiled in a test-owned directory outside workspace.
 * [Sync] 2026-09-13: preserve native executable policy rather than admit script shadows.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* [Sync] 2026-09-13: require actual thread config readability and binding;
 * never let a constant output hide missing Notion environment delivery. */

int main(void) {
    const char *home = getenv("NOTION_HOME");
    const char *token = getenv("NOTION_API_TOKEN");
    const char *keyring = getenv("NOTION_KEYRING");
    char path[4096];
    if (!home || !*home || !token || strcmp(token, "fixture-notion-token") ||
        !keyring || strcmp(keyring, "0")) {
        fputs("fixture binding unavailable\n", stderr);
        return 91;
    }
    if (snprintf(path, sizeof(path), "%s/config.json", home) >= (int)sizeof(path)) return 92;
    FILE *config = fopen(path, "r");
    if (!config) { perror("fixture config read"); return 93; }
    int first = fgetc(config);
    fclose(config);
    if (first != '{') return 94;
    puts("{\"fake_ntn\":\"ok\"}");
    return 0;
}
