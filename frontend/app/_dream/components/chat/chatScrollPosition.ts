// [Input] Measured message content, viewport and vertical offset from the current renderer.
// [Output] Original ChatPanel bottom proximity and jump-action visibility.
// [Pos] Shared numeric scroll policy; Web DOM and native ScrollView own measurement and movement.
export const CHAT_BOTTOM_PROXIMITY_PX = 120;
export function chatScrollPosition(contentHeight:number,offset:number,viewportHeight:number) {
  const isScrollable=contentHeight-viewportHeight>CHAT_BOTTOM_PROXIMITY_PX;
  const isNearBottom=contentHeight-offset-viewportHeight<CHAT_BOTTOM_PROXIMITY_PX;
  return {isNearBottom,showScrollToBottom:isScrollable&&!isNearBottom};
}
