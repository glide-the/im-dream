// [Input] Existing Dream app host and isolated signed-package fixture resources.
// [Output] Target Bash execution receipt with application stdio and PID retained.
// [Pos] Provider-free target compatibility qualification, no account/model access.
#import <XCTest/XCTest.h>
#import <Foundation/Foundation.h>
#include <unistd.h>
#include <sys/stat.h>
extern int InkGuestRunFixture(const char *, char *, size_t, char *, size_t, int *);
@interface PosixCompatibilityTests : XCTestCase
@end
@implementation PosixCompatibilityTests
- (void)testActualGuestBashInsideExistingDreamApplication {
    NSBundle *bundle = [NSBundle bundleForClass:self.class];
    NSURL *source = [bundle.bundleURL URLByAppendingPathComponent:@"rootfs" isDirectory:YES];
    NSURL *root = [[NSURL fileURLWithPath:NSTemporaryDirectory() isDirectory:YES]
        URLByAppendingPathComponent:[@"ink-posix-fixture-" stringByAppendingString:NSUUID.UUID.UUIDString] isDirectory:YES];
    XCTAssertTrue([root.path hasPrefix:[NSHomeDirectory() stringByAppendingString:@"/"]]);
    NSError *copyError = nil;
    XCTAssertTrue([[NSFileManager defaultManager] copyItemAtURL:source toURL:root error:&copyError], @"%@", copyError);
    if (copyError) return;
    NSData *modesData = [NSData dataWithContentsOfURL:[bundle.bundleURL URLByAppendingPathComponent:@"guest-modes.json"]];
    NSArray *modes = [NSJSONSerialization JSONObjectWithData:modesData options:0 error:nil];
    XCTAssertNotNil(modes);
    for (NSDictionary *entry in modes) {
        NSString *relative = entry[@"path"];
        XCTAssertFalse([relative hasPrefix:@"/"]);
        XCTAssertFalse([relative.pathComponents containsObject:@".."]);
        NSNumber *mode = entry[@"mode"];
        XCTAssertLessThanOrEqual(mode.unsignedIntegerValue, 0777UL);
        NSError *modeError = nil;
        XCTAssertTrue([[NSFileManager defaultManager] setAttributes:@{NSFilePosixPermissions:mode}
            ofItemAtPath:[root.path stringByAppendingPathComponent:relative] error:&modeError], @"%@", modeError);
    }
    NSData *linksData = [NSData dataWithContentsOfURL:[bundle.bundleURL URLByAppendingPathComponent:@"guest-symlinks.json"]];
    NSArray *links = [NSJSONSerialization JSONObjectWithData:linksData options:0 error:nil];
    XCTAssertNotNil(links);
    for (NSDictionary *link in links) {
        NSString *relative = link[@"path"];
        XCTAssertFalse([relative hasPrefix:@"/"]);
        XCTAssertFalse([relative.pathComponents containsObject:@".."]);
        NSError *linkError = nil;
        XCTAssertTrue([[NSFileManager defaultManager] createSymbolicLinkAtPath:[root.path stringByAppendingPathComponent:relative]
            withDestinationPath:link[@"target"] error:&linkError], @"%@", linkError);
    }
    pid_t before = getpid();
    struct stat descriptors[3];
    for (int i=0; i<3; i++) XCTAssertEqual(fstat(i, &descriptors[i]), 0);
    XCTestExpectation *done = [self expectationWithDescription:@"Actual interpreted guest Bash finished"];
    __block int result = -2000;
    __block int guestPID = 0;
    __block NSString *stdoutText = nil;
    __block NSString *stderrText = nil;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        char output[4096] = {0}, errors[4096] = {0};
        result = InkGuestRunFixture(root.fileSystemRepresentation, output, sizeof(output), errors, sizeof(errors), &guestPID);
        stdoutText = [NSString stringWithUTF8String:output];
        stderrText = [NSString stringWithUTF8String:errors];
        [done fulfill];
    });
    [self waitForExpectations:@[done] timeout:60];
    XCTAssertEqual(result, 7);
    XCTAssertGreaterThan(guestPID, 1);
    XCTAssertTrue([stdoutText containsString:@"background-ok\nPIPE_ARRAY_SUBSHELL_WAIT_OK\nLinux aarch64\n"], @"%@", stdoutText);
    XCTAssertEqualObjects(stderrText, @"stderr-ok\n");
    NSString *written = [NSString stringWithContentsOfURL:[root URLByAppendingPathComponent:@"workspace/result.txt"] encoding:NSUTF8StringEncoding error:nil];
    XCTAssertEqualObjects(written, @"nested\n");
    XCTAssertEqual(before, getpid());
    for (int i=0; i<3; i++) {
        struct stat after;
        XCTAssertEqual(fstat(i, &after), 0);
        XCTAssertEqual(after.st_dev, descriptors[i].st_dev);
        XCTAssertEqual(after.st_ino, descriptors[i].st_ino);
        XCTAssertEqual(after.st_mode, descriptors[i].st_mode);
    }
    NSLog(@"IOS_POSIX_FIXTURE attemptedGuestBash=1 completedGuestBash=%d guestExit=%d guestPID=%d hostPID=%d stdioRetained=1 accounts=0 models=0", result == 7, result, guestPID, getpid());
    if (result == 7) [[NSFileManager defaultManager] removeItemAtURL:root error:nil];
}
@end
