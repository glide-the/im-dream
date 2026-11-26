// [Sync] 2026-11-13: share the five-item More order on narrow Web and native.
// [Input] Shared More entries, platform labels/icons/colors and existing navigation/theme callbacks.
// [Output] The same journal cards, preference rows, guidance and theme feedback on native and narrow Web.
// [Pos] Shared RN/RNW presentation; callers own headers, scrolling, routes and persisted preferences.
// [Sync] 2026-11-01: extract the current native card layout for both platform callers.
import {useState, type ComponentType, type ReactNode} from 'react';
import {Pressable, StyleSheet, View, type TextProps} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {InkColors} from '../../../../../src/components/inkColors';
import {MORE_NAVIGATION_ITEMS, type MoreNavigationDestination} from './moreNavigation';

export type MoreNavigationItem = (typeof MORE_NAVIGATION_ITEMS)[number];
export type MoreLabelProps = Omit<TextProps, 'children'> & {children: string};
type Props = {
  colors: Pick<InkColors, 'color-bg-app' | 'color-bg-paper' | 'color-bg-hover' | 'color-border-paper' | 'color-text-primary' | 'color-text-secondary' | 'color-state-error'>;
  Label: ComponentType<MoreLabelProps>;
  renderIcon: (id: MoreNavigationItem['id'], color: string) => ReactNode;
  chevron: ReactNode;
  appearance: string;
  nextAppearance: string;
  onNavigate: (destination: MoreNavigationDestination) => void;
  onToggleTheme: () => void;
};

export default function MoreNavigationContent({colors: c, Label, renderIcon, chevron, appearance, nextAppearance, onNavigate, onToggleTheme}: Props) {
  const {t} = useTranslation();
  const [themeError, setThemeError] = useState(false);
  function changeTheme() {
    setThemeError(false);
    try { onToggleTheme(); } catch { setThemeError(true); }
  }
  function entry(item: MoreNavigationItem, layout: 'row' | 'tile') {
    return <Pressable key={item.id} accessibilityRole="button" accessibilityLabel={t(item.labelKey)} accessibilityHint={item.id === 'theme' ? t('morePage.themeAction', {appearance, next: nextAppearance}) : t(`morePage.guidance.${item.id}`)} onPress={() => item.id === 'theme' ? changeTheme() : onNavigate(item.id)} style={({pressed}) => [styles.entry, layout === 'tile' ? styles.tile : styles.row, {backgroundColor: pressed ? c['color-bg-hover'] : c['color-bg-paper'], borderColor: c['color-border-paper']}]}>
      <View style={[styles.icon, {backgroundColor: c['color-bg-app']}]}>{renderIcon(item.id, c['color-text-primary'])}</View>
      <View style={styles.copy}>
        <Label style={[styles.label, {color: c['color-text-primary']}]}>{t(item.labelKey)}</Label>
        <Label style={[styles.description, {color: c['color-text-secondary']}]}>{item.id === 'theme' ? t('morePage.currentTheme', {appearance}) : t(`morePage.guidance.${item.id}`)}</Label>
      </View>
      {layout === 'row' ? chevron : null}
    </Pressable>;
  }
  return <View style={styles.content}>
    <Label style={[styles.intro, {color: c['color-text-secondary']}]}>{t('morePage.intro')}</Label>
    <View style={styles.section}>
      <Label accessibilityRole="header" style={[styles.sectionTitle, {color: c['color-text-secondary']}]}>{t('morePage.journal')}</Label>
      {MORE_NAVIGATION_ITEMS.filter(item => item.id === 'writing').map(item => entry(item, 'row'))}
      <View style={styles.tiles}>{MORE_NAVIGATION_ITEMS.filter(item => item.id === 'timeline' || item.id === 'analysis').map(item => entry(item, 'tile'))}</View>
    </View>
    <View style={styles.section}>
      <Label accessibilityRole="header" style={[styles.sectionTitle, {color: c['color-text-secondary']}]}>{t('morePage.preferences')}</Label>
      {themeError ? <Label accessibilityRole="alert" style={[styles.description, {color: c['color-state-error']}]}>{t('settings.workspace.preferences.localSaveFailed')}</Label> : null}
      {MORE_NAVIGATION_ITEMS.filter(item => item.id === 'theme' || item.id === 'settings').map(item => entry(item, 'row'))}
    </View>
  </View>;
}

const styles = StyleSheet.create({
  content: {gap: 26, minWidth: 0},
  intro: {fontSize: 14, lineHeight: 22},
  section: {gap: 12}, sectionTitle: {fontSize: 14},
  entry: {minWidth: 0, borderWidth: StyleSheet.hairlineWidth, borderRadius: 18, padding: 16, gap: 12},
  row: {flexDirection: 'row', alignItems: 'center', minHeight: 92},
  tiles: {flexDirection: 'row', gap: 12}, tile: {flex: 1, alignItems: 'flex-start', minHeight: 152},
  icon: {width: 44, height: 44, borderRadius: 13, alignItems: 'center', justifyContent: 'center'},
  copy: {flex: 1, minWidth: 0, gap: 6}, label: {fontSize: 19},
  description: {fontSize: 13, lineHeight: 20, flexShrink: 1},
});
