// [Input] Validated Writing clipboard or PNG bytes and an exact document-lifetime guard.
// [Output] Existing native clipboard/file-share actions with imported-file cleanup.
// [Pos] Writing platform action adapter; importSketch and exportFiles retain byte/handle validation.
import {NativeModules} from 'react-native';
import {importNativeSketch, releaseNativeFiles} from './fileUpload.native';
import type {WritingShareRequest, WritingShareResult} from '../../app/_dream/components/Editor/WritingShare.protocol';
export async function performNoteShare(request: WritingShareRequest, active: () => boolean): Promise<WritingShareResult> {
  const files: string[] = [];
  try {
    if (!active()) return {requestId: request.requestId, status: 'cancelled'};
    if (request.kind === 'copy') {
      await NativeModules.InkRuntime.copyText(request.text);
      return {requestId: request.requestId, status: 'completed'};
    }
    for (const image of request.images) {
      const file = await importNativeSketch(image.base64, image.name, Number.MAX_SAFE_INTEGER);
      files.push(file.id);
      if (!active()) return {requestId: request.requestId, status: 'cancelled'};
    }
    const result = await NativeModules.InkRuntime.exportFiles(files) as {completed: boolean};
    return {requestId: request.requestId, status: result.completed ? 'completed' : 'cancelled'};
  } catch {return {requestId: request.requestId, status: 'failed'};}
  finally {releaseNativeFiles(files);}
}
