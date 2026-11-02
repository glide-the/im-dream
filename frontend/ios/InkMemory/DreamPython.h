// [Input] Bundled Python paths and a named backend entry function.
// [Output] JSON returned by the embedded Dream Python module, or an NSError.
// [Pos] Objective-C boundary for CPython; startup is serialized and concurrent calls hold the GIL.
#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN
NSString * _Nullable IMDreamPythonCall(NSString *resources, NSString *function,
                                      NSString * _Nullable payload, NSError **error);
NS_ASSUME_NONNULL_END
