// [Input] ChatExportSnapshot (messages + pendingConfirmation + toolChoice) + thread title +
//         i18n labels from the ChatView share dialog.
// [Output] Converts UIMessage parts into ordered export blocks (text / reasoning / tool rows
//          and Terminal output cards), builds the static bottom confirmation card, renders
//          ThreadImageCard off-screen and captures it as a long PNG via html-to-image.
// [Pos] chat share long-image export node in frontend/src/components/chat
// [Sync] 2026-08-03: created for the share dialog export-image option.
// [Sync] 2026-08-03: export reasoning + tool invocation/output blocks (mirroring
//                    ChatMessageList collapsed rows and Terminal cards) and the single
//                    pending ToolConfirmationDock card pinned at the bottom of the image.
import { flushSync } from 'react-dom';
import { createRoot } from 'react-dom/client';
import { getToolName, isToolUIPart, type DynamicToolUIPart, type ToolUIPart, type UIMessage } from 'ai';
import type { TFunction } from 'i18next';
import ThreadImageCard, {
  type ExportBlock,
  type ExportChatMessage,
  type ExportConfirmationQuestion,
  type ExportImageLabels,
  type ExportPendingConfirmation,
  type ExportToolBlock,
} from './ThreadImageCard';
import {
  resolvePendingToolConfirmation,
  resolveToolName,
  type PendingToolConfirmation,
} from './toolConfirmation';
import { isEditorWriteTool } from './editorWriteTools';
import {
  isShellTool,
  resolveToolInputSummary,
  summarizeToolInvocation,
} from './toolInputSummary';
import type { AskUserQuestionInput, QuestionField } from './AskUserQuestionUI';

export type { ExportChatMessage, ExportImageLabels, ExportPendingConfirmation };

export interface ExportThreadImageOptions {
  threadId: string;
  title: string;
  messages: ExportChatMessage[];
  labels: ExportImageLabels;
  pendingConfirmation?: ExportPendingConfirmation | null;
}

const TOOL_COMPLETED_STATES = new Set(['output-available', 'output-error']);
const BUILTIN_WRITE_TOOL_NAMES = new Set(['write']);
const REASONING_CHAR_LIMIT = 8000;
const TOOL_OUTPUT_CHAR_LIMIT = 4000;

/** Local mirror of ChatMessageList.getToolOutputText (kept private there). */
function readToolOutputText(part: ToolUIPart | DynamicToolUIPart): string | null {
  if ('output' in part && part.output != null) {
    return typeof part.output === 'string' ? part.output : JSON.stringify(part.output, null, 2);
  }
  if ('error' in part && part.error != null) {
    return typeof part.error === 'string' ? part.error : JSON.stringify(part.error, null, 2);
  }
  return null;
}

/** Local mirror of ChatMessageList.parseTerminalOutput (kept private there). */
function parseTerminalOutput(raw: string): { command: string | null; output: string; exitCode: string | null } {
  const lines = raw.split('\n');
  let command: string | null = null;
  let exitCode: string | null = null;
  const outputLines: string[] = [];
  lines.forEach((line) => {
    const commandMatch = line.match(/^\$\s+(.+)/);
    const exitMatch = line.match(/^Exit code:\s*(\d+)/i);
    if (commandMatch && !command) command = commandMatch[1];
    else if (exitMatch) exitCode = exitMatch[1];
    else outputLines.push(line);
  });
  return { command, output: outputLines.join('\n').trim(), exitCode };
}

function truncateText(text: string, limit: number): { text: string; truncated: boolean } {
  if (text.length <= limit) {
    return { text, truncated: false };
  }
  return { text: text.slice(0, limit), truncated: true };
}

function toExportToolBlock(
  part: ToolUIPart | DynamicToolUIPart,
  toolChoice: string,
  t: TFunction,
): ExportToolBlock {
  const toolName = resolveToolName(part) || getToolName(part);
  const title = 'title' in part ? (part as { title?: string }).title : undefined;
  const input = 'input' in part ? part.input : undefined;
  const summary = summarizeToolInvocation(toolName, input) || undefined;
  const status: ExportToolBlock['status'] = part.state === 'output-error'
    ? 'error'
    : TOOL_COMPLETED_STATES.has(part.state ?? '')
      ? 'completed'
      : 'executing';

  const pendingKind = resolvePendingToolConfirmation(part, toolChoice);
  const pendingLabel = pendingKind === 'askuser'
    ? t('chat.toolConfirmation.pendingAnswer')
    : pendingKind
      ? t('chat.toolConfirmation.pendingConfirm')
      : undefined;

  const base: ExportToolBlock = { kind: 'tool', toolName, title, summary, status, pendingLabel };

  // Completed editor-write tools render as a quiet success row (their specialized
  // completed card shows file diffs in-app; the image keeps a one-line record).
  if (isEditorWriteTool(toolName) && status !== 'executing') {
    return { ...base, isEditorWrite: true };
  }

  const isWrite = BUILTIN_WRITE_TOOL_NAMES.has(toolName.toLowerCase());
  const outputText = readToolOutputText(part);

  if (isWrite) {
    const value = input && typeof input === 'object' && !Array.isArray(input)
      ? (input as Record<string, unknown>)
      : {};
    const filePath = typeof value.file_path === 'string' ? value.file_path : '';
    const content = typeof value.content === 'string' ? value.content : '';
    const bodyText = content || outputText || '';
    const { text, truncated } = truncateText(bodyText, TOOL_OUTPUT_CHAR_LIMIT);
    return {
      ...base,
      terminalLabel: t('chat.share.write'),
      command: `write ${filePath || 'pending-path'}`,
      output: text || undefined,
      outputTruncated: truncated,
      statusLabel: status === 'error'
        ? t('chat.share.writeFailed')
        : part.state === 'output-available'
          ? t('chat.share.written')
          : t('chat.share.writing'),
    };
  }

  if (status !== 'executing' && outputText) {
    const parsed = parseTerminalOutput(outputText);
    const command = resolveToolInputSummary(input).command || parsed.command || undefined;
    const body = parsed.output || outputText;
    const { text, truncated } = truncateText(body, TOOL_OUTPUT_CHAR_LIMIT);
    return {
      ...base,
      terminalLabel: t('chat.share.terminal'),
      command,
      output: text || undefined,
      outputTruncated: truncated,
      exitCode: parsed.exitCode,
    };
  }

  return base;
}

/** Convert a UIMessage into ordered export blocks; null when nothing exportable remains. */
export function toExportChatMessage(message: UIMessage, toolChoice: string, t: TFunction): ExportChatMessage | null {
  if (message.role !== 'user' && message.role !== 'assistant') {
    return null;
  }
  const blocks: ExportBlock[] = [];
  const files: string[] = [];

  for (const part of message.parts ?? []) {
    if (part.type === 'text') {
      const text = ((part as { text?: string }).text ?? '').trim();
      if (text) {
        blocks.push({ kind: 'text', text });
      }
      continue;
    }
    if (part.type === 'reasoning') {
      const reasoningText = (part as { text?: string }).text ?? '';
      if (reasoningText.trim()) {
        const { text } = truncateText(reasoningText.trim(), REASONING_CHAR_LIMIT);
        blocks.push({ kind: 'reasoning', text });
      }
      continue;
    }
    if (part.type === 'file') {
      const filename = (part as { filename?: string }).filename ?? '';
      if (filename) {
        files.push(filename);
      }
      continue;
    }
    if (message.role === 'assistant' && isToolUIPart(part)) {
      blocks.push(toExportToolBlock(part as ToolUIPart | DynamicToolUIPart, toolChoice, t));
    }
  }

  if (blocks.length === 0 && files.length === 0) {
    return null;
  }
  return { role: message.role, blocks, files };
}

function toExportConfirmationQuestions(input: unknown, t: TFunction): ExportConfirmationQuestion[] {
  const value = (input ?? {}) as AskUserQuestionInput;
  if (Array.isArray(value.questions) && value.questions.length > 0) {
    return value.questions.map((question: QuestionField) => ({
      question: question.question ?? question.label ?? question.header ?? t('chat.askUser.fallbackQuestion'),
      required: question.required === true,
      description: question.description,
      options: (question.options ?? []).map((option) => (
        typeof option === 'string'
          ? { label: option }
          : { label: option.label, description: 'description' in option ? option.description : undefined }
      )),
    }));
  }
  const fallbackQuestion = value.question ?? value.message ?? value.text ?? value.prompt;
  const fallbackOptions = value.options ?? value.choices ?? [];
  if (!fallbackQuestion && fallbackOptions.length === 0) {
    return [];
  }
  return [{
    question: fallbackQuestion ?? t('chat.askUser.fallbackQuestion'),
    options: fallbackOptions.map((option) => ({ label: option })),
  }];
}

/**
 * Build the static bottom card mirroring ToolConfirmationDock for the exported image.
 * Returns null when no confirmation is pending.
 */
export function buildExportPendingConfirmation(
  confirmation: PendingToolConfirmation | null,
  t: TFunction,
): ExportPendingConfirmation | null {
  if (!confirmation) {
    return null;
  }
  const { kind, toolName, input } = confirmation;
  const summaryText = summarizeToolInvocation(toolName, input);
  const unknownTool = t('chat.toolConfirmation.unknownTool');

  if (kind === 'askuser') {
    return {
      kind,
      title: t('chat.toolConfirmation.askUserTitle'),
      badge: t('chat.toolConfirmation.pendingAnswer'),
      questions: toExportConfirmationQuestions(input, t),
      primaryActionLabel: t('chat.toolConfirmation.submit'),
      secondaryActionLabel: t('chat.toolConfirmation.cancel'),
    };
  }

  if (kind === 'sandbox-network') {
    const networkRequest = confirmation.networkRequest ?? null;
    const policyModeText = networkRequest?.policyMode === 'allowlist'
      ? t('chat.toolConfirmation.networkPolicyAllowlist')
      : networkRequest?.policyMode === 'open'
        ? t('chat.toolConfirmation.networkPolicyOpen')
        : networkRequest?.policyMode || unknownTool;
    return {
      kind,
      title: t('chat.toolConfirmation.networkConfirmTitle', { tool: toolName || unknownTool }),
      badge: t('chat.toolConfirmation.pendingApproval'),
      infoRows: [
        t('chat.toolConfirmation.networkHostLabel') + (networkRequest?.host ?? t('chat.toolConfirmation.networkHostUnknown')),
        t('chat.toolConfirmation.networkPolicyLabel') + policyModeText,
      ],
      primaryActionLabel: t('chat.toolConfirmation.approve'),
      secondaryActionLabel: t('chat.toolConfirmation.reject'),
    };
  }

  const commandText = isShellTool(toolName) ? resolveToolInputSummary(input).command : '';
  let detail = commandText;
  if (!detail && input != null) {
    try {
      const json = JSON.stringify(input);
      detail = json.length > 240 ? `${json.slice(0, 240)}…` : json;
    } catch {
      detail = String(input);
    }
  }
  return {
    kind,
    title: t('chat.toolConfirmation.confirmTitle', { tool: toolName || unknownTool })
      + (summaryText ? t('chat.toolConfirmation.withSummary', { summary: summaryText }) : ''),
    badge: t('chat.toolConfirmation.pendingApproval'),
    detail: detail || undefined,
    primaryActionLabel: t('chat.toolConfirmation.approve'),
    secondaryActionLabel: t('chat.toolConfirmation.reject'),
  };
}

export interface RenderedThreadImage {
  /** One or more full-resolution PNG data URLs in top-to-bottom order. Very long
   *  conversations exceed a single canvas's safe height and are split into multiple
   *  images; the preview stacks them seamlessly. */
  images: string[];
  /** Base file name (single image) — part suffixes are added when split. */
  fileName: string;
  /** True while only the head segment has been rendered — the rest is still processing. */
  partial?: boolean;
}

export interface RenderThreadImageHooks {
  /** Fired as soon as the first slice is captured so the dialog can show a head
   *  preview immediately instead of making the user wait for the full render. */
  onPartialPreview?: (preview: RenderedThreadImage) => void;
}

/**
 * 拼接方案 — the card is captured in vertical slices (each always at full CAPTURE_PIXEL_RATIO,
 * independent of total height) and stitched at the slices' ACTUAL pixel size — never
 * downscaled. A one-shot html-to-image capture of a very tall node forces the pixel ratio
 * down once the canvas hits the browser's edge/area limit, which is what made long exports
 * blurry; slices stay well under the limit so every pixel is rasterized at 3x. When the
 * stitched result would exceed a single canvas's safe height, it is emitted as multiple
 * full-resolution PNG parts instead of shrinking.
 */
const SLICE_HEIGHT_PX = 2000;
const CAPTURE_PIXEL_RATIO = 3;
/** Safe per-canvas height in physical pixels (browsers cap canvas edge ≈ 16384). */
const MAX_PART_HEIGHT_PX = 15000;

function loadImage(dataUrl: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('slice image failed to load'));
    image.src = dataUrl;
  });
}

async function captureCardSlices(node: HTMLElement, host: HTMLElement, onFirstSlice?: (dataUrl: string) => void): Promise<HTMLImageElement[]> {
  const { toPng } = await import('html-to-image');
  const totalHeight = node.offsetHeight;
  const cardWidth = node.offsetWidth;
  const slices: HTMLImageElement[] = [];
  for (let offset = 0; offset < totalHeight; offset += SLICE_HEIGHT_PX) {
    const sliceHeight = Math.min(SLICE_HEIGHT_PX, totalHeight - offset);
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `width:${cardWidth}px;height:${sliceHeight}px;overflow:hidden;`;
    const clone = node.cloneNode(true) as HTMLElement;
    clone.style.marginTop = `-${offset}px`;
    wrapper.appendChild(clone);
    host.appendChild(wrapper);
    try {
      const dataUrl = await toPng(wrapper, { pixelRatio: CAPTURE_PIXEL_RATIO });
      if (slices.length === 0) {
        onFirstSlice?.(dataUrl);
      }
      slices.push(await loadImage(dataUrl));
    } finally {
      wrapper.remove();
    }
  }
  return slices;
}

/**
 * Stitch 3x slices at their natural pixel size. Slices are grouped so every output
 * canvas stays under MAX_PART_HEIGHT_PX; each canvas is emitted as its own PNG part.
 */
function stitchSlices(node: HTMLElement, slices: HTMLImageElement[]): string[] {
  const background = getComputedStyle(node).backgroundColor || '#F6EFE5';
  const parts: string[] = [];
  let group: HTMLImageElement[] = [];
  let groupHeight = 0;

  const flushGroup = () => {
    if (group.length === 0) {
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = group[0].width;
    canvas.height = groupHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('failed to create stitch canvas context');
    }
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    let cursorY = 0;
    for (const slice of group) {
      ctx.drawImage(slice, 0, cursorY);
      cursorY += slice.height;
    }
    parts.push(canvas.toDataURL('image/png'));
    group = [];
    groupHeight = 0;
  };

  for (const slice of slices) {
    if (groupHeight + slice.height > MAX_PART_HEIGHT_PX && group.length > 0) {
      flushGroup();
    }
    group.push(slice);
    groupHeight += slice.height;
  }
  flushGroup();
  return parts;
}

/**
 * Render the conversation off-screen and return the long PNG (or PNG parts for very
 * long conversations) as data URLs — the share dialog shows them as a scrollable
 * preview before downloading. Throws when rendering or capture fails.
 */
export async function renderThreadImage({ threadId, title, messages, labels, pendingConfirmation }: ExportThreadImageOptions, hooks?: RenderThreadImageHooks): Promise<RenderedThreadImage> {
  const host = document.createElement('div');
  host.style.cssText = 'position:fixed;left:-100000px;top:0;z-index:-1;pointer-events:none;';
  document.body.appendChild(host);
  const root = createRoot(host);
  try {
    flushSync(() => {
      root.render(
        <ThreadImageCard
          title={title}
          messages={messages}
          labels={labels}
          pendingConfirmation={pendingConfirmation}
          dateText={new Date().toLocaleDateString()}
        />,
      );
    });
    const node = host.firstElementChild as HTMLElement | null;
    if (!node) {
      throw new Error('export render produced no node');
    }
    await document.fonts.ready;
    // Give the off-screen tree two frames to settle layout before capture.
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });
    const safeTitle = title.replace(/[^\w一-龥-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48) || 'chat';
    const fileName = `ink-memory-${safeTitle}-${threadId.slice(0, 8)}.png`;
    // 先出头部一段预览，避免用户空等 — 剩余切片在后台继续截取拼接。
    const slices = await captureCardSlices(node, host, (firstSliceDataUrl) => {
      hooks?.onPartialPreview?.({ images: [firstSliceDataUrl], fileName, partial: true });
    });
    const images = stitchSlices(node, slices);

    return { images, fileName };
  } finally {
    root.unmount();
    host.remove();
  }
}

/** Trigger browser downloads for a previously rendered preview. Multi-part renders are
 *  merged back into ONE big PNG at the binary level (png-stitch — no canvas, no size
 *  ceiling); per-part downloads remain as the fallback if stitching fails. */
export async function downloadThreadImage(rendered: RenderedThreadImage): Promise<void> {
  const triggerDownload = (href: string, fileName: string) => {
    const link = document.createElement('a');
    link.href = href;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  if (rendered.images.length === 1) {
    triggerDownload(rendered.images[0], rendered.fileName);
    return;
  }

  try {
    const { stitchPngPartsToBlob } = await import('../../lib/png-stitch');
    const blob = await stitchPngPartsToBlob(rendered.images);
    const objectUrl = URL.createObjectURL(blob);
    triggerDownload(objectUrl, rendered.fileName);
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    return;
  } catch {
    // fall through to per-part downloads
  }

  const dotIndex = rendered.fileName.lastIndexOf('.');
  const base = dotIndex > 0 ? rendered.fileName.slice(0, dotIndex) : rendered.fileName;
  const ext = dotIndex > 0 ? rendered.fileName.slice(dotIndex) : '.png';
  rendered.images.forEach((dataUrl, index) => {
    triggerDownload(dataUrl, `${base}-part-${index + 1}-of-${rendered.images.length}${ext}`);
  });
}
