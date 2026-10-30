// [Input] Original Timeline dates, picture metadata, comment text and card geometry.
// [Output] Shared Web/native date and preview presentation without network or lifecycle ownership.
// [Pos] Helpers moved intact from CollectionsView; original ranges and card dimensions remain.
// [Sync] 2026-10-29: share the existing Timeline presentation with the native destination.
import type {Commentor} from '../engine/EditorEngine';
import {findNormalizedPhrase} from '../utils/textNormalize';
export interface TimelineDay {
  date: string;
  isPast: boolean;
  isFuture: boolean;
  isToday: boolean;
  daysOffset: number;
}

export type TimelinePicture = {
  date: string;
  base64: string;
  full_base64?: string;
  prompt: string;
};

export interface TimelineEntryData {
  picture?: TimelinePicture;
  comments: Commentor[];
}

export interface SessionSummary {
  id: string;
  date_key?: string | null;
  first_line?: string | null;
  name?: string | null;
  created_at?: string;
  updated_at?: string;
}

// @@@ Extract complete sentence containing a phrase
export function extractCompleteSentence(text: string, phrase: string): string {
  const phraseIndex = findNormalizedPhrase(text, phrase);
  if (phraseIndex === -1) {
    return phrase;
  }

  const sentenceEndings = '.!?。！？\n';

  let sentenceStart = 0;
  for (let i = phraseIndex - 1; i >= 0; i--) {
    if (sentenceEndings.includes(text[i])) {
      sentenceStart = i + 1;
      break;
    }
  }

  let sentenceEnd = text.length;
  for (let i = phraseIndex + phrase.length; i < text.length; i++) {
    if (sentenceEndings.includes(text[i])) {
      sentenceEnd = i + 1;
      break;
    }
  }

  return text.slice(sentenceStart, sentenceEnd).trim();
}

// @@@ Helper to get icon emoji
export function getIconForVoice(icon: string): string {
  const iconMap: Record<string, string> = {
    brain: '🧠',
    heart: '❤️',
    question: '❓',
    cloud: '☁️',
    masks: '🎭',
    eye: '👁️',
    fist: '✊',
    lightbulb: '💡',
    shield: '🛡️',
    wind: '💨',
    fire: '🔥',
    compass: '🧭'
  };
  return iconMap[icon] || '💭';
}

// @@@ Helper to get date in local timezone as YYYY-MM-DD
export function getLocalDateString(date?: Date | string): string {
  const d = date ? new Date(date) : new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function formatDate(date: Date | string, locale: string): string {
  return new Date(date).toLocaleDateString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

// @@@ Date helpers for dynamic timeline
export function startOfDay(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

export function addDays(date: Date, delta: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + delta);
  return d;
}

export function makeTimelineDay(date: Date): TimelineDay {
  const today = startOfDay(new Date());
  const day = startOfDay(date);
  const diff = Math.round((day.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  return {
    date: getLocalDateString(day),
    isPast: diff < 0,
    isFuture: diff > 0,
    isToday: diff === 0,
    daysOffset: diff
  };
}

export function buildDayRange(startDate: Date, endDate: Date): TimelineDay[] {
  const days: TimelineDay[] = [];
  const cursor = startOfDay(startDate);
  const end = startOfDay(endDate);
  while (cursor.getTime() <= end.getTime()) {
    days.push(makeTimelineDay(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

// @@@ Extract and truncate beginning of text for timeline preview
export function getTextPreview(text: string, maxLength: number = 60): string {
  if (!text || text.trim().length === 0) return '';

  const cleaned = text.trim().replace(/\s+/g, ' ');
  const sentenceEndings = /[.!?。！？]/;
  const match = cleaned.match(sentenceEndings);

  let preview = '';
  if (match && match.index !== undefined && match.index < maxLength * 1.5) {
    preview = cleaned.substring(0, match.index + 1);
  } else {
    preview = cleaned.substring(0, maxLength);
  }

  if (preview.length > maxLength) {
    preview = preview.substring(0, maxLength).trim() + '...';
  }

  return preview;
}

// @@@ Card height for overlap calculation
export const CARD_HEIGHT = 100;
export const CARD_OVERLAP = 30; // 30% overlap for zigzag effect
export const SLOT_HEIGHT = CARD_HEIGHT - CARD_OVERLAP;
export const INITIAL_PAST_DAYS = 14;
export const CHUNK_SIZE = 14;
export const MAX_PAST_DAYS = 365;
export const LOAD_THRESHOLD_PX = 200;
export const VIRTUAL_BUFFER = 5;

