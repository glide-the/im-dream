'use client';
// [Input] Saved page projection and the existing resolved application theme.
// [Output] react-notion-x body with shared code/math extensions and recoverable image feedback.
// [Pos] On-demand browser document; no Notion client, resource discovery or page re-fetch.
// [Sync] 2026-11-18: register host extensions and keep page chrome in the existing Modal.
import {useEffect, useMemo, useState, type AnchorHTMLAttributes, type ImgHTMLAttributes} from 'react';
import {useTranslation} from 'react-i18next';
import {NotionRenderer} from 'react-notion-x';
import {Code} from 'react-notion-x/third-party/code';
import type {CodeBlock, EquationBlock} from 'notion-types';
import {getTheme, onThemeChange} from '../../utils/theme';
import ChatMath from './ChatMath';
import MermaidBlock from './MermaidBlock';
import {createNotionRecordMap, notionPreviewUrl} from './notionRecordMapAdapter';
import type {NotionWorkspacePreviewData} from './notionPreviewProjection';

function NotionLink({href, children, ...props}: AnchorHTMLAttributes<HTMLAnchorElement>) {
  const safe = notionPreviewUrl(href);
  return safe ? <a {...props} href={safe} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">{children}</a> : <span>{children}</span>;
}
function NotionCode({block}: {block: CodeBlock}) {
  const language = block.properties.language?.[0]?.[0]?.toLowerCase();
  return language === 'mermaid' ? <MermaidBlock chart={block.properties.title.map(piece => piece[0]).join('')}/> : <Code block={block} defaultLanguage="plain text"/>;
}
function NotionEquation({block, math, inline = false}: {block: EquationBlock; math?: string; inline?: boolean}) {
  const value = math || block.properties?.title.map(piece => piece[0]).join('') || '';
  return <ChatMath source={inline ? `\\(${value}\\)` : `$$${value}$$`} display={!inline} closed/>;
}
function NotionImage({src, alt, style, className, onLoad}: Pick<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'alt' | 'style' | 'className' | 'onLoad'>) {
  const {t} = useTranslation();
  const [failed, setFailed] = useState(false), [attempt, setAttempt] = useState(0);
  const safe = notionPreviewUrl(typeof src === 'string' ? src : undefined);
  return <span className="notion-preview__image">
    {failed || !safe ? <span role="alert" className="notion-preview__media-error">{t('chat.notionPreview.imageFailed')}
      {safe ? <><button type="button" onClick={() => {setFailed(false); setAttempt(value => value + 1);}}>{t('chat.notionPreview.retry')}</button><NotionLink href={safe}>{t('chat.notionPreview.openOriginal')}</NotionLink></> : null}
    </span> : <img key={attempt} src={safe} alt={alt || ''} style={style} className={className} loading="lazy" decoding="async" referrerPolicy="no-referrer" onLoad={onLoad} onError={() => setFailed(true)}/>}
  </span>;
}
const components = {Code: NotionCode, Equation: NotionEquation, Image: NotionImage, Link: NotionLink, PageLink: NotionLink};

export default function NotionPageDocument({data}: {data: NotionWorkspacePreviewData}) {
  const [theme, setTheme] = useState(getTheme);
  useEffect(() => onThemeChange(next => setTheme(next)), []);
  const recordMap = useMemo(() => createNotionRecordMap(data), [data]);
  return <NotionRenderer recordMap={recordMap} rootPageId={data.pageId} fullPage={false} darkMode={theme === 'dark'}
    components={components} mapImageUrl={notionPreviewUrl} forceCustomImages isImageZoomable={false} previewImages={false}
    showTableOfContents={false} className="notion-preview__document"/>;
}
