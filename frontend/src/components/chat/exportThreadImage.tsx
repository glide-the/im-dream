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
  /** One or more full-resolution PNG blob object URLs in top-to-bottom order (the
   *  partial head preview may be an SVG blob URL or, in the legacy fallback, a PNG
   *  data URL). Very long conversations exceed a single canvas's safe height and are
   *  split into multiple images; the preview stacks them seamlessly. Call
   *  releaseThreadImage when the preview is replaced/discarded or the dialog closes. */
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

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('slice image failed to load'));
    image.src = src;
  });
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error('canvas.toBlob failed'));
      }
    }, 'image/png');
  });
}

const yieldToUi = () => new Promise<void>((resolve) => { setTimeout(resolve, 0); });

function planSliceHeights(totalHeight: number): number[] {
  const heights: number[] = [];
  for (let offset = 0; offset < totalHeight; offset += SLICE_HEIGHT_PX) {
    heights.push(Math.min(SLICE_HEIGHT_PX, totalHeight - offset));
  }
  return heights;
}

/**
 * 流式拼接器 — 分片位图画入分块 canvas 后立即释放；块满即导出为压缩 PNG Blob 并销毁
 * canvas 位图。内存峰值 ≈ 1 片位图 + 1 块 canvas，与对话长度无关（旧方案持有全部
 * 分片位图直到拼接结束，长对话下 500MB+，是页面 OOM 崩溃的根因）。分片高度在截取前
 * 即可确定，因此每块 canvas 按精确高度一次性分配，分图之间无缝堆叠。
 */
class PartCanvasCollector {
  private readonly widthPx: number;
  private readonly background: string;
  private readonly partHeights: number[] = [];
  private readonly blobs: Blob[] = [];
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private cursorPx = 0;
  private partIndex = 0;

  constructor(widthPx: number, sliceHeightsPx: number[], background: string) {
    this.widthPx = widthPx;
    this.background = background;
    let acc = 0;
    for (const height of sliceHeightsPx) {
      if (acc > 0 && acc + height > MAX_PART_HEIGHT_PX) {
        this.partHeights.push(acc);
        acc = 0;
      }
      acc += height;
    }
    if (acc > 0) {
      this.partHeights.push(acc);
    }
  }

  private beginPart(): void {
    const canvas = document.createElement('canvas');
    canvas.width = this.widthPx;
    canvas.height = this.partHeights[this.partIndex];
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('failed to create stitch canvas context');
    }
    ctx.fillStyle = this.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    this.canvas = canvas;
    this.ctx = ctx;
    this.cursorPx = 0;
  }

  /** Draw one slice image at `scale` (CSS-unit slices pass 3; physical-pixel slices pass 1). */
  async add(image: HTMLImageElement, scale: number): Promise<void> {
    if (!this.canvas || !this.ctx) {
      this.beginPart();
    }
    const ctx = this.ctx as CanvasRenderingContext2D;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.drawImage(image, 0, this.cursorPx / scale);
    this.cursorPx += image.height * scale;
    if (this.cursorPx >= this.partHeights[this.partIndex]) {
      await this.flushPart();
    }
  }

  private async flushPart(): Promise<void> {
    if (!this.canvas) {
      return;
    }
    this.blobs.push(await canvasToBlob(this.canvas));
    // 立即销毁位图 — 压缩后的 Blob 通常只占几 MB。
    this.canvas.width = 0;
    this.canvas = null;
    this.ctx = null;
    this.partIndex += 1;
    this.cursorPx = 0;
  }

  async finish(): Promise<Blob[]> {
    if (this.canvas) {
      await this.flushPart();
    }
    return this.blobs;
  }
}

/**
 * Fast path — 单趟样式内联 + 流式输出：html-to-image 的开销几乎全部在「克隆整棵 DOM +
 * 逐节点 getComputedStyle 内联」，逐片 toPng 会把这份开销乘以片数（长对话下页面卡死的
 * 根因）。这里 toSvg 只调用一次，之后每个分片通过 SVG 字符串手术重建（视口 = 分片尺寸 +
 * foreignObject y 负偏移定位），交给浏览器栅格化；canvas 按 3x 绘制时 Chrome 会按
 * 绘制尺寸重新栅格化矢量内容，清晰度与逐片 toPng 一致（已用色块 + 3px 条纹探针在
 * Playwright 中逐片验证）。每片解码画入拼接器后立即释放位图（字符串拷贝随迭代结束
 * 被 GC），片间 setTimeout(0) 让出主线程保持页面响应。
 * 注意：分片必须用 data: URL — Chrome 会把 blob: URL 加载的含 foreignObject 的 SVG
 * 视为污染画布（toBlob/toDataURL 抛 SecurityError），data: URL 则无此限制。
 */
export async function capturePartBlobsFast(node: HTMLElement, onFirstSlice?: (previewUrl: string) => void): Promise<Blob[]> {
  const { toSvg } = await import('html-to-image');
  const totalHeight = node.offsetHeight;
  const cardWidth = node.offsetWidth;
  const background = getComputedStyle(node).backgroundColor || '#F6EFE5';
  const svgDataUrl = await toSvg(node);
  const svgText = decodeURIComponent(svgDataUrl.slice(svgDataUrl.indexOf(',') + 1));
  const openTag = svgText.match(/<svg[^>]*>/)?.[0];
  const foTag = svgText.match(/<foreignObject[^>]*>/)?.[0];
  const foClose = svgText.lastIndexOf('</foreignObject>');
  if (!openTag || !foTag || foClose < 0) {
    throw new Error('unexpected toSvg output structure');
  }
  const xmlnsAttrs = (openTag.match(/xmlns[^=]*="[^"]*"/g) ?? []).join(' ');
  const content = svgText.slice(svgText.indexOf(foTag) + foTag.length, foClose);

  const sliceHeights = planSliceHeights(totalHeight);
  const collector = new PartCanvasCollector(
    cardWidth * CAPTURE_PIXEL_RATIO,
    sliceHeights.map((height) => height * CAPTURE_PIXEL_RATIO),
    background,
  );

  let offset = 0;
  for (let index = 0; index < sliceHeights.length; index += 1) {
    const sliceHeight = sliceHeights[index];
    const slicedSvg = `<svg ${xmlnsAttrs} width="${cardWidth}" height="${sliceHeight}">`
      + `<foreignObject x="0" y="${-offset}" width="${cardWidth}" height="${totalHeight}">`
      + content
      + '</foreignObject></svg>';
    offset += sliceHeight;
    const sliceUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(slicedSvg)}`;
    const image = await loadImage(sliceUrl);
    // 首片 data URL 直接交给弹窗做预览头（SVG 可在 <img> 中显示）。
    if (index === 0) {
      onFirstSlice?.(sliceUrl);
    }
    await collector.add(image, CAPTURE_PIXEL_RATIO);
    image.src = ''; // 立即释放分片位图
    await yieldToUi();
  }
  return collector.finish();
}

/** Legacy per-slice toPng path — kept as a fallback if the SVG surgery ever fails. */
export async function capturePartBlobsLegacy(node: HTMLElement, host: HTMLElement, onFirstSlice?: (previewUrl: string) => void): Promise<Blob[]> {
  const { toPng } = await import('html-to-image');
  const totalHeight = node.offsetHeight;
  const cardWidth = node.offsetWidth;
  const background = getComputedStyle(node).backgroundColor || '#F6EFE5';
  const sliceHeights = planSliceHeights(totalHeight);
  const collector = new PartCanvasCollector(
    cardWidth * CAPTURE_PIXEL_RATIO,
    sliceHeights.map((height) => height * CAPTURE_PIXEL_RATIO),
    background,
  );

  let offset = 0;
  for (let index = 0; index < sliceHeights.length; index += 1) {
    const sliceHeight = sliceHeights[index];
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `width:${cardWidth}px;height:${sliceHeight}px;overflow:hidden;`;
    const clone = node.cloneNode(true) as HTMLElement;
    clone.style.marginTop = `-${offset}px`;
    wrapper.appendChild(clone);
    host.appendChild(wrapper);
    offset += sliceHeight;
    try {
      const dataUrl = await toPng(wrapper, { pixelRatio: CAPTURE_PIXEL_RATIO });
      if (index === 0) {
        onFirstSlice?.(dataUrl);
      }
      const image = await loadImage(dataUrl);
      await collector.add(image, 1);
      image.src = ''; // 立即释放分片位图
    } finally {
      wrapper.remove();
    }
    await yieldToUi();
  }
  return collector.finish();
}

async function capturePartBlobs(node: HTMLElement, host: HTMLElement, onFirstSlice?: (previewUrl: string) => void): Promise<Blob[]> {
  try {
    return await capturePartBlobsFast(node, onFirstSlice);
  } catch {
    return capturePartBlobsLegacy(node, host, onFirstSlice);
  }
}

/**
 * Render the conversation off-screen and return the long PNG (or PNG parts for very
 * long conversations) as blob object URLs — the share dialog shows them as a scrollable
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
    // 先出头部一段预览，避免用户空等 — 剩余切片在后台继续流式截取拼接。
    const partBlobs = await capturePartBlobs(node, host, (firstSliceUrl) => {
      hooks?.onPartialPreview?.({ images: [firstSliceUrl], fileName, partial: true });
    });
    const images = partBlobs.map((blob) => URL.createObjectURL(blob));
    if (images.length === 0) {
      throw new Error('export capture produced no image parts');
    }
    return { images, fileName };
  } finally {
    root.unmount();
    host.remove();
  }
}

/** Revoke every blob: object URL held by a rendered image or partial preview (data URLs
 *  are ignored). Must be called when a preview is replaced or discarded and when the
 *  share dialog closes — object URLs otherwise pin whole PNG blobs in memory forever. */
export function releaseThreadImage(rendered: RenderedThreadImage | null | undefined): void {
  if (!rendered) {
    return;
  }
  for (const url of rendered.images) {
    if (url.startsWith('blob:')) {
      URL.revokeObjectURL(url);
    }
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
