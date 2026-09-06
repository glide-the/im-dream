// [Input] Server-authored Story Workspace output receipts from ClaudeAgent SSE.
// [Output] Same-tab notifications that open Dream's canonical review surface.
// [Pos] Browser event boundary between Chat transport and Story Workspace UI.

export interface StoryWorkspaceOutputReceipt {
  story_id: string;
  review_status: 'pending';
  character_ids: string[];
  scene_ids: string[];
  chat_thread_id: string;
  deck_id?: string | null;
  deck_name?: string | null;
  deck_name_zh?: string | null;
  deck_name_en?: string | null;
}

const STORY_WORKSPACE_OUTPUT_EVENT = 'ink:story-workspace-output';

export function publishStoryWorkspaceOutput(receipt: StoryWorkspaceOutputReceipt): void {
  window.dispatchEvent(new CustomEvent<StoryWorkspaceOutputReceipt>(
    STORY_WORKSPACE_OUTPUT_EVENT,
    { detail: receipt },
  ));
}

export function subscribeStoryWorkspaceOutput(
  listener: (receipt: StoryWorkspaceOutputReceipt) => void,
): () => void {
  const handle = (event: Event) => {
    const receipt = (event as CustomEvent<StoryWorkspaceOutputReceipt>).detail;
    if (receipt?.story_id && receipt.review_status === 'pending') {
      listener(receipt);
    }
  };
  window.addEventListener(STORY_WORKSPACE_OUTPUT_EVENT, handle);
  return () => window.removeEventListener(STORY_WORKSPACE_OUTPUT_EVENT, handle);
}
