// [Input] Original configured Font Awesome icons and shared Deck color metadata.
// [Output] Existing Web icon map and COLORS export with unchanged values.
// [Pos] Web Deck visual entry; native uses the same pure color metadata and projected paths.
// [Sync] 2026-10-29: re-export pure color metadata for native forms; DOM icons remain unchanged.
import {
  FaBrain, FaHeart, FaQuestion, FaCloud, FaTheaterMasks, FaEye,
  FaFistRaised, FaLightbulb, FaShieldAlt, FaWind, FaFire, FaCompass
} from 'react-icons/fa';

export {DECK_COLORS as COLORS} from '../constants/deck.ts';

export const iconMap = {
  brain: FaBrain,
  heart: FaHeart,
  question: FaQuestion,
  cloud: FaCloud,
  masks: FaTheaterMasks,
  eye: FaEye,
  fist: FaFistRaised,
  lightbulb: FaLightbulb,
  shield: FaShieldAlt,
  wind: FaWind,
  fire: FaFire,
  compass: FaCompass,
};
