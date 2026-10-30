// [Input] Original workspace multipart response and the caller's translated failure message.
// [Output] Workspace path/time/hash normalization shared by browser and native upload callers.
// [Pos] Existing workspace upload DTO reader; no upload, workspace creation or policy ownership.
export async function readWorkspaceUploadResponse(response:Response,failureMessage:string) {
  const body=await response.json().catch(()=>({})) as {error?:string;code?:string;uploaded?:string[];files?:{workspacePath:string;savedAt:string;hash?:string}[]};
  if(!response.ok){const message=body.error || failureMessage;throw new Error(body.code?`${message} (${body.code})`:message);}
  const metadata=body.files?.[0];if(metadata?.workspacePath)return metadata;
  const path=body.uploaded?.[0];return path?{workspacePath:path,savedAt:new Date().toISOString()}:undefined;
}
