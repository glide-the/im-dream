// [Sync] 2026-10-29: register operation-scoped system authorization for MCP resources; account login remains presentLogin.
// [Sync] 2026-10-29: register Foundation UUID generation in the existing module.
// [Sync] 2026-10-28: register image-only export data and grouped system share; single-file calls remain compatible.
// [Sync] 2026-10-28: register Workspace binary resource/text/export methods; existing HTTP/SSE methods remain.
// [Sync] 2026-10-28: export the existing message Copy action to the system clipboard.
// [Input] RN promise call metadata.
// [Output] Swift InkRuntime registration without importing its generated class interface twice.
// [Pos] Runtime module export; implementation stays in InkReactNative.swift.
// [Sync] 2026-10-28: export picked-file handles/upload and inherited upload-progress events.
// [Sync] 2026-10-28: export a PNG-only sketch import; paths and file leases remain native-owned.
#import <React/RCTBridgeModule.h>
#import <React/RCTEventEmitter.h>
@interface RCT_EXTERN_MODULE(InkRuntime, RCTEventEmitter)
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
