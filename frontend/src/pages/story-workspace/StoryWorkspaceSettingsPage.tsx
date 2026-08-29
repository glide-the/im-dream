// [Input] Settings route section, existing resource/plugin managers, and the Work-owned Deck management surface.
// [Output] Existing Settings shell with one Work category plus single-heading Notion and Claude MCP detail surfaces.
// [Pos] Canonical Story Workspace Settings page and Work workbench route surface.
// [Sync] 2026-08-17: localize the complete Settings shell and Work surface; render one locale at a time.
// [Sync] 2026-08-20: host the actor-owned Claude MCP detail projection beside the Notion detail page.
// [Sync] 2026-08-29: let the Notion detail own its sole h1 and long-page hierarchy instead of wrapping it in a duplicate SettingsSection header.
/* eslint-disable react-refresh/only-export-components -- route metadata helpers intentionally share this page module. */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { FaArrowLeft, FaBriefcase, FaCog, FaCoins, FaDatabase, FaInfoCircle, FaPuzzlePiece, FaRobot, FaSearch } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import AboutView from '../../components/AboutView';
import { IconMonitor, IconMoon, IconSun } from '../../components/chat/Icons';
import ClaudeMcpServerDetailPage from '../../components/claude-mcp/ClaudeMcpServerDetailPage';
import ClaudePluginAdminPage from '../../components/claude-plugin-admin/ClaudePluginAdminPage';
import ConnectorNotionDetailPage from '../../components/dashboard/ConnectorNotionDetailPage';
import ConnectorSettingsSection from '../../components/dashboard/ConnectorSettingsSection';
import ModelConfigSection from '../../components/dashboard/ModelConfigSection';
import { getAuthToken } from '../../contexts/AuthContext';
import { API_BASE } from '../../lib/apiBase';
import type { StoryWorkspaceStaticRoute } from '../../router/storyWorkspacePath';
import { getThemeMode, onThemeChange, setThemeMode, type ThemeMode } from '../../utils/theme';
import { StoryWorkspaceSubscriptionPage } from './StoryWorkspaceSubscriptionPage';
import './StoryWorkspaceSettingsPage.css';

export type StoryWorkspaceSettingsSection =
  | 'settings'
  | 'settings-work'
  | 'settings-resources'
  | 'settings-plugins'
  | 'settings-model'
  | 'settings-about'
  | 'settings-subscription';

export interface StoryWorkspaceSettingsPageProps {
  activeSection: StoryWorkspaceSettingsSection;
  isMobile?: boolean;
  currentLanguage: string;
  languageCodes: readonly string[];
  onLanguageChange: (code: string) => void;
  showEnergyBar: boolean;
  onEnergyBarChange: () => void;
  connectorSettingsFocusNonce?: number;
  showNotionConnectorDetail?: boolean;
  claudeMcpDetailServerName?: string | null;
  onOpenNotionDetail?: () => void;
  onCloseNotionDetail?: () => void;
  onOpenClaudeMcpDetail?: (serverName: string) => void;
  onCloseClaudeMcpDetail?: () => void;
  onNavigate: (path: string) => void;
  workDeckContent?: ReactNode;
}

export type StoryWorkspaceWorkTab = 'deck' | 'resources' | 'plugins';

export function storyWorkspaceWorkTabForSection(
  activeSection: StoryWorkspaceSettingsSection,
  search = typeof window === 'undefined' ? '' : window.location.search,
): StoryWorkspaceWorkTab {
  if (activeSection === 'settings-resources') return 'resources';
  if (activeSection === 'settings-plugins') return 'plugins';
  const candidate = new URLSearchParams(search).get('tab');
  return candidate === 'resources' || candidate === 'plugins' ? candidate : 'deck';
}

interface SettingsNavItem {
  id: StoryWorkspaceSettingsSection;
  label: string;
  icon: typeof FaCog;
  path: string;
}

const THEME_OPTIONS: { mode: ThemeMode; labelKey: string; Icon: typeof IconSun }[] = [
  { mode: 'light', labelKey: 'settings.workspace.theme.options.light', Icon: IconSun },
  { mode: 'system', labelKey: 'settings.workspace.theme.options.system', Icon: IconMonitor },
  { mode: 'dark', labelKey: 'settings.workspace.theme.options.dark', Icon: IconMoon },
];

function AppearanceThemeSetting() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<ThemeMode>(() => getThemeMode());

  useEffect(() => {
    const unsubscribe = onThemeChange((_resolved, mode) => setTheme(mode));
    return () => { unsubscribe(); };
  }, []);

  const handleThemeChange = useCallback((mode: ThemeMode) => {
    setThemeMode(mode);
    void fetch(`${API_BASE}/api/system-config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getAuthToken()}` },
      body: JSON.stringify({ theme: mode }),
    }).catch(() => undefined);
  }, []);

  return (
    <div className="story-workspace-settings__theme-field">
      <strong id="story-workspace-theme-label">{t('settings.workspace.theme.label')}</strong>
      <p>{t('settings.workspace.theme.description')}</p>
      <div aria-labelledby="story-workspace-theme-label" className="story-workspace-settings__theme-options" role="group">
        {THEME_OPTIONS.map(({ mode, labelKey, Icon }) => {
          const isActive = theme === mode;
          return (
            <button
              aria-pressed={isActive}
              className={`story-workspace-settings__theme-button${isActive ? ' is-active' : ''}`}
              key={mode}
              onClick={() => handleThemeChange(mode)}
              type="button"
            >
              <Icon />
              <span>{t(labelKey)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SettingsSection({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={`${id}-title`} className="story-workspace-settings__section" id={id}>
      <header className="story-workspace-settings__section-header">
        <h2 id={`${id}-title`}>{title}</h2>
        {description ? <p>{description}</p> : null}
      </header>
      {children}
    </section>
  );
}

export function StoryWorkspaceSettingsPage({
  activeSection,
  isMobile = false,
  currentLanguage,
  languageCodes,
  onLanguageChange,
  showEnergyBar,
  onEnergyBarChange,
  connectorSettingsFocusNonce = 0,
  showNotionConnectorDetail = false,
  claudeMcpDetailServerName = null,
  onOpenNotionDetail,
  onCloseNotionDetail,
  onOpenClaudeMcpDetail,
  onCloseClaudeMcpDetail,
  onNavigate,
  workDeckContent = null,
}: StoryWorkspaceSettingsPageProps) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const navItems = useMemo<SettingsNavItem[]>(() => [
    { id: 'settings', label: t('settings.workspace.navigation.general'), icon: FaCog, path: '/story-workspace/settings' },
    { id: 'settings-subscription', label: t('settings.workspace.navigation.subscription'), icon: FaCoins, path: '/story-workspace/subscription' },
    { id: 'settings-work', label: t('settings.workspace.navigation.work'), icon: FaBriefcase, path: '/story-workspace/settings/work' },
    { id: 'settings-model', label: t('settings.workspace.navigation.model'), icon: FaRobot, path: '/story-workspace/settings/model' },
    { id: 'settings-about', label: t('settings.workspace.navigation.about'), icon: FaInfoCircle, path: '/story-workspace/settings/about' },
  ], [t]);
  const filteredNavItems = navItems.filter((item) => item.label.toLocaleLowerCase().includes(searchQuery.trim().toLocaleLowerCase()));
  const isWorkSection = activeSection === 'settings-work'
    || activeSection === 'settings-resources'
    || activeSection === 'settings-plugins';
  const workTab = storyWorkspaceWorkTabForSection(activeSection);
  const workTabs = [
    { id: 'deck' as const, label: t('settings.workspace.work.tabs.deck'), icon: FaBriefcase },
    { id: 'resources' as const, label: t('settings.workspace.work.tabs.resources'), icon: FaDatabase },
    { id: 'plugins' as const, label: t('settings.workspace.work.tabs.plugins'), icon: FaPuzzlePiece },
  ];

  const workPanel = workTab === 'resources' ? (
    <ConnectorSettingsSection
      focusNonce={connectorSettingsFocusNonce}
      isMobile={isMobile}
      onOpenNotionDetail={onOpenNotionDetail}
      onOpenClaudeMcpDetail={onOpenClaudeMcpDetail}
    />
  ) : workTab === 'plugins' ? (
    <ClaudePluginAdminPage />
  ) : workDeckContent;

  const content = claudeMcpDetailServerName ? (
    <SettingsSection
      id="settings-claude-mcp-detail"
      title="Claude MCP"
      description="查看连接身份、可用能力和 Chat 可访问的工具。"
    >
      <ClaudeMcpServerDetailPage
        serverName={claudeMcpDetailServerName}
        onBack={onCloseClaudeMcpDetail ?? (() => undefined)}
        isMobile={isMobile}
      />
    </SettingsSection>
  ) : showNotionConnectorDetail ? (
    <div id="settings-resource-detail">
      <ConnectorNotionDetailPage onBack={onCloseNotionDetail ?? (() => undefined)} isMobile={isMobile} />
    </div>
  ) : isWorkSection ? (
    <section aria-labelledby="story-workspace-work-title" className="story-workspace-work" id="settings-work">
      <header className="story-workspace-work__header">
        <h2 id="story-workspace-work-title">{t('settings.workspace.work.title')}</h2>
        <p>{t('settings.workspace.work.description')}</p>
      </header>
      <div className="story-workspace-work__toolbar">
        <div aria-label={t('settings.workspace.work.tabsLabel')} className="story-workspace-work__tabs" role="tablist">
          {workTabs.map(({ id, label, icon: Icon }) => (
            <button
              aria-controls={`story-workspace-work-panel-${id}`}
              aria-selected={workTab === id}
              className={workTab === id ? 'is-active' : undefined}
              id={`story-workspace-work-tab-${id}`}
              key={id}
              onClick={() => onNavigate(`/story-workspace/settings/work?tab=${id}`)}
              role="tab"
              tabIndex={workTab === id ? 0 : -1}
              type="button"
            >
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
      <div
        aria-labelledby={`story-workspace-work-tab-${workTab}`}
        className="story-workspace-work__panel"
        id={`story-workspace-work-panel-${workTab}`}
        role="tabpanel"
      >
        {workPanel}
      </div>
    </section>
  ) : activeSection === 'settings-model' ? (
    <SettingsSection
      id="settings-model"
      title={t('settings.workspace.model.title')}
      description={t('settings.workspace.model.description')}
    >
      <div className="story-workspace-settings__card"><ModelConfigSection /></div>
    </SettingsSection>
  ) : activeSection === 'settings-subscription' ? (
    <StoryWorkspaceSubscriptionPage />
  ) : activeSection === 'settings-about' ? (
    <SettingsSection
      id="settings-about"
      title={t('settings.workspace.about.title')}
      description={t('settings.workspace.about.description')}
    >
      <div className="story-workspace-settings__card"><AboutView /></div>
    </SettingsSection>
  ) : (
    <SettingsSection
      id="settings-general"
      title={t('nav.settings')}
      description={t('settings.workspace.general.description')}
    >
      <div className="story-workspace-settings__card">
        <div className="story-workspace-settings__field">
          <label htmlFor="story-workspace-language">{t('settings.workspace.languageLabel')}</label>
          <p>{t('settings.language.description')}</p>
          <div className="story-workspace-settings__language-options" id="story-workspace-language">
            {languageCodes.map((code) => {
              const isActive = currentLanguage === code;
              return (
                <button
                  aria-pressed={isActive}
                  className={`story-workspace-settings__language-button${isActive ? ' is-active' : ''}`}
                  key={code}
                  onClick={() => onLanguageChange(code)}
                  type="button"
                >
                  {t(`settings.language.options.${code}`)}
                </button>
              );
            })}
          </div>
          <p className="story-workspace-settings__hint">{t('settings.language.preview')}</p>
        </div>
        <AppearanceThemeSetting />
        <div className="story-workspace-settings__toggle-row">
          <div>
            <strong>{t('settings.workspace.energy.label')}</strong>
            <p>{t('settings.workspace.energy.description')}</p>
          </div>
          <button
            aria-label={t('settings.workspace.energy.toggleLabel')}
            aria-pressed={showEnergyBar}
            className={`story-workspace-settings__switch${showEnergyBar ? ' is-active' : ''}`}
            onClick={onEnergyBarChange}
            type="button"
          ><span /></button>
        </div>
      </div>
    </SettingsSection>
  );

  return (
    <div className={`story-workspace-settings${isMobile ? ' story-workspace-settings--mobile' : ''}`}>
      <aside aria-label={t('settings.workspace.aria.categories')} className="story-workspace-settings__sidebar">
        <div className="story-workspace-settings__sidebar-header">
          <button
            aria-label={t('settings.workspace.backToApp')}
            className="story-workspace-settings__back-button"
            onClick={() => onNavigate('/story-workspace/dream')}
            type="button"
          >
            <FaArrowLeft aria-hidden="true" />
            <span>{t('settings.workspace.backToApp')}</span>
          </button>
          <label className="story-workspace-settings__search-label" htmlFor="story-workspace-settings-search">
            {t('settings.workspace.search.label')}
          </label>
          <div className="story-workspace-settings__search-wrap">
            <FaSearch aria-hidden="true" />
            <input
              id="story-workspace-settings-search"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t('settings.workspace.search.placeholder')}
              type="search"
              value={searchQuery}
            />
          </div>
        </div>
        <nav aria-label={t('settings.workspace.aria.navigation')} className="story-workspace-settings__nav">
          <span className="story-workspace-settings__nav-group">{t('settings.workspace.personal')}</span>
          {filteredNavItems.map((item) => {
            const Icon = item.icon;
            const selected = item.id === activeSection || (item.id === 'settings-work' && isWorkSection);
            return (
              <button
                aria-current={selected ? 'page' : undefined}
                className={`story-workspace-settings__nav-item${selected ? ' is-active' : ''}`}
                key={item.id}
                onClick={() => onNavigate(item.path)}
                type="button"
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            );
          })}
          {filteredNavItems.length === 0 ? (
            <span className="story-workspace-settings__no-results">{t('settings.workspace.search.noResults')}</span>
          ) : null}
        </nav>
      </aside>
      <div aria-label={t('settings.workspace.aria.content')} className="story-workspace-settings__content" role="region">
        <div className="story-workspace-settings__content-inner">{content}</div>
      </div>
    </div>
  );
}

export function storyWorkspaceSettingsSectionForRoute(route: StoryWorkspaceStaticRoute): StoryWorkspaceSettingsSection {
  return route === 'settings'
    || route === 'settings-work'
    || route === 'settings-resources'
    || route === 'settings-plugins'
    || route === 'settings-model'
    || route === 'settings-about'
    || route === 'subscription'
    ? route === 'subscription' ? 'settings-subscription' : route
    : 'settings';
}
