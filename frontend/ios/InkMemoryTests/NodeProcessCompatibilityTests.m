// [Input] Existing Dream app host with explicit native qualification Worker.
// [Output] App/Node/native process receipts without business requests from the fixture.
// [Pos] App-hosted process compatibility qualification; original product behavior retained.
// [Sync] 2026-10-25: qualify distinct invocation identity, signals/proc and existing filesystem/network behavior.
#import <XCTest/XCTest.h>
#import <Foundation/Foundation.h>
#include <unistd.h>
#include <sys/stat.h>
@interface NodeProcessCompatibilityTests : XCTestCase
@end
@implementation NodeProcessCompatibilityTests
- (void)testOriginalNodeChildProcessInsideApplication {
    NSFileManager *files = NSFileManager.defaultManager;
    struct stat originalDescriptors[3];
    for (int i=0; i<3; i++) XCTAssertEqual(fstat(i, &originalDescriptors[i]), 0);
    NSURL *support = [files URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL *runtime = [[support URLByAppendingPathComponent:@"InkMemory"] URLByAppendingPathComponent:@"runtime"];
    NSURL *input = [runtime URLByAppendingPathComponent:[NSString stringWithFormat:@"node-process-input-%d.json", getpid()]];
    NSURL *result = [runtime URLByAppendingPathComponent:[NSString stringWithFormat:@"node-process-result-%d.json", getpid()]];
    [files createDirectoryAtURL:runtime withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:nil];
    NSBundle *bundle = [NSBundle bundleForClass:self.class];
    NSURL *root = [[NSURL fileURLWithPath:NSTemporaryDirectory() isDirectory:YES]
        URLByAppendingPathComponent:[@"ink-node-process-fixture-" stringByAppendingString:NSUUID.UUID.UUIDString] isDirectory:YES];
    XCTAssertTrue([root.path hasPrefix:[NSHomeDirectory() stringByAppendingString:@"/"]]);
    NSError *copyError = nil;
    XCTAssertTrue([files copyItemAtURL:[bundle.bundleURL URLByAppendingPathComponent:@"rootfs"] toURL:root error:&copyError], @"%@", copyError);
    if (copyError) return;
    NSArray *modes = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfURL:[bundle.bundleURL URLByAppendingPathComponent:@"guest-modes.json"]] options:0 error:nil];
    for (NSDictionary *entry in modes) {
        NSString *relative = entry[@"path"];
        XCTAssertFalse([relative hasPrefix:@"/"]);
        XCTAssertFalse([relative.pathComponents containsObject:@".."]);
        XCTAssertLessThanOrEqual([entry[@"mode"] unsignedIntegerValue], 0777UL);
        XCTAssertTrue([files setAttributes:@{NSFilePosixPermissions:entry[@"mode"]} ofItemAtPath:[root.path stringByAppendingPathComponent:relative] error:nil]);
    }
    NSArray *links = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfURL:[bundle.bundleURL URLByAppendingPathComponent:@"guest-symlinks.json"]] options:0 error:nil];
    for (NSDictionary *entry in links) {
        NSString *relative = entry[@"path"];
        XCTAssertFalse([relative hasPrefix:@"/"]);
        XCTAssertFalse([relative.pathComponents containsObject:@".."]);
        XCTAssertTrue([files createSymbolicLinkAtPath:[root.path stringByAppendingPathComponent:relative] withDestinationPath:entry[@"target"] error:nil]);
    }
    NSData *configuration = [NSJSONSerialization dataWithJSONObject:@{@"root":root.path} options:0 error:nil];
    XCTAssertTrue([configuration writeToURL:input atomically:YES]);
    NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:60];
    while (![files fileExistsAtPath:result.path] && deadline.timeIntervalSinceNow > 0)
        [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.02]];
    NSData *data = [NSData dataWithContentsOfURL:result];
    XCTAssertNotNil(data);
    if (!data) return;
    NSDictionary *receipt = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
    NSLog(@"IOS_NODE_PROCESS_FIXTURE %@", receipt);
    if (![receipt[@"ok"] boolValue]) {XCTFail(@"Qualification failed: %@", receipt); return;}
    XCTAssertEqualObjects(receipt[@"bindingVersion"], @6);
    XCTAssertEqualObjects(receipt[@"nativePID"], @(getpid()));
    XCTAssertEqualObjects(receipt[@"nodePID"], @(getpid()));
    XCTAssertEqualObjects(receipt[@"platform"], @"ios");
    XCTAssertGreaterThan([receipt[@"builtinBytes"] unsignedIntegerValue], 10000UL);
    XCTAssertEqualObjects(receipt[@"originalChildProcess"], @YES);
    XCTAssertEqualObjects(receipt[@"bashExit"], @7);
    XCTAssertEqualObjects(receipt[@"missingCode"], @"ENOENT");
    XCTAssertEqualObjects(receipt[@"concurrent"], @2);
    XCTAssertEqualObjects(receipt[@"cancelSignal"], @"SIGTERM");
    XCTAssertEqualObjects(receipt[@"singleSignal"], @"SIGTERM");
    XCTAssertEqualObjects(receipt[@"syncExit"], @7);
    XCTAssertEqualObjects(receipt[@"syncDuplexBytes"], @262144);
    XCTAssertEqualObjects(receipt[@"syncPipeError"], @"EPIPE");
    XCTAssertEqualObjects(receipt[@"syncPrimaryError"], @"ETIMEDOUT");
    XCTAssertEqualObjects(receipt[@"syncTimeout"], @"ETIMEDOUT");
    XCTAssertEqualObjects(receipt[@"syncOverflow"], @"ENOBUFS");
    XCTAssertEqualObjects(receipt[@"syncCombinedOverflow"], @"ENOBUFS");
    XCTAssertEqualObjects(receipt[@"syncWhich"], @YES);
    XCTAssertEqualObjects(receipt[@"syncPath"], @YES);
    XCTAssertEqualObjects(receipt[@"syncErrors"], @YES);
    XCTAssertEqualObjects(receipt[@"syncInheritedFD"], @YES);
    XCTAssertEqualObjects(receipt[@"unknownPID"], @"ESRCH");
    XCTAssertEqualObjects(receipt[@"hostSignalDenied"], @"ENOSYS");
    XCTAssertEqualObjects(receipt[@"networkDenied"], @5);
    XCTAssertEqualObjects(receipt[@"networkProxyConnections"], @3);
    XCTAssertEqualObjects(receipt[@"networkOtherConnections"], @0);
    XCTAssertEqualObjects(receipt[@"networkFork"], @YES);
    XCTAssertEqualObjects(receipt[@"networkConcurrent"], @YES);
    XCTAssertEqualObjects(receipt[@"networkImmutable"], @YES);
    XCTAssertEqualObjects(receipt[@"networkInheritedSocketDenied"], @YES);
    XCTAssertEqualObjects(receipt[@"namespaceDenied"], @YES);
    XCTAssertEqualObjects(receipt[@"filesystemAllowed"], @YES);
    XCTAssertEqualObjects(receipt[@"filesystemDenied"], @13);
    XCTAssertEqualObjects(receipt[@"filesystemLinks"], @YES);
    XCTAssertEqualObjects(receipt[@"filesystemExactTemp"], @YES);
    XCTAssertEqualObjects(receipt[@"filesystemInheritedDescriptors"], @2);
    XCTAssertEqualObjects(receipt[@"filesystemDescriptorRecheck"], @YES);
    XCTAssertEqualObjects(receipt[@"filesystemMmapDenied"], @YES);
    XCTAssertEqualObjects(receipt[@"filesystemConcurrent"], @2);
    XCTAssertEqualObjects(receipt[@"filesystemImmutable"], @YES);
    XCTAssertGreaterThan([receipt[@"filesystemSymlinkRaceCycles"] unsignedIntegerValue], 0UL);
    for (NSString *key in @[@"processDistinctGenerations", @"processForeignSignalsDenied",
            @"processForeignProcDenied", @"processOwnDescendant", @"processSignalABI",
            @"processNativeGeneration", @"processVictimSurvived"])
        XCTAssertEqualObjects(receipt[key], @YES, @"%@", key);
    XCTAssertEqualObjects(receipt[@"binaryBytes"], @131076);
    XCTAssertGreaterThan([receipt[@"guestPID"] intValue], 1);
    for (int i=0; i<3; i++) {
        struct stat after;
        XCTAssertEqual(fstat(i, &after), 0);
        XCTAssertEqual(after.st_dev, originalDescriptors[i].st_dev);
        XCTAssertEqual(after.st_ino, originalDescriptors[i].st_ino);
        XCTAssertEqual(after.st_mode, originalDescriptors[i].st_mode);
    }
    if ([receipt[@"ok"] boolValue]) [files removeItemAtURL:root error:nil];
}
@end
