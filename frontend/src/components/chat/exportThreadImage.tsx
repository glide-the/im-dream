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
import { EXPORT_FONT_UNCOVERED_RANGES } from './exportFontSubset';

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
  /** 截取进度（done/total 块数）— 弹窗用它渲染进度条。 */
  onProgress?: (progress: { done: number; total: number }) => void;
}

/**
 * 拼接方案 — the card is captured in vertical tiles (each always at full CAPTURE_PIXEL_RATIO,
 * independent of total height) and stitched at the tiles' ACTUAL pixel size — never
 * downscaled. A one-shot html-to-image capture of a very tall node forces the pixel ratio
 * down once the canvas hits the browser's edge/area limit, which is what made long exports
 * blurry; tiles stay well under the limit so every pixel is rasterized at 3x. When the
 * stitched result would exceed a single canvas's safe height, it is emitted as multiple
 * full-resolution PNG parts instead of shrinking.
 */
const SLICE_HEIGHT_PX = 2000;
/** DOM-tile 路径的单块最大高度（CSS px）— 每块独立序列化，字符串开销有界；
 *  取 4000（3x 物理 12000，仍低于 canvas 上限 15000）以减半块数、摊薄每块固定开销。 */
const TILE_HEIGHT_CSS = 5000;
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

/**
 * 让出主线程直到下一帧绘制完成 — 进度条等 UI 更新有机会真正上屏。
 * 后台标签页 rAF 不触发，用 120ms 超时兜底避免卡死。
 */
const yieldToUi = () => new Promise<void>((resolve) => {
  const timer = setTimeout(resolve, 120);
  requestAnimationFrame(() => {
    clearTimeout(timer);
    setTimeout(resolve, 0);
  });
});

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

export interface CaptureProgressHooks {
  onFirstSlice?: (previewUrl: string) => void;
  onProgress?: (progress: { done: number; total: number }) => void;
}

/** 从首块 toSvg 输出中提取内嵌字体的 <style> 元素（无字体时返回空串）。 */
function extractFontStyleElement(svgText: string): string {
  const match = svgText.match(/<style[^>]*>[\s\S]*?<\/style>/);
  return match?.[0] ?? '';
}

const SVG_DATA_PREFIX = 'data:image/svg+xml;charset=utf-8,';
const decodeSvgDataUrl = (url: string) => decodeURIComponent(url.slice(url.indexOf(',') + 1));

/** 把「已编码」的字体 <style> 拼进后续块的 data URL（skipFonts 后由我们补回）。
 *  字体 base64 可达 16MB，若对整块 SVG 跑 encodeURIComponent，每块都要逐字符
 *  重编码这份字体（CPU 主因之一）；这里只对几 KB 的正文两段做编码，字体编码串
 *  全局只算一次，最终 URL 以 rope 拼接（img.src 赋值时一次平坦化）。 */
function spliceEncodedFontStyle(dataUrl: string, encodedFontStyle: string): string | null {
  const svgText = decodeSvgDataUrl(dataUrl); // skipFonts 后的正文，只有几 KB
  const foIndex = svgText.indexOf('<foreignObject');
  if (foIndex < 0) {
    return null;
  }
  const divIndex = svgText.indexOf('<div', foIndex);
  if (divIndex < 0) {
    return null;
  }
  const gtIndex = svgText.indexOf('>', divIndex);
  if (gtIndex < 0) {
    return null;
  }
  return SVG_DATA_PREFIX
    + encodeURIComponent(svgText.slice(0, gtIndex + 1))
    + encodedFontStyle
    + encodeURIComponent(svgText.slice(gtIndex + 1));
}

/**
 * 导出字体计划 — CPU 优化的核心。
 * 实测：SVG 图像文档禁止外部子资源（blob:/http: 字体 URL 会被静默忽略、仅 data: 内嵌有效），
 * 而完整 Xiaolai 有 11.8MB（base64 后约 16MB），Chrome 对每个分块 SVG 都要重新解析一遍字体
 * （约 190ms/块，占整条管线 CPU 的 60%+）。构建期用 fonttools 生成 1.5MB 的 GB2312 子集
 * （scripts/subset-export-font.py），解析耗时降为约 1/3；逐块扫描文本，命中子集未覆盖的
 * 生僻字（EXPORT_FONT_UNCOVERED_RANGES，即全量 cmap 减子集）时回退全量内嵌字体，
 * 保证任何字符都渲染正确。子集内同时内嵌 Excalifont 全量（52KB，Latin unicode-range
 * 与 App.css 保持一致），确保中英混排的字体选择与页面一致。
 */
interface ExportFontPlan {
  /** 已 encodeURIComponent 的 <style>（Xiaolai 子集 + Excalifont 全量）。 */
  subsetEncodedStyle: string;
}

let exportFontPlanPromise: Promise<ExportFontPlan | null> | null = null;

async function blobToBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = '';
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(binary);
}

function getExportFontPlan(): Promise<ExportFontPlan | null> {
  if (!exportFontPlanPromise) {
    exportFontPlanPromise = (async () => {
      try {
        const base = (import.meta as { env?: { BASE_URL?: string } }).env?.BASE_URL ?? '/';
        const [xiaolaiRes, excaliRes] = await Promise.all([
          fetch(`${base}Xiaolai-ExportSubset.woff2`),
          fetch(`${base}Excalifont-Regular.woff2`),
        ]);
        if (!xiaolaiRes.ok || !excaliRes.ok) {
          return null;
        }
        const [xB64, eB64] = await Promise.all([
          xiaolaiRes.blob().then(blobToBase64),
          excaliRes.blob().then(blobToBase64),
        ]);
        const style = '<style>'
          + `@font-face{font-family:'Excalifont';src:url(data:font/woff2;base64,${eB64}) format('woff2');`
          + 'font-weight:normal;font-style:normal;'
          + 'unicode-range:U+0000-00FF,U+0100-017F,U+0180-024F,U+1E00-1EFF,U+2000-206F,U+20A0-20CF,U+2100-214F;}'
          + `@font-face{font-family:'Xiaolai';src:url(data:font/woff2;base64,${xB64}) format('woff2');`
          + 'font-weight:normal;font-style:normal;}'
          + '</style>';
        return { subsetEncodedStyle: encodeURIComponent(style) };
      } catch {
        return null; // 子集不可用（如 dev 未生成文件）→ 回退逐块全量内嵌
      }
    })();
  }
  return exportFontPlanPromise;
}

/** 文本是否包含子集字体未覆盖的生僻字（命中即该块回退全量字体渲染）。 */
function textNeedsFullFont(text: string): boolean {
  for (const ch of text) {
    const cp = ch.codePointAt(0) ?? 0;
    let lo = 0;
    let hi = EXPORT_FONT_UNCOVERED_RANGES.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const range = EXPORT_FONT_UNCOVERED_RANGES[mid];
      if (cp < range[0]) {
        hi = mid - 1;
      } else if (cp > range[1]) {
        lo = mid + 1;
      } else {
        return true;
      }
    }
  }
  return false;
}

/**
 * SVG 内嵌字体预热 — 修复冷启动竞态。
 * 实测：SVG 图像文档首次加载某份内嵌字体（按字体 data URL 缓存）时，foreignObject 的
 * 布局可能在字体解码完成前完成，导致整块文本空白（同一 SVG 首载空白、再载正常）。
 * 在正式加载各分块前，用一个内嵌**相同字体字节**的微型探针 SVG 反复加载并做像素验证，
 * 直到字体真正生效；此后所有分块（同一字体 URL）的渲染即为确定性。
 * 探针文本需覆盖字体栈中各族的典型字符（CJK / Latin / 数字 / 标点）。
 */
const SVG_FONT_WARMUP_MAX_ATTEMPTS = 40;
async function warmupEmbeddedFonts(encodedFontStyle: string): Promise<void> {
  try {
    const style = decodeURIComponent(encodedFontStyle);
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="64">'
      + style
      + '<foreignObject width="100%" height="100%">'
      + '<div xmlns="http://www.w3.org/1999/xhtml" style="'
      + "font-family:'Excalifont','Xiaolai',Georgia,serif;font-size:20px;line-height:1.4;"
      + 'background:#ffffff;color:#000000;padding:4px;">墨问A1。</div>'
      + '</foreignObject></svg>';
    const url = SVG_DATA_PREFIX + encodeURIComponent(svg);
    for (let attempt = 0; attempt < SVG_FONT_WARMUP_MAX_ATTEMPTS; attempt += 1) {
      const image = await loadImage(url);
      const canvas = document.createElement('canvas');
      canvas.width = 240;
      canvas.height = 64;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) {
        return;
      }
      ctx.drawImage(image, 0, 0);
      image.src = '';
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      let dark = 0;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i] < 128) {
          dark += 1;
          if (dark > 50) {
            return; // 字体已生效
          }
        }
      }
      await new Promise((resolve) => { setTimeout(resolve, 50); });
    }
  } catch {
    // 预热是 best-effort：失败不阻断导出（退化为旧行为，大概率仍能渲染）。
  }
}


/**
 * Tile 路径 — DOM 分块截取：把卡片的直接子节点按像素高度分组为若干 tile（每块
 * ≤TILE_HEIGHT_CSS），每块用「卡片浅克隆容器 + 该组子节点深克隆」单独 toSvg。
 * 这样任何时刻都不存在完整对话的 SVG 文本（长对话下单趟 toSvg 的字符串可达数百 MB，
 * encodeURIComponent 后更可达 6-9 倍，是 Chrome 卡死/OOM 的根因），单块的序列化/编码
 * 开销严格有界。子节点间距通过实测 getBoundingClientRect 换算为克隆节点的显式
 * margin-top（规避 margin 折叠双倍计数），拼回后与原排版逐像素一致；容器 overflow:hidden
 * 建立 BFC 防止首尾 margin 穿透，并裁齐整数块高。SVG 图像文档要求字体 base64 内嵌，
 * 而 Chrome 对每块都重新解析字体（完整 Xiaolai 11.8MB，约 190ms/块，是 CPU 占满的主因），
 * 因此默认改用构建期生成的 1.5MB GB2312 子集字体（见 getExportFontPlan），仅当分块文本
 * 命中子集未覆盖的生僻字时才回退全量内嵌。块间让出主线程到下一帧，保证进度条实时上屏。
 */
export async function capturePartBlobsTiled(node: HTMLElement, host: HTMLElement, hooks?: CaptureProgressHooks): Promise<Blob[]> {
  const { toSvg } = await import('html-to-image');
  const totalHeight = node.offsetHeight;
  const cardWidth = node.offsetWidth;
  const background = getComputedStyle(node).backgroundColor || '#F6EFE5';
  const cardRect = node.getBoundingClientRect();
  const children = Array.from(node.children) as HTMLElement[];
  if (children.length === 0) {
    throw new Error('export card has no element children to tile');
  }

  // 1) 实测每个子节点相对卡片顶部的位置（含 margin 折叠后的真实渲染结果）。
  const metrics = children.map((el) => {
    const rect = el.getBoundingClientRect();
    return { top: rect.top - cardRect.top, bottom: rect.bottom - cardRect.top };
  });

  // 2) 按高度分组为 tiles；边界取整避免分数漂移产生接缝。
  interface Tile { start: number; end: number; topCss: number; heightCss: number }
  const tiles: Tile[] = [];
  let tileStart = 0;
  let tileTop = 0;
  for (let i = 0; i < children.length; i += 1) {
    const bottom = Math.round(metrics[i].bottom);
    if (i > tileStart && bottom - tileTop > TILE_HEIGHT_CSS) {
      // 边界取上一个子节点的底部 — 当前子节点属于下一块。
      const boundary = Math.round(metrics[i - 1].bottom);
      tiles.push({ start: tileStart, end: i, topCss: tileTop, heightCss: boundary - tileTop });
      tileStart = i;
      tileTop = boundary;
    }
  }
  tiles.push({ start: tileStart, end: children.length, topCss: tileTop, heightCss: totalHeight - tileTop });
  // 单个子节点超高时整 tile 超高，超出分块 canvas 上限则放弃 fast 路径（回退 legacy）。
  if (tiles.some((tile) => tile.heightCss * CAPTURE_PIXEL_RATIO > MAX_PART_HEIGHT_PX)) {
    throw new Error('a single export block exceeds the tile canvas limit');
  }

  // 3) 逐块克隆、序列化、解码、拼接。字体策略：优先使用构建期生成的 1.5MB GB2312 子集
  //    （Chrome 对每个分块 SVG 都重新解析内嵌字体，子集把这部分 CPU 降到约 1/3）；
  //    分块文本命中子集未覆盖的生僻字时，该块回退全量内嵌字体（首个全量块由 toSvg 自行
  //    嵌入并提取编码串，后续全量块 skipFonts + 拼接复用，与旧逻辑一致）。
  hooks?.onProgress?.({ done: 0, total: tiles.length });
  const partHeightsPx = tiles.map((tile) => tile.heightCss * CAPTURE_PIXEL_RATIO);
  const widthPx = cardWidth * CAPTURE_PIXEL_RATIO;
  const collector = new PartCanvasCollector(widthPx, partHeightsPx, background);
  const fontPlan = await getExportFontPlan();
  // 字体冷启动竞态修复：正式渲染前先预热（见 warmupEmbeddedFonts）。
  if (fontPlan) {
    await warmupEmbeddedFonts(fontPlan.subsetEncodedStyle);
  }
  // 全量字体 <style> 的「编码后」形态；null = 尚未提取（下一块全量块不带 skipFonts 重试）。
  let fullEncodedFontStyle: string | null = null;
  for (let index = 0; index < tiles.length; index += 1) {
    const tile = tiles[index];
    const wrapper = node.cloneNode(false) as HTMLElement;
    wrapper.style.paddingTop = '0px';
    wrapper.style.paddingBottom = '0px';
    wrapper.style.margin = '0px';
    wrapper.style.height = `${tile.heightCss}px`;
    wrapper.style.overflow = 'hidden';
    for (let i = tile.start; i < tile.end; i += 1) {
      const clone = children[i].cloneNode(true) as HTMLElement;
      clone.style.marginTop = i === tile.start
        ? `${metrics[i].top - tile.topCss}px`
        : `${metrics[i].top - metrics[i - 1].bottom}px`;
      clone.style.marginBottom = i === tile.end - 1
        ? `${tile.topCss + tile.heightCss - metrics[i].bottom}px`
        : '0px';
      wrapper.appendChild(clone);
    }
    host.appendChild(wrapper);
    try {
      const useSubset = fontPlan !== null && !textNeedsFullFont(wrapper.textContent ?? '');
      let tileUrl: string;
      if (useSubset && fontPlan) {
        tileUrl = await toSvg(wrapper, { skipFonts: true });
        tileUrl = spliceEncodedFontStyle(tileUrl, fontPlan.subsetEncodedStyle) ?? tileUrl;
      } else {
        tileUrl = await toSvg(wrapper, fullEncodedFontStyle ? { skipFonts: true } : undefined);
        if (fullEncodedFontStyle === null) {
          const extracted = extractFontStyleElement(decodeSvgDataUrl(tileUrl));
          // 只有确实提取到字体样式才启用后续块的 skipFonts 复用；编码串只算这一次。
          fullEncodedFontStyle = extracted ? encodeURIComponent(extracted) : null;
          if (fullEncodedFontStyle) {
            // 全量字体同样是首次加载，先预热再渲染本块，避免冷启动空白。
            await warmupEmbeddedFonts(fullEncodedFontStyle);
          }
        } else {
          tileUrl = spliceEncodedFontStyle(tileUrl, fullEncodedFontStyle) ?? tileUrl;
        }
      }
      // 首块 data URL 直接交给弹窗做预览头（SVG 可在 <img> 中显示）。
      if (index === 0) {
        hooks?.onFirstSlice?.(tileUrl);
      }
      const image = await loadImage(tileUrl);
      // onload ≠ 首帧就绪（见 waitForSliceImageReady）；无文本内容的块（纯图片/留白）
      // 跳过等待，避免空等超时。
      if ((wrapper.textContent ?? '').trim().length > 0) {
        await waitForSliceImageReady(image);
      }
      await collector.add(image, CAPTURE_PIXEL_RATIO);
      image.src = ''; // 立即释放分块位图
    } finally {
      wrapper.remove();
    }
    hooks?.onProgress?.({ done: index + 1, total: tiles.length });
    await yieldToUi();
  }
  return collector.finish();
}

/**
 * 位图就绪等待 — SVG 图像文档的 onload 不代表首帧已绘制完成：
 * 实测内嵌字体的 SVG（尤其大尺寸/大字体）在 onload 时位图仍是空白，
 * 字体解码与首帧栅格完成后**同一个 img 会异步重绘**（约 100-600ms，逐文档独立，
 * 预热字体缓存只能加速、不能消除）。若在空白窗口期 drawImage，该块整段内容丢失
 * （即线上偶发「长条状坏图」的根因）。这里轮询采样多个水平条带的「局部细节」
 * （相邻像素差异），出现任何细节即视为首帧就绪；超时放行（均匀内容的块本来就
 * 画不错，等不到细节也不过是退回旧行为）。
 */
const SLICE_READY_MAX_ATTEMPTS = 40;
async function waitForSliceImageReady(image: HTMLImageElement): Promise<void> {
  const width = image.naturalWidth;
  const height = image.naturalHeight;
  if (!width || !height) {
    return;
  }
  const probeWidth = Math.min(width, 720);
  const probe = document.createElement('canvas');
  probe.width = probeWidth;
  probe.height = 100;
  const ctx = probe.getContext('2d', { willReadFrequently: true });
  if (!ctx) {
    return;
  }
  const stripYs = [0, Math.max(0, Math.floor(height / 2) - 50), Math.max(0, height - 100)];
  for (let attempt = 0; attempt < SLICE_READY_MAX_ATTEMPTS; attempt += 1) {
    for (const y of stripYs) {
      ctx.drawImage(image, 0, y, width, 100, 0, 0, probeWidth, 100);
      const data = ctx.getImageData(0, 0, probeWidth, 100).data;
      for (let i = 0; i + 12 < data.length; i += 16) {
        // 相邻采样点差异 > 24 → 有文字/边框/图片等细节，首帧已就绪。
        if (Math.abs(data[i] - data[i + 16]) > 24
          || Math.abs(data[i + 1] - data[i + 17]) > 24
          || Math.abs(data[i + 2] - data[i + 18]) > 24) {
          return;
        }
      }
    }
    await new Promise((resolve) => { setTimeout(resolve, 50); });
  }
}

/** Legacy per-slice toPng path — kept as a fallback if the tiled capture ever fails. */
export async function capturePartBlobsLegacy(node: HTMLElement, host: HTMLElement, hooks?: CaptureProgressHooks): Promise<Blob[]> {
  const { toPng } = await import('html-to-image');
  const totalHeight = node.offsetHeight;
  const cardWidth = node.offsetWidth;
  const background = getComputedStyle(node).backgroundColor || '#F6EFE5';
  const sliceHeights = planSliceHeights(totalHeight);
  hooks?.onProgress?.({ done: 0, total: sliceHeights.length });
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
        hooks?.onFirstSlice?.(dataUrl);
      }
      const image = await loadImage(dataUrl);
      await collector.add(image, 1);
      image.src = ''; // 立即释放分片位图
    } finally {
      wrapper.remove();
    }
    hooks?.onProgress?.({ done: index + 1, total: sliceHeights.length });
    await yieldToUi();
  }
  return collector.finish();
}

async function capturePartBlobs(node: HTMLElement, host: HTMLElement, hooks?: CaptureProgressHooks): Promise<Blob[]> {
  try {
    return await capturePartBlobsTiled(node, host, hooks);
  } catch {
    return capturePartBlobsLegacy(node, host, hooks);
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
    const partBlobs = await capturePartBlobs(node, host, {
      onFirstSlice: (firstSliceUrl) => {
        hooks?.onPartialPreview?.({ images: [firstSliceUrl], fileName, partial: true });
      },
      onProgress: hooks?.onProgress,
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
