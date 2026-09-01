/**
 * EditorEngine.ts
 * Clean editor engine based on trace-based energy model
 * [Sync] 2026-05-30: fix insertWidgetAfterLine to always ensure a text cell exists after any widget,
 *   even when inserting between two widgets (was only guarding the last-cell case).
 * [Sync] 2026-05-30: fix deleteCell to guarantee last cell is always text after widget removal.
 * [Sync] 2026-06-14: add loadState source markers so remote Agent-write reloads
 *   can skip the next automatic save cycle.
 * [Sync] 2026-08-31: retire automatic PolyCLI voice analysis on text edits;
 *   Writing inspiration and explicit Thread Chat own model interaction.
 * [Sync] 2026-09-01: add persistent WritingSuggestionCell sequencing and a
 *   Session-owned Writing Thread while keeping all prose metrics TextCell-only.
 */

// @@@ Core data model - cells + commentors + tasks + WeightPath
export interface EditorState {
  cells: Cell[];
  commentors: Commentor[];
  tasks: Task[];
  weightPath: WeightEntry[];
  overlappedPhrases: string[];  // @@@ Phrases rejected due to overlap (feedback to backend)
  notFoundPhrases: string[];  // @@@ Phrases LLM suggested that were not found in text
  id: string;
  /** Product-level Claude Agent Thread shared by every suggestion in this Session. */
  writingThreadId?: string;
  selectedState?: string | null;  // @@@ Emotional state for this session (stored per-session)
  createdAt?: string;  // @@@ ISO timestamp when session was created
}

export type Cell = TextCell | WidgetCell | WritingSuggestionCell;

export interface TextCell {
  id: string;
  type: 'text';
  content: string;  // Plain text content
}

export interface WidgetCell {
  id: string;
  type: 'widget';
  widgetType: 'chat' | 'greeting' | 'other';
  data: unknown;  // Widget-specific data; consumers narrow by widgetType before use
}

export type WritingSuggestionStatus = 'idle' | 'streaming' | 'completed' | 'failed';

export interface WritingSuggestionError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface WritingSuggestionAnchor {
  textCellId: string;
  textSnapshot: string;
}

export interface WritingSuggestionCell {
  id: string;
  type: 'writing-suggestion';
  content: string;
  status: WritingSuggestionStatus;
  anchor: WritingSuggestionAnchor;
  createdAt: string;
  updatedAt: string;
  error?: WritingSuggestionError;
  /** Transient generation identity persisted only to reject stale responses safely. */
  requestId?: string;
  /** Completed content retained while Refresh waits for its first replacement delta. */
  previousContent?: string;
}

export interface ChatMessage {
  role: 'assistant' | 'user';
  content: string;
  timestamp: number;
}

export interface Commentor {
  id: string;
  phrase: string;       // Highlighted phrase
  comment: string;      // The comment
  voiceId?: string;     // NEW: Voice ID for voiceConfigs lookup (e.g., "mirror")
  voice: string;        // Voice display name (e.g., "照镜者") - immutable snapshot
  icon: string;         // Icon identifier
  color: string;        // Color identifier
  appliedAt?: number;   // Timestamp when applied (if applied)
  computedAt: number;   // Timestamp when computed
  textSnapshot: string; // Text at computation time
  chatHistory?: ChatMessage[];  // Conversation with this comment
  feedback?: 'star' | 'kill';   // User feedback
}

export interface Task {
  id: string;
  type: 'searching' | 'thinking' | 'other';
  message: string;
  startedAt: number;
  completedAt?: number;
}

export interface WeightEntry {
  timestamp: number;
  text: string;
  weight: number;
  delta: number;  // max(0, weight - prevWeight)
  energy: number; // Accumulated energy at this point
}

export type EditorStateLoadSource = 'local' | 'remote';

// @@@ Weight function implementation
export function computeWeight(text: string): number {
  let weight = 0;

  for (const char of text) {
    // Sentence boundaries
    if (/[.!?。！？\n]/.test(char)) {
      weight += 4;
    }
    // Chinese comma (ignored)
    else if (char === '，') {
      // Skip: weight += 0
    }
    // CJK characters
    else if (/[\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]/.test(char)) {
      weight += 2;
    }
    // Default
    else {
      weight += 1;
    }
  }

  return weight;
}

// @@@ Main engine class
export class EditorEngine {
  private state: EditorState;
  private onStateChange?: (state: EditorState) => void;
  private blankResetSubscribers: Set<() => void> = new Set();
  private lastLoadSource: EditorStateLoadSource = 'local';

  constructor(sessionId: string) {
    this.state = {
      cells: [{ id: generateId(), type: 'text', content: '' }],
      commentors: [],
      tasks: [],
      weightPath: [],
      overlappedPhrases: [],
      notFoundPhrases: [],
      id: sessionId
    };
  }

  onBlankReset(callback: () => void) {
    this.blankResetSubscribers.add(callback);
    return () => this.blankResetSubscribers.delete(callback);
  }

  private notifyBlankReset() {
    this.blankResetSubscribers.forEach(cb => {
      try {
        cb();
      } catch (error) {
        console.error('Blank reset subscriber failed', error);
      }
    });
  }

  // @@@ Update voice configurations from settings
  // No-op: Backend now loads voice configs from database, not from frontend
  setVoiceConfigs(configs: Record<string, unknown>) {
    void configs;
    // Kept for backward compatibility, but does nothing
  }

  // @@@ Update a specific text cell by ID
  updateTextCell(cellId: string, newText: string) {
    const cell = this.state.cells.find(c => c.id === cellId);
    if (!cell || cell.type !== 'text') return;

    (cell as TextCell).content = newText;
    this.applyTextUpdate();
  }

  // @@@ Apply local weight calculation; text edits never start model requests
  private applyTextUpdate() {
    const combinedText = this.getCombinedText();

    // @@@ Auto-reset when editor is cleared (no widgets + empty text cells)
    if (this.shouldResetEditorState(combinedText)) {
      this.resetEditorToBlank();
      return;
    }

    // Compute new weight entry
    const weight = computeWeight(combinedText);
    const lastEntry = this.state.weightPath[this.state.weightPath.length - 1];
    const prevWeight = lastEntry?.weight || 0;
    const delta = Math.max(0, weight - prevWeight);
    const prevEnergy = lastEntry?.energy || 0;
    const energy = prevEnergy + delta;

    // Add to weight path
    this.state.weightPath.push({
      timestamp: Date.now(),
      text: combinedText,
      weight,
      delta,
      energy
    });

    this.notifyChange();
  }

  // @@@ Get combined text from all text cells
  private getCombinedText(): string {
    return this.state.cells
      .filter(c => c.type === 'text')
      .map(c => (c as TextCell).content)
      .join('');
  }

  // @@@ Detect when all text cells are empty and no user-authored widgets remain.
  // Suggestions are derived content, so clearing the prose clears them and the
  // Session-owned Writing Thread association together.
  private shouldResetEditorState(combinedText: string): boolean {
    const hasUserWidgetCells = this.state.cells.some(cell => cell.type === 'widget');
    if (hasUserWidgetCells) {
      return false;
    }

    return combinedText.trim().length === 0;
  }

  // @@@ Restore editor to pristine state while starting a fresh session
  private resetEditorToBlank() {
    const { selectedState, createdAt, id } = this.state;
    const preservedTimestamp = createdAt ?? new Date().toISOString();
    const preservedId = id || (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString());

    this.state = {
      cells: [{ id: generateId(), type: 'text', content: '' }],
      commentors: [],
      tasks: [],
      weightPath: [],
      overlappedPhrases: [],
      notFoundPhrases: [],
      id: preservedId,
      selectedState,
      createdAt: preservedTimestamp
    };

    this.notifyChange();
    this.notifyBlankReset();
  }

  // @@@ Merge consecutive text cells to prevent text-text pattern
  private mergeConsecutiveTextCells() {
    const merged: Cell[] = [];
    let i = 0;

    while (i < this.state.cells.length) {
      const cell = this.state.cells[i];

      if (cell.type === 'text') {
        // Collect all consecutive text cells
        let combinedContent = (cell as TextCell).content;
        let j = i + 1;
        while (j < this.state.cells.length && this.state.cells[j].type === 'text') {
          combinedContent += (this.state.cells[j] as TextCell).content;
          j++;
        }

        // Add merged text cell
        merged.push({
          id: cell.id, // Keep first cell's ID
          type: 'text',
          content: combinedContent
        });

        i = j; // Skip all merged cells
      } else {
        merged.push(cell);
        i++;
      }
    }

    this.state.cells = merged;
  }

  // @@@ Insert widget at cursor, removing @ character if present
  insertWidgetAtCursor(cellId: string, cursorPosition: number, widgetType: WidgetCell['widgetType'], data: unknown) {
    const cell = this.state.cells.find(c => c.id === cellId);
    if (!cell || cell.type !== 'text') return;

    const text = (cell as TextCell).content;

    // Remove @ character if it's right before cursor
    const atPosition = cursorPosition - 1;
    if (atPosition >= 0 && text[atPosition] === '@') {
      // Check if @ is the only character on its line
      const lineStart = text.lastIndexOf('\n', atPosition - 1) + 1;
      const lineEnd = text.indexOf('\n', cursorPosition);
      const lineEndPos = lineEnd === -1 ? text.length : lineEnd;
      const lineContent = text.substring(lineStart, lineEndPos);
      const isOnlyCharOnLine = lineContent.trim() === '@';

      // Remove the @ and optionally the newline
      let newText: string;
      if (isOnlyCharOnLine) {
        // @ is alone on its line - remove the newline before it (if exists)
        const hasNewlineBefore = atPosition > 0 && text[atPosition - 1] === '\n';
        if (hasNewlineBefore) {
          // Remove the newline before @ and the @
          newText = text.substring(0, atPosition - 1) + text.substring(cursorPosition);
        } else {
          // Just remove @
          newText = text.substring(0, atPosition) + text.substring(cursorPosition);
        }
      } else {
        // @ is not alone - just remove @
        newText = text.substring(0, atPosition) + text.substring(cursorPosition);
      }
      (cell as TextCell).content = newText;

      // Insert widget at the @ position (adjust if we removed newline before)
      const insertPos = isOnlyCharOnLine && atPosition > 0 && text[atPosition - 1] === '\n'
        ? atPosition - 1
        : atPosition;
      this.insertWidgetAfterLine(cellId, insertPos, widgetType, data);
    } else {
      // No @ found, just insert widget at cursor position
      this.insertWidgetAfterLine(cellId, cursorPosition, widgetType, data);
    }
  }

  // @@@ Add a widget cell after a specific text position in a specific cell
  insertWidgetAfterLine(cellId: string, cursorPosition: number, widgetType: WidgetCell['widgetType'], data: unknown) {
    // Find the specific cell and its index
    const cellIndex = this.state.cells.findIndex(c => c.id === cellId);
    if (cellIndex === -1) return;

    const cell = this.state.cells[cellIndex];
    if (cell.type !== 'text') return;

    const text = (cell as TextCell).content;

    // Find the line end after cursor position
    let lineEndPos = text.indexOf('\n', cursorPosition);
    if (lineEndPos === -1) {
      lineEndPos = text.length;
    } else {
      lineEndPos += 1; // Include the newline
    }

    // Split text into before and after
    const beforeText = text.substring(0, lineEndPos);
    const afterText = text.substring(lineEndPos);

    // Create replacement cells for this position
    const replacementCells: Cell[] = [];

    // Text before widget (only if non-empty)
    if (beforeText.length > 0) {
      replacementCells.push({
        id: generateId(),
        type: 'text',
        content: beforeText
      });
    }

    // Widget cell
    replacementCells.push({
      id: generateId(),
      type: 'widget',
      widgetType,
      data
    });

    // Text after widget: always add when there's afterText, or when the next cell is not
    // already a text cell (covers both end-of-list and widget-follows-widget cases).
    const hasNextTextCell = cellIndex + 1 < this.state.cells.length &&
      this.state.cells[cellIndex + 1].type === 'text';

    if (afterText.length > 0 || !hasNextTextCell) {
      replacementCells.push({
        id: generateId(),
        type: 'text',
        content: afterText
      });
    }

    // Replace the cell at cellIndex with the new cells, keeping all other cells intact
    this.state.cells.splice(cellIndex, 1, ...replacementCells);
    this.mergeConsecutiveTextCells(); // Ensure no consecutive text cells
    this.notifyChange();
  }

  // @@@ Add a widget cell at the end
  addWidgetCell(widgetType: WidgetCell['widgetType'], data: unknown) {
    const widget: WidgetCell = {
      id: generateId(),
      type: 'widget',
      widgetType,
      data
    };
    this.state.cells.push(widget);
    this.notifyChange();
  }

  // @@@ Update widget data (for chat messages)
  updateWidgetData(widgetId: string, data: unknown) {
    const widget = this.state.cells.find(c => c.type === 'widget' && c.id === widgetId);
    if (widget && widget.type === 'widget') {
      widget.data = data;
      this.notifyChange();
    }
  }

  hasWritingSuggestionForTextCell(textCellId: string): boolean {
    return this.state.cells.some(
      (cell) => cell.type === 'writing-suggestion' && cell.anchor.textCellId === textCellId,
    );
  }

  getWritingSuggestionCell(cellId: string): WritingSuggestionCell | undefined {
    const cell = this.state.cells.find((candidate) => candidate.id === cellId);
    return cell?.type === 'writing-suggestion' ? cell : undefined;
  }

  insertWritingSuggestionAfterTextCell(
    textCellId: string,
    textSnapshot: string,
    requestId: string,
  ): WritingSuggestionCell | null {
    const cellIndex = this.state.cells.findIndex(
      (cell) => cell.id === textCellId && cell.type === 'text',
    );
    if (cellIndex < 0 || textSnapshot.trim().length === 0) return null;
    if (this.hasWritingSuggestionForTextCell(textCellId)) return null;

    const timestamp = new Date().toISOString();
    const suggestion: WritingSuggestionCell = {
      id: generateId(),
      type: 'writing-suggestion',
      content: '',
      status: 'streaming',
      anchor: { textCellId, textSnapshot },
      createdAt: timestamp,
      updatedAt: timestamp,
      requestId,
    };

    this.state.cells.splice(cellIndex + 1, 0, suggestion);
    const cellAfterSuggestion = this.state.cells[cellIndex + 2];
    if (!cellAfterSuggestion || cellAfterSuggestion.type !== 'text') {
      this.state.cells.splice(cellIndex + 2, 0, {
        id: generateId(),
        type: 'text',
        content: '',
      });
    }
    this.notifyChange();
    return suggestion;
  }

  beginWritingSuggestionRetry(cellId: string, requestId: string): WritingSuggestionCell | null {
    const cell = this.getWritingSuggestionCell(cellId);
    if (!cell || cell.status === 'streaming') return null;

    cell.previousContent = cell.content || cell.previousContent;
    cell.content = '';
    cell.status = 'streaming';
    cell.requestId = requestId;
    cell.error = undefined;
    cell.updatedAt = new Date().toISOString();
    this.notifyChange();
    return cell;
  }

  isWritingSuggestionRequestCurrent(
    sessionId: string,
    cellId: string,
    requestId: string,
    threadId?: string,
  ): boolean {
    if (this.state.id !== sessionId) return false;
    if (threadId && this.state.writingThreadId !== threadId) return false;
    return this.getWritingSuggestionCell(cellId)?.requestId === requestId;
  }

  appendWritingSuggestionDelta(
    sessionId: string,
    cellId: string,
    requestId: string,
    threadId: string,
    delta: string,
  ): boolean {
    if (!delta || !this.isWritingSuggestionRequestCurrent(sessionId, cellId, requestId, threadId)) {
      return false;
    }
    const cell = this.getWritingSuggestionCell(cellId);
    if (!cell) return false;
    cell.content += delta;
    cell.updatedAt = new Date().toISOString();
    this.notifyChange();
    return true;
  }

  completeWritingSuggestion(
    sessionId: string,
    cellId: string,
    requestId: string,
    threadId: string,
  ): boolean {
    if (!this.isWritingSuggestionRequestCurrent(sessionId, cellId, requestId, threadId)) {
      return false;
    }
    const cell = this.getWritingSuggestionCell(cellId);
    if (!cell) return false;
    cell.status = 'completed';
    cell.requestId = undefined;
    cell.previousContent = undefined;
    cell.error = undefined;
    cell.updatedAt = new Date().toISOString();
    this.notifyChange();
    return true;
  }

  failWritingSuggestion(
    sessionId: string,
    cellId: string,
    requestId: string,
    error: WritingSuggestionError,
    threadId?: string,
  ): boolean {
    if (!this.isWritingSuggestionRequestCurrent(sessionId, cellId, requestId, threadId)) {
      return false;
    }
    const cell = this.getWritingSuggestionCell(cellId);
    if (!cell) return false;
    if (cell.previousContent) {
      cell.content = cell.previousContent;
    }
    cell.status = 'failed';
    cell.requestId = undefined;
    cell.previousContent = undefined;
    cell.error = error;
    cell.updatedAt = new Date().toISOString();
    this.notifyChange();
    return true;
  }

  setWritingThreadId(sessionId: string, threadId: string): boolean {
    if (this.state.id !== sessionId || !threadId.trim()) return false;
    if (this.state.writingThreadId && this.state.writingThreadId !== threadId) return false;
    this.state.writingThreadId = threadId;
    this.notifyChange();
    return true;
  }

  // @@@ Subscribe to state changes
  subscribe(callback: (state: EditorState) => void) {
    this.onStateChange = callback;
  }

  private notifyChange() {
    this.onStateChange?.(this.state);
  }

  // @@@ Get current state
  getState(): EditorState {
    return this.state;
  }

  // @@@ Load state from storage
  loadState(state: EditorState, options: { source?: EditorStateLoadSource } = {}) {
    if (!state.id) {
      throw new Error('EditorState.id is required when loading');
    }
    this.lastLoadSource = options.source ?? 'local';
    const restoredAt = new Date().toISOString();
    const cells = Array.isArray(state.cells) ? state.cells.map((cell) => {
      if (cell.type !== 'writing-suggestion') return cell;
      const restored: WritingSuggestionCell = {
        ...cell,
        content: typeof cell.content === 'string' ? cell.content : '',
        status: cell.status === 'streaming' ? 'failed' : cell.status,
        anchor: {
          textCellId: cell.anchor?.textCellId ?? '',
          textSnapshot: cell.anchor?.textSnapshot ?? '',
        },
        createdAt: cell.createdAt || restoredAt,
        updatedAt: cell.status === 'streaming' ? restoredAt : (cell.updatedAt || restoredAt),
        requestId: undefined,
        previousContent: undefined,
        ...(cell.status === 'streaming'
          ? {
              error: {
                code: 'WRITING_SSE_INTERRUPTED',
                message: 'The suggestion stream was interrupted.',
                retryable: true,
              },
            }
          : {}),
      };
      return restored;
    }) : [];
    this.state = {
      ...state,
      cells: cells.length > 0 ? cells : [{ id: generateId(), type: 'text', content: '' }],
      ...(typeof state.writingThreadId === 'string' && state.writingThreadId.trim()
        ? { writingThreadId: state.writingThreadId }
        : { writingThreadId: undefined }),
    };
    // @@@ Ensure overlappedPhrases field exists (migration for old state)
    if (!this.state.overlappedPhrases) {
      this.state.overlappedPhrases = [];
    }
    if (!this.state.notFoundPhrases) {
      this.state.notFoundPhrases = [];
    }
    this.notifyChange();
  }

  consumeLastLoadSource(): EditorStateLoadSource {
    const source = this.lastLoadSource;
    this.lastLoadSource = 'local';
    return source;
  }

  // @@@ Set current entry ID (for calendar overwrite tracking)
  setCurrentEntryId(entryId: string | undefined) {
    if (!entryId) return;
    this.state.id = entryId;
    this.notifyChange();
  }

  // @@@ Delete a cell by ID
  deleteCell(cellId: string) {
    const cellIndex = this.state.cells.findIndex(c => c.id === cellId);
    if (cellIndex === -1) return;

    this.state.cells.splice(cellIndex, 1);

    // Ensure we always have at least one text cell
    if (this.state.cells.length === 0) {
      this.state.cells.push({ id: generateId(), type: 'text', content: '' });
    }

    // Merge consecutive text cells (important when deleting a widget between text cells)
    this.mergeConsecutiveTextCells();

    // Ensure the last cell is always a text cell so the user can continue writing
    const lastCell = this.state.cells[this.state.cells.length - 1];
    if (lastCell && lastCell.type !== 'text') {
      this.state.cells.push({ id: generateId(), type: 'text', content: '' });
    }

    this.notifyChange();
  }

  // @@@ Add a message to a comment's chat history
  addCommentChatMessage(commentId: string, role: 'assistant' | 'user', content: string) {
    const comment = this.state.commentors.find(c => c.id === commentId);
    if (!comment) return;

    if (!comment.chatHistory) {
      // Initialize with the original comment as first assistant message
      comment.chatHistory = [{
        role: 'assistant',
        content: comment.comment,
        timestamp: comment.computedAt
      }];
    }

    comment.chatHistory.push({
      role,
      content,
      timestamp: Date.now()
    });

    this.notifyChange();
  }

  // @@@ Set feedback for a comment
  setCommentFeedback(commentId: string, feedback: 'star' | 'kill' | undefined) {
    const comment = this.state.commentors.find(c => c.id === commentId);
    if (!comment) return;

    comment.feedback = feedback;
    this.notifyChange();
  }

  // @@@ Get comment by ID
  getComment(commentId: string): Commentor | undefined {
    return this.state.commentors.find(c => c.id === commentId);
  }
}

// @@@ Helper to generate IDs
function generateId(): string {
  return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
