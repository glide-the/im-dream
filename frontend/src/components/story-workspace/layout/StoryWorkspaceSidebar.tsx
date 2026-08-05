// [Input] Current Story Workspace path, navigation callbacks, collapse state, and the existing auth context.
// [Output] Render the collapsible desktop Story Workspace navigation sidebar.
// [Pos] Story Workspace left layout region.
import { useEffect, useState } from 'react';
import type { IconType } from 'react-icons';
import {
  FaBookOpen,
  FaChevronLeft,
  FaChevronRight,
  FaCog,
  FaMoon,
  FaRegCreditCard,
  FaSun,
  FaThLarge,
  FaUserCircle,
} from 'react-icons/fa';
import { useAuth } from '../../../contexts/AuthContext';
import { getTheme, onThemeChange, toggleTheme } from '../../../utils/theme';

interface StoryWorkspaceSidebarItem {
  icon: IconType;
  label: string;
  path: string;
}

const storyWorkspaceSidebarItems: StoryWorkspaceSidebarItem[] = [
  { icon: FaBookOpen, label: 'Dream', path: '/story-workspace/dream' },
  { icon: FaThLarge, label: 'Decks', path: '/story-workspace/decks' },
  { icon: FaRegCreditCard, label: '订阅', path: '/story-workspace/subscription' },
];

export interface StoryWorkspaceSidebarProps {
  collapsed: boolean;
  currentPath: string;
  onNavigate: (path: string) => void;
  onOpenSettings: () => void;
  onToggleCollapse: () => void;
}

export function StoryWorkspaceSidebar({
  collapsed,
  currentPath,
  onNavigate,
  onOpenSettings,
  onToggleCollapse,
}: StoryWorkspaceSidebarProps) {
  const { user } = useAuth();
  const [isDark, setIsDark] = useState(() => getTheme() === 'dark');
  const displayName = user?.display_name?.trim() || user?.email || 'Ink & Memory 用户';
  const avatarLabel = Array.from(displayName)[0]?.toUpperCase() || 'I';
  const themeToggleLabel = isDark ? '切换到浅色' : '切换到深色';

  useEffect(() => {
    return onThemeChange((resolved) => {
      setIsDark(resolved === 'dark');
    });
  }, []);

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
          justify-content: center;
          padding: 14px 0 0;
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
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 12px;
          padding: 14px 10px 0;
          border-top: 1px dashed var(--color-border-paper);
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
        {storyWorkspaceSidebarItems.map((item) => {
          const Icon = item.icon;
          const isCurrent = item.path === currentPath;

          return (
            <button
              aria-current={isCurrent ? 'page' : undefined}
              className="story-workspace-sidebar__nav-button"
              key={item.path}
              onClick={() => onNavigate(item.path)}
              title={collapsed ? item.label : undefined}
              type="button"
            >
              <Icon aria-hidden="true" className="story-workspace-sidebar__icon" />
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
          className="story-workspace-sidebar__settings-button"
          onClick={onOpenSettings}
          title={collapsed ? '设置' : undefined}
          type="button"
        >
          <FaCog aria-hidden="true" className="story-workspace-sidebar__icon" />
          <span className="story-workspace-sidebar__settings-label">设置</span>
        </button>

        <div className="story-workspace-sidebar__user">
          <span aria-hidden="true" className="story-workspace-sidebar__avatar">
            {user ? avatarLabel : <FaUserCircle />}
          </span>
          <span className="story-workspace-sidebar__user-details">
            <span className="story-workspace-sidebar__user-name">{displayName}</span>
            {user?.display_name && user.email ? (
              <span className="story-workspace-sidebar__user-email">{user.email}</span>
            ) : null}
          </span>
        </div>
      </footer>
    </div>
  );
}
