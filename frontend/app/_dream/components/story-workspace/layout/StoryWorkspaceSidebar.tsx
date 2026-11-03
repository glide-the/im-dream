// [Sync] 2026-11-02: adopt display-only Kastention naming; existing behavior and technical identities remain.
// [Sync] 2026-11-01: let the Writing page reuse the existing narrow More menu and report its open state.
// [Sync] 2026-11-01: narrow More shares native cards and guidance; existing Modal, desktop and route owners remain.
// [Sync] 2026-10-29: narrow More opens one full-page five-item menu; desktop disclosure and routes remain.
// [Sync] 2026-09-14: failed logout retains the real session and shows safe feedback in the user menu.
// [Input] Current Story Workspace path, navigation callbacks, collapse state, and the existing auth context.
// [Output] Render the desktop sidebar and the narrow full-page Writing/Timeline/Reflections/Theme/Settings menu.
// [Pos] Story Workspace desktop sidebar and narrow bottom-navigation region.
// [Sync] 2026-08-14: temporarily hide Writing, Timeline, and Analysis entries while
//                    retaining their routes and content for authorized deep links.
// [Sync] 2026-08-14: order visible entries as Chat, Dream, then Decks.
// [Sync] 2026-08-15: restore Writing, Timeline, and Analysis in their original
//                    sidebar positions, reusing the retained production routes.
// [Sync] 2026-08-15: group restored Writing, Timeline, and Analysis under an
//                    accessible More disclosure below Chat, Dream, and Decks.
// [Sync] 2026-09-18: render the same navigation as a thumb-reachable bottom bar and More sheet on mobile.
import { BRAND_NAME } from '../../../constants/brand';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {Text} from 'react-native';
import type { IconType } from 'react-icons';
import {
  FaBookOpen,
  FaChartLine,
  FaChevronLeft,
  FaChevronRight,
  FaComments,
  FaCog,
  FaEllipsisH,
  FaMoon,
  FaPenNib,
  FaStream,
  FaSun,
  FaThLarge,
  FaUserCircle,
} from 'react-icons/fa';
import { useAuth } from '../../../contexts/AuthContext';
import { getTheme, getThemeMode, onThemeChange, toggleTheme } from '../../../utils/theme';
import Modal from '../../chat/Modal';
import {IconClock, IconEdit, IconChevronRight} from '../../chat/Icons';
import MoreNavigationContent, {type MoreLabelProps, type MoreNavigationItem} from './MoreNavigationContent';
import {MORE_NAVIGATION_ITEMS} from './moreNavigation';

const moreColors = {
  'color-bg-app': 'var(--color-bg-app)', 'color-bg-paper': 'var(--color-bg-paper)',
  'color-bg-hover': 'var(--color-bg-hover)', 'color-border-paper': 'var(--color-border-paper)',
  'color-text-primary': 'var(--color-text-primary)', 'color-text-secondary': 'var(--color-text-secondary)',
  'color-state-error': 'var(--color-state-error)',
};
function MoreWebLabel({style, ...props}: MoreLabelProps) {
  return <Text {...props} style={[{fontFamily: 'inherit'}, style]}/>;
}
function MoreWebIcon({id, color}: {id: MoreNavigationItem['id']; color: string}) {
  if (id === 'writing') return <IconEdit style={{width: 26, height: 26, color}}/>;
  if (id === 'timeline') return <IconClock style={{width: 26, height: 26, color}}/>;
  return <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {id === 'analysis' ? <><path d="M4 4v16h16"/><path d="m7 14 4-4 4 3 5-7"/></> : id === 'theme' ? <><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18Z" fill={color} stroke="none"/></> : <><path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/></>}
  </svg>;
}

const storyWorkspaceMainNavPaths = {
  writing: '/story-workspace/writing',
  timeline: '/story-workspace/timeline',
  analysis: '/story-workspace/analysis',
  decks: '/story-workspace/decks',
  dream: '/story-workspace/dream',
  chat: '/story-workspace/chat',
} as const;

export interface StoryWorkspaceSidebarProps {
  mobileMoreNonce?:number;
  onMobileMoreOpenChange?:(open:boolean)=>void;
  collapsed: boolean;
  currentPath: string;
  onNavigate: (path: string) => void;
  onToggleCollapse: () => void;
}

export function StoryWorkspaceSidebar({
  mobileMoreNonce, onMobileMoreOpenChange,
  collapsed,
  currentPath,
  onNavigate,
  onToggleCollapse,
}: StoryWorkspaceSidebarProps) {
  const { user, logout, authError } = useAuth();
  const { t } = useTranslation();
  const [isDark, setIsDark] = useState(() => getTheme() === 'dark');
  const [themeMode, setThemeMode] = useState(getThemeMode);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [mobileMoreOpen,setMobileMoreOpen]=useState(false);
  useEffect(()=>{if(mobileMoreNonce){setShowUserMenu(false);setMobileMoreOpen(true);}},[mobileMoreNonce]);
  useEffect(()=>{onMobileMoreOpenChange?.(mobileMoreOpen);},[mobileMoreOpen,onMobileMoreOpenChange]);
  const [showMoreNavigation, setShowMoreNavigation] = useState(() => (
    currentPath === storyWorkspaceMainNavPaths.writing
    || currentPath === storyWorkspaceMainNavPaths.timeline
    || currentPath === storyWorkspaceMainNavPaths.analysis
  ));
  const displayName = user?.display_name?.trim() || user?.email || `${t('brand.name')} 用户`;
  const avatarLabel = Array.from(displayName)[0]?.toUpperCase() || 'I';
  const themeToggleLabel = isDark ? '切换到浅色' : '切换到深色';
  useEffect(() => {
    return onThemeChange((resolved, mode) => {
      setIsDark(resolved === 'dark');
      setThemeMode(mode);
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

  useEffect(() => {
    if (
      currentPath === storyWorkspaceMainNavPaths.writing
      || currentPath === storyWorkspaceMainNavPaths.timeline
      || currentPath === storyWorkspaceMainNavPaths.analysis
    ) {
      setShowMoreNavigation(true);
    }
  }, [currentPath]);

  useEffect(()=>{
    const media=window.matchMedia('(max-width: 767px)');
    const closeWhenWide=()=>{if(!media.matches)setMobileMoreOpen(false);};
    const closeAfterHistoryNavigation=()=>setMobileMoreOpen(false);
    media.addEventListener('change',closeWhenWide);
    window.addEventListener('popstate',closeAfterHistoryNavigation);
    return()=>{media.removeEventListener('change',closeWhenWide);window.removeEventListener('popstate',closeAfterHistoryNavigation);};
  },[]);

  const handleToggleTheme = () => {
    toggleTheme();
  };

  const handleNavigate = (path: string) => {
    setShowMoreNavigation(false);
    setMobileMoreOpen(false);
    setShowUserMenu(false);
    onNavigate(path);
  };

  return (
    <div
      className={`story-workspace-sidebar${collapsed ? ' story-workspace-sidebar--collapsed' : ''}`}
      data-mobile-more-open={mobileMoreOpen ? 'true' : 'false'}
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
          font-family: var(--font-family-ui);
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
        .story-workspace-sidebar--collapsed .story-workspace-sidebar__disclosure-chevron,
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

        .story-workspace-sidebar__more-button {
          margin-top: 8px;
        }

        .story-workspace-sidebar__disclosure-chevron {
          width: 12px;
          height: 12px;
          margin-left: auto;
          color: var(--color-text-secondary);
          transition: transform 160ms ease;
        }

        .story-workspace-sidebar__disclosure-chevron--open {
          transform: rotate(90deg);
        }

        .story-workspace-sidebar__legacy-nav {
          display: flex;
          flex-direction: column;
          gap: 4px;
          animation: story-workspace-sidebar-reveal 160ms ease-out;
        }

        .story-workspace-sidebar__legacy-nav .story-workspace-sidebar__nav-button {
          padding-left: 24px;
          color: var(--color-text-secondary);
          font-size: 13px;
        }

        .story-workspace-sidebar--collapsed .story-workspace-sidebar__legacy-nav .story-workspace-sidebar__nav-button {
          padding-left: 0;
        }

        @keyframes story-workspace-sidebar-reveal {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @media (prefers-reduced-motion: reduce) {
          .story-workspace-sidebar__legacy-nav {
            animation: none;
          }

          .story-workspace-sidebar__disclosure-chevron {
            transition: none;
          }
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
          <p className="story-workspace-sidebar__brand-name">{BRAND_NAME}</p>
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
          { icon: FaComments, label: t('nav.chat'), view: 'chat', path: storyWorkspaceMainNavPaths.chat },
          { icon: FaBookOpen, label: t('nav.dream'), view: 'dream', path: storyWorkspaceMainNavPaths.dream },
          { icon: FaThLarge, label: t('nav.decks'), view: 'decks', path: storyWorkspaceMainNavPaths.decks },
        ] as const).map((item) => {
          const isCurrent = currentPath === item.path;
          const Icon = item.icon as IconType;
          return (
            <button
              aria-label={collapsed ? item.label : undefined}
              aria-current={isCurrent ? 'page' : undefined}
              className="story-workspace-sidebar__nav-button"
              key={item.view}
              onClick={() => handleNavigate(item.path)}
              title={collapsed ? item.label : undefined}
              type="button"
            >
              <Icon aria-hidden="true" className="story-workspace-sidebar__icon" />
              <span className="story-workspace-sidebar__label">{item.label}</span>
            </button>
          );
        })}
        <button
          aria-controls="story-workspace-more-navigation"
          aria-expanded={showMoreNavigation}
          aria-label={collapsed ? t('nav.more') : undefined}
          className="story-workspace-sidebar__nav-button story-workspace-sidebar__more-button story-workspace-sidebar__more-button--desktop"
          aria-current={showMoreNavigation || currentPath === storyWorkspaceMainNavPaths.writing || currentPath === storyWorkspaceMainNavPaths.timeline || currentPath === storyWorkspaceMainNavPaths.analysis ? 'page' : undefined}
          onClick={()=>setShowMoreNavigation(visible=>!visible)}
          title={collapsed ? t('nav.more') : undefined}
          type="button"
        >
          <FaEllipsisH aria-hidden="true" className="story-workspace-sidebar__icon" />
          <span className="story-workspace-sidebar__label">{t('nav.more')}</span>
          <FaChevronRight
            aria-hidden="true"
            className={`story-workspace-sidebar__disclosure-chevron${showMoreNavigation ? ' story-workspace-sidebar__disclosure-chevron--open' : ''}`}
          />
        </button>
        <button type="button" className="story-workspace-sidebar__nav-button story-workspace-sidebar__more-button story-workspace-sidebar__more-button--narrow" aria-controls="story-workspace-narrow-more-items" aria-haspopup="dialog" aria-expanded={mobileMoreOpen} aria-current={mobileMoreOpen||currentPath===storyWorkspaceMainNavPaths.writing||currentPath===storyWorkspaceMainNavPaths.timeline||currentPath===storyWorkspaceMainNavPaths.analysis?'page':undefined} onClick={()=>{setShowUserMenu(false);setMobileMoreOpen(true);}}>
          <FaEllipsisH aria-hidden="true" className="story-workspace-sidebar__icon"/><span className="story-workspace-sidebar__label">{t('nav.more')}</span>
        </button>
        {showMoreNavigation ? (
          <div
            aria-label={t('nav.more')}
            className="story-workspace-sidebar__legacy-nav"
            id="story-workspace-more-navigation"
            role="group"
          >
            {([
              { icon: FaPenNib, label: t('nav.writing'), view: 'writing', path: storyWorkspaceMainNavPaths.writing },
              { icon: FaStream, label: t('nav.timeline'), view: 'timeline', path: storyWorkspaceMainNavPaths.timeline },
              { icon: FaChartLine, label: t('nav.analysis'), view: 'analysis', path: storyWorkspaceMainNavPaths.analysis },
            ] as const).map((item) => {
              const isCurrent = currentPath === item.path;
              const Icon = item.icon as IconType;
              return (
                <button
                  aria-label={collapsed ? item.label : undefined}
                  aria-current={isCurrent ? 'page' : undefined}
                  className="story-workspace-sidebar__nav-button"
                  key={item.view}
                  onClick={() => handleNavigate(item.path)}
                  title={collapsed ? item.label : undefined}
                  type="button"
                >
                  <Icon aria-hidden="true" className="story-workspace-sidebar__icon" />
                  <span className="story-workspace-sidebar__label">{item.label}</span>
                </button>
              );
            })}
          </div>
        ) : null}
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
          onClick={() => handleNavigate('/story-workspace/settings')}
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
                    void logout();
                  }}
                  role="menuitem"
                  type="button"
                >
                  Logout
                </button>
                {authError && <p role="alert" style={{ color: 'var(--color-state-danger)', padding: '0 12px' }}>{authError}</p>}
              </div>
            </>
          ) : null}
        </div>
      </footer>
      <Modal open={mobileMoreOpen} title={t('nav.more')} closeLabel={t('chat.history.close')} onClose={()=>setMobileMoreOpen(false)} surfaceClassName="story-workspace-narrow-more-page">
        <nav id="story-workspace-narrow-more-items" aria-label={t('nav.more')} className="story-workspace-narrow-more-page__items">
          <MoreNavigationContent colors={moreColors} Label={MoreWebLabel} renderIcon={(id,color)=><MoreWebIcon id={id} color={color}/>} chevron={<IconChevronRight style={{width:18,height:18,color:'var(--color-text-muted)'}}/>} appearance={t(`settings.workspace.theme.options.${themeMode}`)+(themeMode==='system'?` · ${t(`settings.workspace.theme.options.${isDark?'dark':'light'}`)}`:'')} nextAppearance={t(`settings.workspace.theme.options.${isDark?'light':'dark'}`)} onToggleTheme={handleToggleTheme} onNavigate={destination=>{
            const item=MORE_NAVIGATION_ITEMS.find(item=>item.id===destination);
            if(item && 'path' in item)handleNavigate(item.path);
          }}/>
        </nav>
        <div className="story-workspace-narrow-more-page__account">
          <span>{displayName}</span><button type="button" onClick={()=>void logout()}>Logout</button>
          {authError?<p role="alert">{authError}</p>:null}
        </div>
      </Modal>
    </div>
  );
}
