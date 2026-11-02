// [Input] Original saved report, section intent and presentation selection.
// [Output] The same available sections, selected result and previous/next behavior for Web/native readers.
// [Pos] Presentation-only state extracted from ReflectionBlogPage; no HTTP or task ownership.
// [Sync] 2026-10-29: share existing result navigation; Web keeps focus/scroll and native keeps platform accessibility.
import {useEffect,useState} from 'react';
import type {ReflectionSectionKey as SectionKey,ReflectionResult} from '../api/reflectionsApi';
import type {AnalysisReport} from '../components/reflectionHistory';
export default function useReflectionReport(report:AnalysisReport,initialSection?:SectionKey|null){
  const blogSections: { key: SectionKey; icon: string; items: ReflectionResult[]; kind: 'echo' | 'trait' | 'pattern' }[] = [
    ...(report.echoes.length > 0 ? [{ key: 'echoes' as SectionKey, icon: '🔄', items: report.echoes, kind: 'echo' as const }] : []),
    ...(report.traits.length > 0 ? [{ key: 'traits' as SectionKey, icon: '⭐', items: report.traits, kind: 'trait' as const }] : []),
    ...(report.patterns.length > 0 ? [{ key: 'patterns' as SectionKey, icon: '🌀', items: report.patterns, kind: 'pattern' as const }] : []),
  ];

  const firstKey = (blogSections[0]?.key ?? 'echoes') as SectionKey;
  const [activeSection, setActiveSection] = useState<SectionKey>(firstKey);
  const [selectedItemIdx, setSelectedItemIdx] = useState<number | null>(null);

  useEffect(()=>{if(initialSection&&report[initialSection].length>0){setActiveSection(initialSection);setSelectedItemIdx(null);}},[initialSection,report]);
  const activeSectionObj = blogSections.find(s => s.key === activeSection) ?? blogSections[0];
  const activeItems = activeSectionObj?.items ?? [];
  const selectedItem = selectedItemIdx !== null ? (activeItems[selectedItemIdx] ?? null) : null;

  const handleSectionChange = (key: SectionKey) => { setActiveSection(key); setSelectedItemIdx(null); };
  const goToPrev = () => { if (selectedItemIdx !== null && selectedItemIdx > 0) setSelectedItemIdx(selectedItemIdx - 1); };
  const goToNext = () => { if (selectedItemIdx !== null && selectedItemIdx < activeItems.length - 1) setSelectedItemIdx(selectedItemIdx + 1); };
  const cfill = (c?: string) => c === 'high' ? 5 : c === 'low' ? 1 : 3;


  return {blogSections,activeSection,selectedItemIdx,setSelectedItemIdx,activeSectionObj,activeItems,selectedItem,handleSectionChange,goToPrev,goToNext,cfill};
}
