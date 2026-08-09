/* eslint-disable react-refresh/only-export-components -- route metadata helper intentionally shares this page module. */
import { useMemo, useState, type ReactNode } from 'react';
import { FaArrowLeft, FaCog, FaCoins, FaDatabase, FaInfoCircle, FaPuzzlePiece, FaRobot, FaSearch } from 'react-icons/fa';
import { useTranslation } from 'react-i18next';
import AboutView from '../../components/AboutView';
import ClaudePluginAdminPage from '../../components/claude-plugin-admin/ClaudePluginAdminPage';
import ConnectorNotionDetailPage from '../../components/dashboard/ConnectorNotionDetailPage';
import ConnectorSettingsSection from '../../components/dashboard/ConnectorSettingsSection';
import ModelConfigSection from '../../components/dashboard/ModelConfigSection';
import type { StoryWorkspaceStaticRoute } from '../../router/storyWorkspacePath';
import { StoryWorkspaceSubscriptionPage } from './StoryWorkspaceSubscriptionPage';
import './StoryWorkspaceSettingsPage.css';

export type StoryWorkspaceSettingsSection =
  | 'settings'
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
  onOpenNotionDetail?: () => void;
  onCloseNotionDetail?: () => void;
  onNavigate: (path: string) => void;
}

interface SettingsNavItem {
  id: StoryWorkspaceSettingsSection;
  label: string;
  icon: typeof FaCog;
  path: string;
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
  onOpenNotionDetail,
  onCloseNotionDetail,
  onNavigate,
}: StoryWorkspaceSettingsPageProps) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const navItems = useMemo<SettingsNavItem[]>(() => [
    { id: 'settings', label: '常规', icon: FaCog, path: '/story-workspace/settings' },
    { id: 'settings-subscription', label: '订阅', icon: FaCoins, path: '/story-workspace/subscription' },
    { id: 'settings-resources', label: '资源连接', icon: FaDatabase, path: '/story-workspace/settings/resources' },
    { id: 'settings-plugins', label: '插件', icon: FaPuzzlePiece, path: '/story-workspace/settings/plugins' },
    { id: 'settings-model', label: 'AI 模型', icon: FaRobot, path: '/story-workspace/settings/model' },
    { id: 'settings-about', label: '关于', icon: FaInfoCircle, path: '/story-workspace/settings/about' },
  ], []);
  const filteredNavItems = navItems.filter((item) => item.label.toLocaleLowerCase().includes(searchQuery.trim().toLocaleLowerCase()));

  const content = showNotionConnectorDetail ? (
    <SettingsSection id="settings-resource-detail" title="资源连接" description="管理单个资源连接。">
      <ConnectorNotionDetailPage onBack={onCloseNotionDetail ?? (() => undefined)} isMobile={isMobile} />
    </SettingsSection>
  ) : activeSection === 'settings-resources' ? (
    <SettingsSection id="settings-resources" title="资源连接" description="管理可供创作工作区使用的外部资源。">
      <ConnectorSettingsSection
        focusNonce={connectorSettingsFocusNonce}
        isMobile={isMobile}
        onOpenNotionDetail={onOpenNotionDetail}
      />
    </SettingsSection>
  ) : activeSection === 'settings-plugins' ? (
    <SettingsSection id="settings-plugins" title="插件" description="安装和管理工作区扩展能力。">
      <ClaudePluginAdminPage />
    </SettingsSection>
  ) : activeSection === 'settings-model' ? (
    <SettingsSection id="settings-model" title="AI 模型配置" description="配置创作工作区使用的模型和运行策略。">
      <div className="story-workspace-settings__card"><ModelConfigSection /></div>
    </SettingsSection>
  ) : activeSection === 'settings-subscription' ? (
    <StoryWorkspaceSubscriptionPage />
  ) : activeSection === 'settings-about' ? (
    <SettingsSection id="settings-about" title="关于" description="Ink & Memory 工作区信息。">
      <div className="story-workspace-settings__card"><AboutView /></div>
    </SettingsSection>
  ) : (
    <SettingsSection id="settings-general" title={t('nav.settings')} description="调整语言和工作区显示偏好。">
      <div className="story-workspace-settings__card">
        <div className="story-workspace-settings__field">
          <label htmlFor="story-workspace-language">Language / 语言</label>
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
        <div className="story-workspace-settings__toggle-row">
          <div>
            <strong>Energy Bar / 能量条</strong>
            <p>Toggle the energy progress bar in the bottom stats line.</p>
          </div>
          <button
            aria-label="切换能量条"
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
      <aside aria-label="设置分类" className="story-workspace-settings__sidebar">
        <div className="story-workspace-settings__sidebar-header">
          <button
            aria-label="返回应用"
            className="story-workspace-settings__back-button"
            onClick={() => onNavigate('/story-workspace/dream')}
            type="button"
          >
            <FaArrowLeft aria-hidden="true" />
            <span>返回应用</span>
          </button>
          <label className="story-workspace-settings__search-label" htmlFor="story-workspace-settings-search">
            搜索设置
          </label>
          <div className="story-workspace-settings__search-wrap">
            <FaSearch aria-hidden="true" />
            <input
              id="story-workspace-settings-search"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="搜索设置..."
              type="search"
              value={searchQuery}
            />
          </div>
        </div>
        <nav aria-label="设置分类导航" className="story-workspace-settings__nav">
          <span className="story-workspace-settings__nav-group">个人</span>
          {filteredNavItems.map((item) => {
            const Icon = item.icon;
            const selected = item.id === activeSection;
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
            <span className="story-workspace-settings__no-results">没有匹配的设置</span>
          ) : null}
        </nav>
      </aside>
      <div aria-label="设置内容" className="story-workspace-settings__content" role="region">
        <div className="story-workspace-settings__content-inner">{content}</div>
      </div>
    </div>
  );
}

export function storyWorkspaceSettingsSectionForRoute(route: StoryWorkspaceStaticRoute): StoryWorkspaceSettingsSection {
  return route === 'settings'
    || route === 'settings-resources'
    || route === 'settings-plugins'
    || route === 'settings-model'
    || route === 'settings-about'
    || route === 'subscription'
    ? route === 'subscription' ? 'settings-subscription' : route
    : 'settings';
}
