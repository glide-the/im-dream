// [Input] Current Story Workspace path, navigation callbacks, collapse state, and the existing auth context.
// [Output] Render the collapsible desktop Story Workspace navigation sidebar.
// [Pos] Story Workspace left layout region.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FaBookOpen,
  FaChevronLeft,
  FaChevronRight,
  FaCog,
  FaMoon,
  FaSun,
  FaThLarge,
  FaUserCircle,
} from 'react-icons/fa';
import { useAuth } from '../../../contexts/AuthContext';
import { getTheme, onThemeChange, toggleTheme } from '../../../utils/theme';

const storyWorkspaceMainNavPaths = {
  writing: '/story-workspace/writing',
  timeline: '/story-workspace/timeline',
  analysis: '/story-workspace/analysis',
  decks: '/story-workspace/decks',
  dream: '/story-workspace/dream',
  chat: '/story-workspace/chat',
} as const;

export interface StoryWorkspaceSidebarProps {
  collapsed: boolean;
  currentPath: string;
  onNavigate: (path: string) => void;
  onToggleCollapse: () => void;
}

export function StoryWorkspaceSidebar({
  collapsed,
  currentPath,
  onNavigate,
  onToggleCollapse,
}: StoryWorkspaceSidebarProps) {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const [isDark, setIsDark] = useState(() => getTheme() === 'dark');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const displayName = user?.display_name?.trim() || user?.email || 'Ink & Memory 用户';
  const avatarLabel = Array.from(displayName)[0]?.toUpperCase() || 'I';
  const themeToggleLabel = isDark ? '切换到浅色' : '切换到深色';
  useEffect(() => {
    return onThemeChange((resolved) => {
      setIsDark(resolved === 'dark');
    });
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty(
      '--story-workspace-sidebar-width',
      collapsed ? '72px' : '240px',
    );
    return () => {
      document.documentElement.style.removeProperty('--story-workspace-sidebar-width');
    };
  }, [collapsed]);

  useEffect(() => {
    if (!showUserMenu) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setShowUserMenu(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showUserMenu]);

  const handleToggleTheme = () => {
    toggleTheme();
  };

  return (
    <div
      className={`story-workspace-sidebar${collapsed ? ' story-workspace-sidebar--collapsed' : ''}`}
    >
      <style>{`
        .story-workspace-sidebar {
          display: flex;
          width: 240px;
          min-width: 240px;
          height: 100%;
          min-height: 100%;
          flex-direction: column;
          padding: 28px 20px 20px;
          box-sizing: border-box;
          color: var(--color-text-body);
          background: var(--color-bg-paper);
          font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          transition: width 180ms ease, min-width 180ms ease, padding 180ms ease;
        }

        .story-workspace-sidebar--collapsed {
          width: 72px;
          min-width: 72px;
          padding: 28px 12px 16px;
        }

        .story-workspace-sidebar__brand {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 8px;
          padding: 0 8px 24px;
          border-bottom: 1px dashed var(--color-border-paper);
        }

        .story-workspace-sidebar--collapsed .story-workspace-sidebar__brand {
          justify-content: center;
          padding: 0 0 20px;
        }

        .story-workspace-sidebar--collapsed .story-workspace-sidebar__brand-text,
        .story-workspace-sidebar--collapsed .story-workspace-sidebar__label,
        .story-workspace-sidebar--collapsed .story-workspace-sidebar__theme-label,
        .story-workspace-sidebar--collapsed .story-workspace-sidebar__settings-label,
        .story-workspace-sidebar--collapsed .story-workspace-sidebar__user-details {
          display: none;
        }

        .story-workspace-sidebar--collapsed .story-workspace-sidebar__nav-button,
        .story-workspace-sidebar--collapsed .story-workspace-sidebar__theme-button,
        .story-workspace-sidebar--collapsed .story-workspace-sidebar__settings-button {
          justify-content: center;
          gap: 0;
          padding: 10px 0;
        }

        .story-workspace-sidebar--collapsed .story-workspace-sidebar__user {
          padding: 14px 0 0;
        }

        .story-workspace-sidebar--collapsed .story-workspace-sidebar__user-trigger {
          justify-content: center;
          padding: 0;
        }

        .story-workspace-sidebar__toggle {
          display: inline-flex;
          flex: 0 0 28px;
          width: 28px;
          height: 28px;
          align-items: center;
          justify-content: center;
          padding: 0;
          color: var(--color-text-secondary);
          background: transparent;
          border: 1px solid var(--color-border-paper);
          border-radius: 6px;
          cursor: pointer;
          font: inherit;
          font-size: 11px;
          transition: background-color 160ms ease, color 160ms ease, border-color 160ms ease;
        }

        .story-workspace-sidebar__toggle:hover {
          color: var(--color-text-primary);
          background: var(--color-bg-hover);
          border-color: var(--color-border-neutral);
        }

        .story-workspace-sidebar__toggle:focus-visible {
          outline: 2px solid var(--color-border-focus);
          outline-offset: 2px;
        }

        .story-workspace-sidebar__brand-name {
          margin: 0;
          color: var(--color-text-primary);
          font-family: Georgia, "Times New Roman", serif;
          font-size: 19px;
          font-style: italic;
          font-weight: 700;
          line-height: 1.35;
        }

        .story-workspace-sidebar__brand-context {
          margin: 5px 0 0;
          color: var(--color-text-secondary);
          font-size: 12px;
          letter-spacing: 0.08em;
          line-height: 1.5;
        }

        .story-workspace-sidebar__nav {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding-top: 20px;
        }

        .story-workspace-sidebar__nav-button,
        .story-workspace-sidebar__theme-button,
        .story-workspace-sidebar__settings-button {
          display: flex;
          width: 100%;
          min-height: 44px;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          color: var(--color-text-body);
          background: transparent;
          border: 0;
          border-radius: 7px;
          cursor: pointer;
          font: inherit;
          font-size: 14px;
          font-weight: 500;
          line-height: 1.4;
          text-align: left;
          transition: background-color 160ms ease, color 160ms ease;
        }

        .story-workspace-sidebar__nav-button:hover,
        .story-workspace-sidebar__theme-button:hover,
        .story-workspace-sidebar__settings-button:hover {
          color: var(--color-text-primary);
          background: var(--color-bg-hover);
        }

        .story-workspace-sidebar__nav-button:focus-visible,
        .story-workspace-sidebar__theme-button:focus-visible,
        .story-workspace-sidebar__settings-button:focus-visible {
          outline: 2px solid var(--color-border-focus);
          outline-offset: 2px;
        }

        .story-workspace-sidebar__nav-button[aria-current="page"] {
          color: var(--color-text-primary);
        }

        .story-workspace-sidebar__nav-button[aria-current="page"] .story-workspace-sidebar__label {
          text-decoration-line: underline;
          text-decoration-color: var(--color-voice-yellow);
          text-decoration-thickness: 2px;
          text-underline-offset: 4px;
        }

        .story-workspace-sidebar__icon {
          flex: 0 0 20px;
          width: 20px;
          height: 20px;
          color: var(--color-text-primary);
        }

        .story-workspace-sidebar__footer {
          margin-top: auto;
          padding-top: 20px;
          border-top: 1px dashed var(--color-border-paper);
        }

        .story-workspace-sidebar__user {
          position: relative;
          margin-top: 12px;
          padding: 14px 10px 0;
          border-top: 1px dashed var(--color-border-paper);
        }

        .story-workspace-sidebar__user-trigger {
          display: flex;
          width: 100%;
          align-items: center;
          gap: 10px;
          padding: 0;
          color: inherit;
          background: transparent;
          border: 0;
          border-radius: 8px;
          cursor: pointer;
          font: inherit;
          text-align: left;
        }

        .story-workspace-sidebar__user-trigger:hover {
          background: var(--color-bg-hover);
        }

        .story-workspace-sidebar__user-trigger:focus-visible,
        .story-workspace-sidebar__logout:focus-visible {
          outline: 2px solid var(--color-border-focus);
          outline-offset: 2px;
        }

        .story-workspace-sidebar__avatar {
          display: inline-flex;
          flex: 0 0 32px;
          width: 32px;
          height: 32px;
          align-items: center;
          justify-content: center;
          color: var(--color-bg-paper);
          background: var(--color-action-primary);
          border-radius: 50%;
          font-size: 13px;
          font-weight: 700;
        }

        .story-workspace-sidebar__user-details {
          min-width: 0;
        }

        .story-workspace-sidebar__user-name,
        .story-workspace-sidebar__user-email {
          display: block;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .story-workspace-sidebar__user-name {
          color: var(--color-text-primary);
          font-size: 13px;
          font-weight: 600;
        }

        .story-workspace-sidebar__user-email {
          margin-top: 2px;
          color: var(--color-text-muted);
          font-size: 11px;
        }

        .story-workspace-sidebar__user-scrim {
          position: fixed;
          z-index: 998;
          inset: 0;
          background: transparent;
        }

        .story-workspace-sidebar__user-menu {
          position: fixed;
          z-index: 999;
          left: 20px;
          bottom: 88px;
          width: 220px;
          overflow: hidden;
          color: var(--color-text-body);
          background: var(--color-bg-surface-solid);
          border: 1px solid var(--color-border-paper);
          border-radius: 10px;
          box-shadow: 0 8px 24px var(--color-shadow-medium);
        }

        .story-workspace-sidebar--collapsed .story-workspace-sidebar__user-menu {
          left: 80px;
          bottom: 20px;
        }

        .story-workspace-sidebar__user-menu-profile {
          padding: 12px 14px;
          border-bottom: 1px solid var(--color-border-neutral);
        }

        .story-workspace-sidebar__user-menu-name {
          overflow: hidden;
          color: var(--color-text-primary);
          font-size: 13px;
          font-weight: 650;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .story-workspace-sidebar__user-menu-email {
          margin-top: 3px;
          overflow: hidden;
          color: var(--color-text-secondary);
          font-size: 11px;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .story-workspace-sidebar__logout {
          display: block;
          width: 100%;
          padding: 10px 14px;
          color: var(--color-text-body);
          background: transparent;
          border: 0;
          cursor: pointer;
          font: inherit;
          font-size: 13px;
          text-align: left;
        }

        .story-workspace-sidebar__logout:hover {
          background: var(--color-bg-hover);
        }
      `}</style>

      <header className="story-workspace-sidebar__brand">
        <div className="story-workspace-sidebar__brand-text">
          <p className="story-workspace-sidebar__brand-name">Ink &amp; Memory</p>
          <p className="story-workspace-sidebar__brand-context">创作者工作台</p>
        </div>
        <button
          aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'}
          className="story-workspace-sidebar__toggle"
          onClick={onToggleCollapse}
          title={collapsed ? '展开侧边栏' : '折叠侧边栏'}
          type="button"
        >
          {collapsed
            ? <FaChevronRight aria-hidden="true" />
            : <FaChevronLeft aria-hidden="true" />}
        </button>
      </header>

      <nav aria-label="Story Workspace 导航" className="story-workspace-sidebar__nav">
        {([
          { label: t('nav.writing'), view: 'writing', path: storyWorkspaceMainNavPaths.writing },
          { label: t('nav.timeline'), view: 'timeline', path: storyWorkspaceMainNavPaths.timeline },
          { label: t('nav.analysis'), view: 'analysis', path: storyWorkspaceMainNavPaths.analysis },
          { label: t('nav.decks'), view: 'decks', path: storyWorkspaceMainNavPaths.decks },
          { label: t('nav.dream'), view: 'dream', path: storyWorkspaceMainNavPaths.dream },
          { label: t('nav.chat'), view: 'chat', path: storyWorkspaceMainNavPaths.chat },
        ] as const).map((item) => {
          const isCurrent = currentPath === item.path;
          return (
            <button
              aria-current={isCurrent ? 'page' : undefined}
              className="story-workspace-sidebar__nav-button"
              key={item.view}
              onClick={() => onNavigate(item.path)}
              title={collapsed ? item.label : undefined}
              type="button"
            >
              <span className="story-workspace-sidebar__label">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <footer className="story-workspace-sidebar__footer">
        <button
          aria-label={isDark ? '切换到浅色' : '切换到深色'}
          className="story-workspace-sidebar__theme-button"
          onClick={handleToggleTheme}
          title={isDark ? '切换到浅色' : '切换到深色'}
          type="button"
        >
          {isDark
            ? <FaSun aria-hidden="true" className="story-workspace-sidebar__icon" />
            : <FaMoon aria-hidden="true" className="story-workspace-sidebar__icon" />}
          <span className="story-workspace-sidebar__theme-label">{themeToggleLabel}</span>
        </button>
        <button
          aria-current={currentPath.startsWith('/story-workspace/settings') ? 'page' : undefined}
          className="story-workspace-sidebar__settings-button"
          onClick={() => onNavigate('/story-workspace/settings')}
          title={collapsed ? '设置' : undefined}
          type="button"
        >
          <FaCog aria-hidden="true" className="story-workspace-sidebar__icon" />
          <span className="story-workspace-sidebar__settings-label">设置</span>
        </button>
        <div className="story-workspace-sidebar__user">
          <button
            aria-expanded={showUserMenu}
            aria-haspopup="menu"
            aria-label="打开用户菜单"
            className="story-workspace-sidebar__user-trigger"
            onClick={() => setShowUserMenu((visible) => !visible)}
            title="用户菜单"
            type="button"
          >
            <span aria-hidden="true" className="story-workspace-sidebar__avatar">
              {user ? avatarLabel : <FaUserCircle />}
            </span>
            <span className="story-workspace-sidebar__user-details">
              <span className="story-workspace-sidebar__user-name">{displayName}</span>
              {user?.display_name && user.email ? (
                <span className="story-workspace-sidebar__user-email">{user.email}</span>
              ) : null}
            </span>
          </button>
          {showUserMenu ? (
            <>
              <div
                aria-hidden="true"
                className="story-workspace-sidebar__user-scrim"
                onClick={() => setShowUserMenu(false)}
              />
              <div aria-label="用户菜单" className="story-workspace-sidebar__user-menu" role="menu">
                <div className="story-workspace-sidebar__user-menu-profile">
                  <div className="story-workspace-sidebar__user-menu-name">{user?.display_name || 'User'}</div>
                  {user?.email ? <div className="story-workspace-sidebar__user-menu-email">{user.email}</div> : null}
                </div>
                <button
                  className="story-workspace-sidebar__logout"
                  onClick={() => {
                    setShowUserMenu(false);
                    logout();
                  }}
                  role="menuitem"
                  type="button"
                >
                  Logout
                </button>
              </div>
            </>
          ) : null}
        </div>
      </footer>
    </div>
  );
}
