// [Input] Bundle resources and an application-private working directory.
// [Output] Embedded Node bootstrap startup; endpoint remains native/Python-owned.
// [Pos] Objective-C boundary for the iOS Node library.
#import <Foundation/Foundation.h>
NS_ASSUME_NONNULL_BEGIN
FOUNDATION_EXPORT NSString * _Nullable IMDreamNodeStart(NSString *resources, NSError **error);
NS_ASSUME_NONNULL_END
