// [Input] Existing chat namespace translations.
// [Output] The original three quick actions and exact prompt keys for Web/native.
// [Pos] Portable presentation model extracted unchanged from ChatView.
import type {TFunction} from 'i18next';
import type {QuickActionStripItem} from './QuickActionStrip.types';
export function buildDefaultLandingQuickActions(t: TFunction): QuickActionStripItem[] {
  return [
    {id:'generate-image',label:t('chat.quickActions.generateImage.label'),prompt:t('chat.quickActions.generateImage.prompt'),icon:'image',description:t('chat.quickActions.generateImage.description')},
    {id:'write-edit',label:t('chat.quickActions.writeEdit.label'),prompt:t('chat.quickActions.writeEdit.prompt'),icon:'edit',description:t('chat.quickActions.writeEdit.description')},
    {id:'find-info',label:t('chat.quickActions.findInfo.label'),prompt:t('chat.quickActions.findInfo.prompt'),icon:'search',description:t('chat.quickActions.findInfo.description')},
  ];
}
