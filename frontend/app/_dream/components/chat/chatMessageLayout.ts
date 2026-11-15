// [Input] Existing ChatMessageList stack and message-group geometry.
// [Output] The same width, spacing and wrapping in Chat, public snapshots and image previews.
// [Pos] Presentation-only shared styles; message state and actions retain their owners.
import type {CSSProperties} from 'react';

export const CHAT_MESSAGE_LIST_STYLE: CSSProperties = {
  width: '100%',
  minWidth: 0,
  boxSizing: 'border-box',
  display: 'flex',
  flexDirection: 'column',
  gap: '1.25rem',
  overflowWrap: 'anywhere',
};

export const CHAT_MESSAGE_GROUP_STYLE: CSSProperties = {
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: '1rem',
};
