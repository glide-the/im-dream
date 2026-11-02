// [Input] Persisted Deck/Voice fields used by the existing launcher and preview.
// [Output] Original home visibility, search and preview selections for Web and Native.
// [Pos] Deck presentation model; no reads, mutations, permissions or runtime ownership.
import type {Deck,Voice} from '../../api/voiceApi';

export const isSystemDeckDisplay = (deck: Deck): boolean => (
  deck.is_system || deck.publish_block_reason === 'default_initialized'
);
export const isDeckHomeVisible = (deck: Deck): boolean => (
  isSystemDeckDisplay(deck) || (deck.enabled
    && deck.deck_version_capability === true
    && typeof deck.deck_version === 'number'
    && deck.deck_version > 0
    && deck.deck_version_dirty === false
    && deck.deck_version_status === 'published')
);
export function matchesDeckHomeQuery(deck:Deck,query:string):boolean {
  const normalizedQuery=query.trim().toLocaleLowerCase();
  return normalizedQuery.length===0 || [deck.name,deck.name_zh,deck.name_en,
    deck.description,deck.description_zh,deck.description_en]
    .some(value=>value?.toLocaleLowerCase().includes(normalizedQuery));
}
export function deckPreviewVoices(deck:Deck) {
  const voices=deck.voices || [];
  return {voices,trialVoice:voices.find(voice=>voice.enabled) || voices[0] || null,examples:voices.slice(0,3)};
}
export function deckExamplePrompt(deck:Deck,voice:Voice,fallback:string):string {
  return voice.system_prompt?.split('\n').find(line=>line.trim().length>0)?.trim() || deck.description || fallback;
}
