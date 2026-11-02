// [Input] Original composer submission, upload state, effective tool permission and draft defaults.
// [Output] Shared draft/files/permission state and the original send, clear and rejection-restore behavior.
// [Pos] Headless Web/native composer state extracted from AIInputDock; no DOM, HTTP or runtime ownership.
import {useCallback,useState} from 'react';
import type {TFunction} from 'i18next';
import type {ToolChoice} from '../../lib/chat-schema';
import type {UploadedFile} from './AIInputDock.helpers';

export function buildToolChoiceOptions(t:TFunction):{value:ToolChoice;label:string;title:string}[] {
  return [
    {value:'auto',label:t('chat.inputDock.toolChoiceAuto'),title:t('chat.inputDock.toolChoiceAutoTitle')},
    {value:'manual',label:t('chat.inputDock.toolChoiceManual'),title:t('chat.inputDock.toolChoiceManualTitle')},
  ];
}

export interface ComposerDraftOptions {
  onSendMessage: (message:string,files?:UploadedFile[],toolChoice?:ToolChoice) => void | Promise<void>;
  disabled: boolean;
  loading: boolean;
  onStop?: () => void | Promise<void>;
  fullAccessEnabled: boolean;
  defaultToolChoice: ToolChoice;
  initialDraft?: string;
  onUploadBlocked: () => void;
  releasePreview: (url?:string) => void;
}

export default function useComposerDraft({onSendMessage,disabled,loading,onStop,fullAccessEnabled,defaultToolChoice,initialDraft,onUploadBlocked,releasePreview}:ComposerDraftOptions) {
  const [query,setQuery] = useState(() => initialDraft ?? '');
  const [uploadedFiles,setUploadedFiles] = useState<UploadedFile[]>([]);
  const [toolChoice,setToolChoice] = useState<ToolChoice>(defaultToolChoice);
  const handleSend = useCallback(() => {
    if (disabled || (loading && !onStop)) return;
    if (uploadedFiles.some(file => file.isUploading)) {onUploadBlocked();return;}
    const trimmedQuery = query.trim();
    if (!trimmedQuery && uploadedFiles.length === 0) return;
    setQuery('');setUploadedFiles([]);
    const restoreDraft = () => {
      setQuery(current => current || trimmedQuery);
      setUploadedFiles(current => current.length > 0 ? current : uploadedFiles);
    };
    try {
      void Promise.resolve(onSendMessage(trimmedQuery,uploadedFiles.length > 0 ? uploadedFiles : undefined,fullAccessEnabled ? 'auto' : toolChoice))
        .then(() => uploadedFiles.forEach(file => releasePreview(file.previewUrl)),restoreDraft);
    } catch {restoreDraft();}
  },[disabled,loading,onStop,uploadedFiles,query,onSendMessage,fullAccessEnabled,toolChoice,onUploadBlocked,releasePreview]);
  const hasUploadingFiles = uploadedFiles.some(file => file.isUploading);
  const hasDraftContent = query.trim().length > 0 || uploadedFiles.length > 0;
  return {
    query,setQuery,uploadedFiles,setUploadedFiles,toolChoice,setToolChoice,handleSend,hasUploadingFiles,hasDraftContent,
    showStopAction:loading && Boolean(onStop) && !hasDraftContent,
    canSend:!disabled && (!loading || Boolean(onStop)) && !hasUploadingFiles && hasDraftContent,
  };
}
