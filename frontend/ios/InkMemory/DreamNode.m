// [Input] Pinned NodeMobile framework and the bundled original Runtime resources.
// [Output] One application-process Node event loop with private SDK endpoint metadata.
// [Pos] iOS executable host; Mac is excluded from runtime configuration.
// [Sync] 2026-10-25: pass the native App data root for bundled in-process command execution.
#import "DreamNode.h"
#import <NodeMobile/NodeMobile.h>
#include <unistd.h>

NSString *IMDreamNodeStart(NSString *resources, NSError **error) {
    static NSString *endpoint;
    static dispatch_once_t once;
    __block NSError *failure = nil;
    dispatch_once(&once, ^{
        NSFileManager *files = NSFileManager.defaultManager;
        NSURL *support = [files URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
        NSString *root = [[support.path stringByAppendingPathComponent:@"InkMemory"] stringByAppendingPathComponent:@"runtime"];
        if (![files createDirectoryAtPath:root withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:&failure]) return;
        NSString *workspaces = [root stringByAppendingPathComponent:@"workspaces"];
        if (![files createDirectoryAtPath:workspaces withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:&failure]) return;
        endpoint = [root stringByAppendingPathComponent:[NSString stringWithFormat:@"node-%d.json", getpid()]];
        // Files from another application launch cannot select this process's endpoint.
        [files removeItemAtPath:endpoint error:nil];
        NSArray<NSString *> *arguments = @[@"node", @"--jitless", @"--trace-warnings",
          [resources stringByAppendingPathComponent:@"node/host.cjs"], endpoint, workspaces,
          [resources stringByAppendingPathComponent:@"node/core/cli.js"], NSHomeDirectory()];
        [NSThread detachNewThreadWithBlock:^{
            char **argv = calloc(arguments.count + 1, sizeof(char *));
            for (NSUInteger i = 0; i < arguments.count; i++) argv[i] = strdup(arguments[i].UTF8String);
            node_start((int)arguments.count, argv);
            for (NSUInteger i = 0; i < arguments.count; i++) free(argv[i]);
            free(argv);
        }];
    });
    if (failure || !endpoint) {
        if (error) *error = failure ?: [NSError errorWithDomain:@"InkMemory.DreamNode" code:1
            userInfo:@{NSLocalizedDescriptionKey:@"Embedded Node startup failed."}];
        return nil;
    }
    return endpoint;
}
