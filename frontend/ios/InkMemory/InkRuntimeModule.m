// [Sync] 2026-11-03: expose the unified character/clock view and its display-only mode/color properties.
// [Sync] 2026-10-29: register operation-scoped system authorization for MCP resources; account login remains presentLogin.
// [Sync] 2026-10-29: register Foundation UUID generation in the existing module.
// [Sync] 2026-10-28: register image-only export data and grouped system share; single-file calls remain compatible.
// [Sync] 2026-10-28: register Workspace binary resource/text/export methods; existing HTTP/SSE methods remain.
// [Sync] 2026-10-28: export the existing message Copy action to the system clipboard.
// [Sync] 2026-11-03: export native presence and the idle overlay's material view without task control.
// [Input] RN promise call metadata.
// [Sync] 2026-11-03: register one-shot own-process CPU sampling; the diagnostics view owns scheduling.
// [Sync] 2026-11-02: expose scene-local diagnostics visibility and dismissal; runtime and authentication methods retain their owners.
// [Output] Swift InkRuntime registration without importing its generated class interface twice.
// [Pos] Runtime module export; implementation stays in InkReactNative.swift.
// [Sync] 2026-10-28: export picked-file handles/upload and inherited upload-progress events.
// [Sync] 2026-10-28: export a PNG-only sketch import; paths and file leases remain native-owned.
#import <React/RCTBridgeModule.h>
#import <React/RCTEventEmitter.h>
#import <React/RCTViewManager.h>
@interface RCT_EXTERN_MODULE(InkRuntime, RCTEventEmitter)
RCT_EXTERN_METHOD(configureThreadPresence:(NSString * _Nullable)ownerId resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(canShowIdleOverlay:(BOOL)inModal resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(readPerformanceSample:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(configureDiagnosticsOverlay:(NSDictionary *)options)
RCT_EXTERN_METHOD(dismissRuntimeDiagnostics)
RCT_EXTERN_METHOD(randomUUID:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(presentMcpAuthorization:(NSDictionary *)options resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(cancelMcpAuthorization:(NSString *)operationId)
RCT_EXTERN_METHOD(ensureStarted:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(openRequest:(NSDictionary *)options resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(readResponse:(NSString *)requestId resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(cancelRequest:(NSString *)requestId)
RCT_EXTERN_METHOD(pickFiles:(NSDictionary *)options resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(releaseFiles:(NSArray *)ids)
RCT_EXTERN_METHOD(importSketch:(NSDictionary *)options resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(openFileUpload:(NSDictionary *)options resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(copyText:(NSString *)text resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(readWorkspaceFile:(NSDictionary *)options resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(cancelWorkspaceFile:(NSString *)requestId)
RCT_EXTERN_METHOD(readWorkspaceText:(NSString *)fileId resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(copyWorkspaceFile:(NSString *)fileId resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(readWorkspaceImage:(NSString *)fileId resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(exportFiles:(NSArray *)fileIds resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(exportFile:(NSString *)fileId resolver:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
RCT_EXTERN_METHOD(presentLogin:(RCTPromiseResolveBlock)resolve rejecter:(RCTPromiseRejectBlock)reject)
@end

@interface RCT_EXTERN_MODULE(InkIdleBackdrop, RCTViewManager)
@end

@interface RCT_EXTERN_MODULE(InkKastentionClock, RCTViewManager)
RCT_EXPORT_VIEW_PROPERTY(enabled, BOOL)
RCT_EXPORT_VIEW_PROPERTY(clockMode, NSString)
RCT_EXPORT_VIEW_PROPERTY(faceMood, NSString)
RCT_EXPORT_VIEW_PROPERTY(colorInk, UIColor)
RCT_EXPORT_VIEW_PROPERTY(colorMinute, UIColor)
RCT_EXPORT_VIEW_PROPERTY(colorSecond, UIColor)
RCT_EXPORT_VIEW_PROPERTY(colorPaper, UIColor)
@end
