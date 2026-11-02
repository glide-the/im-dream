// [Input] Original Timeline session/picture/history reads and concrete platform storage/scroll callbacks.
// [Output] One date range, report cursor, image and comment state shared by Web/native.
// [Pos] State extracted from CollectionsView; each platform retains its own scroll container and controls.
// [Sync] 2026-10-29: retain original ranges, report ordering and read-only historical picture behavior.
import {useState,useEffect,useMemo,useCallback,useRef} from 'react';
import type {Commentor,EditorState,TextCell} from '../engine/EditorEngine';
import {getAnalysisHistory,listSessions,getDailyPictures,getSessionsBatch,getDailyPictureFull,type AnalysisHistoryCursor} from '../api/voiceApi';
import {appendHistoryReports,historyReportForReading,type AnalysisReport} from '../components/reflectionHistory';
import {STORAGE_KEYS} from '../constants/storageKeys';
import {extractFirstLine} from '../utils/calendarStorage';
import {getLocalDayKey} from '../utils/timezone';
import {addDays,startOfDay,buildDayRange,getLocalDateString,formatDate,INITIAL_PAST_DAYS,CHUNK_SIZE,MAX_PAST_DAYS,type TimelineDay,type TimelinePicture,type TimelineEntryData,type SessionSummary} from '../components/timelinePresentation';
export type TimelineRow={key:string;date:string;day?:TimelineDay;report?:AnalysisReport;reportIndex?:number};
const browserStorage={getItem:(key:string)=>localStorage.getItem(key)};
interface Options {authenticated:boolean;timezone:string;dateLocale:string;pendingInitialScroll:boolean;setPendingInitialScroll:(value:boolean)=>void;rememberScroll:()=>void;transport?:typeof fetch;historyApi?:typeof getAnalysisHistory;storage?:{getItem:(key:string)=>string|null}}
export default function useTimeline(options:Options){
 const {authenticated:isAuthenticated,timezone,dateLocale,pendingInitialScroll,setPendingInitialScroll,rememberScroll}=options;
 const owner=useRef({transport:options.transport??fetch,historyApi:options.historyApi??getAnalysisHistory,storage:options.storage??browserStorage});
 const {transport,historyApi,storage:localStorage}=owner.current;
 const rememberScrollRef=useRef(rememberScroll);rememberScrollRef.current=rememberScroll;
  const [days, setDays] = useState<TimelineDay[]>([]);
  const [sessionSummaries, setSessionSummaries] = useState<Map<string, SessionSummary>>(new Map());
  const [datesWithSessions, setDatesWithSessions] = useState<Set<string>>(new Set());
  const [allCommentsByDate, setAllCommentsByDate] = useState<Map<string, Commentor[]>>(new Map());
  const [textByDate, setTextByDate] = useState<Map<string, string>>(new Map());
  const [firstLineByDate, setFirstLineByDate] = useState<Map<string, string>>(new Map());
  const [picturesByDate, setPicturesByDate] = useState<Map<string, TimelinePicture>>(new Map());
  const [viewingImage, setViewingImage] = useState<{ base64: string; full_base64?: string; prompt: string; date: string; } | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingCommentsForDate, setLoadingCommentsForDate] = useState<string | null>(null);
  const [loadingPast, setLoadingPast] = useState(false);
  const [hasMorePast, setHasMorePast] = useState(true);
  const loadedRangesRef = useRef<Set<string>>(new Set());
  const [analysisReports, setAnalysisReports] = useState<AnalysisReport[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState(false);
  const [hasMoreAnalyses, setHasMoreAnalyses] = useState(false);
  const historyCursorRef = useRef<AnalysisHistoryCursor | null>(null);
  const historyBusyRef = useRef(false);
  const historyControllerRef = useRef<AbortController | null>(null);
  const loadAnalysisHistory = useCallback(async (reset = false) => {
    if (!isAuthenticated || historyBusyRef.current) return;
    historyBusyRef.current = true;
    const controller = new AbortController();
    historyControllerRef.current = controller;
    setHistoryLoading(true); setHistoryError(false);
    try {
      const page = await historyApi({ before: reset ? null : historyCursorRef.current, signal: controller.signal });
      if (controller.signal.aborted) return;
      if (!reset) rememberScrollRef.current();
      const reports = page.reports.map(historyReportForReading);
      setAnalysisReports(previous => reset ? appendHistoryReports([], reports) : appendHistoryReports(previous, reports));
      historyCursorRef.current = page.next_cursor;
      setHasMoreAnalyses(page.next_cursor !== null);
    } catch {
      if (!controller.signal.aborted) setHistoryError(true);
    } finally {
      if (!controller.signal.aborted) { historyBusyRef.current = false; setHistoryLoading(false); }
    }
  }, [isAuthenticated]);

  useEffect(() => {
    historyControllerRef.current?.abort();
    historyBusyRef.current = false;
    historyCursorRef.current = null;
    setAnalysisReports([]); setHasMoreAnalyses(false); setHistoryError(false);
    if (isAuthenticated) { void loadAnalysisHistory(true); }
    else setHistoryLoading(false);
    return () => { historyControllerRef.current?.abort(); historyBusyRef.current = false; };
  }, [isAuthenticated, timezone, loadAnalysisHistory]);

  const mergeSessions = useCallback((sessions: SessionSummary[]) => {
    setSessionSummaries(prev => {
      const next = new Map(prev);
      sessions.forEach((s) => next.set(s.id, s));
      return next;
    });
    setDatesWithSessions(prev => {
      const next = new Set(prev);
      sessions.forEach(s => {
        if (s.date_key) next.add(s.date_key);
      });
      return next;
    });
    setFirstLineByDate(prev => {
      const next = new Map(prev);
      sessions.forEach(s => {
        if (s.date_key && (s.first_line || s.name) && !next.has(s.date_key)) {
          next.set(s.date_key, s.first_line || s.name || 'Untitled');
        }
      });
      return next;
    });
  }, []);

  const mergePictures = useCallback((pictures: TimelinePicture[]) => {
    setPicturesByDate(prev => {
      const next = new Map(prev);
      pictures.forEach((p) => {
        next.set(p.date, {
          date: p.date,
          base64: p.base64,
          prompt: p.prompt || ''
        });
      });
      return next;
    });
  }, []);

  const loadRange = useCallback(async (rangeStart: Date, rangeEnd: Date) => {
    if (!isAuthenticated) return;
    const startKey = getLocalDateString(rangeStart);
    const endKey = getLocalDateString(rangeEnd);
    const cacheKey = `${startKey}|${endKey}|${timezone}`;
    if (loadedRangesRef.current.has(cacheKey)) return;
    loadedRangesRef.current.add(cacheKey);

    try {
      const [sessions, pictures] = await Promise.all([
        listSessions(timezone, { startDate: startKey, endDate: endKey }, transport),
        getDailyPictures(CHUNK_SIZE * 2, { startDate: startKey, endDate: endKey }, transport)
      ]);
      mergeSessions(sessions);
      mergePictures(pictures);
    } catch (error) {
      loadedRangesRef.current.delete(cacheKey);
      console.error('Failed to load range:', error);
    }
  }, [isAuthenticated, mergePictures, mergeSessions, timezone]);

  useEffect(() => {
    let cancelled = false;
    const today = new Date();
    const start = addDays(today, -INITIAL_PAST_DAYS);
    const end = today;

    setInitialLoading(true);
    setLoadingPast(false);
    setHasMorePast(true);
    setPendingInitialScroll(true);
    setDays(buildDayRange(start, end));
    setSessionSummaries(new Map());
    setDatesWithSessions(new Set());
    setAllCommentsByDate(new Map());
    setTextByDate(new Map());
    setFirstLineByDate(new Map());
    setPicturesByDate(new Map());
    loadedRangesRef.current.clear();

    const run = async () => {
      if (isAuthenticated) {
        await loadRange(start, end);
      } else {
        const savedState = localStorage.getItem(STORAGE_KEYS.EDITOR_STATE);
        if (savedState) {
          try {
            const state = JSON.parse(savedState) as EditorState;
            const todayKey = formatDate(new Date(), dateLocale);
            const comments = state.commentors?.filter((c: Commentor) => c.appliedAt) || [];
            if (comments.length > 0) {
              setAllCommentsByDate(new Map([[todayKey, comments]]));
            }

            const guestTextMap = new Map<string, string>();
            const guestFirstLineMap = new Map<string, string>();
            if (state.cells) {
              const dateKey = state.createdAt || getLocalDateString();
              const combined = state.cells
                .filter((cell): cell is TextCell => cell.type === 'text')
                .map((cell) => cell.content)
                .join(' ')
                .trim();

              if (combined) {
                guestTextMap.set(dateKey, combined);
                guestFirstLineMap.set(dateKey, extractFirstLine(state));
              }
            }
            setTextByDate(guestTextMap);
            setFirstLineByDate(guestFirstLineMap);
            setDatesWithSessions(new Set(Array.from(guestTextMap.keys())));
          } catch (error) {
            console.error('Failed to load guest state:', error);
          }
        }

        const savedPictures = localStorage.getItem(STORAGE_KEYS.DAILY_PICTURES);
        if (savedPictures) {
          try {
            const parsed = JSON.parse(savedPictures);
            mergePictures(parsed);
          } catch (error) {
            console.error('Failed to load pictures:', error);
          }
        }
      }

      if (!cancelled) {
        setInitialLoading(false);
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, timezone, dateLocale, mergePictures, loadRange]);

  const loadPastChunk = useCallback(async () => {
    if (initialLoading || pendingInitialScroll || loadingPast || historyBusyRef.current || historyError || (!hasMorePast && !hasMoreAnalyses) || days.length === 0) return;
    setLoadingPast(true);
    if (hasMoreAnalyses) await loadAnalysisHistory();
    if (!hasMorePast) { setLoadingPast(false); return; }
    const firstDay = days[0];
    const firstDate = startOfDay(new Date(firstDay.date));
    const desiredStart = addDays(firstDate, -CHUNK_SIZE);
    const minDate = addDays(startOfDay(new Date()), -MAX_PAST_DAYS);
    const actualStart = desiredStart < minDate ? minDate : desiredStart;
    const actualEnd = addDays(firstDate, -1);

    if (actualEnd.getTime() < actualStart.getTime()) {
      setHasMorePast(false);
      setLoadingPast(false);
      return;
    }

    const newDays = buildDayRange(actualStart, actualEnd);
    rememberScroll();

    setDays(prev => {
      const existing = new Set(prev.map(d => d.date));
      const merged = [...newDays.filter(d => !existing.has(d.date)), ...prev];
      return merged;
    });

    if (isAuthenticated) {
      await loadRange(actualStart, actualEnd);
    }

    const reachedMin = actualStart.getTime() <= minDate.getTime();
    setHasMorePast(!reachedMin);
    setLoadingPast(false);
  }, [days, hasMorePast, hasMoreAnalyses, historyError, initialLoading, pendingInitialScroll, isAuthenticated, loadRange, loadAnalysisHistory, loadingPast, rememberScroll]);

  // @@@ Group items by date
  const timelineByDate = useMemo(() => {
    const map = new Map<string, TimelineEntryData>();

    datesWithSessions.forEach(date => {
      if (!map.has(date)) {
        map.set(date, { comments: [] });
      }
    });

    allCommentsByDate.forEach((comments, date) => {
      const entry = map.get(date) || { comments: [] };
      entry.comments = comments;
      map.set(date, entry);
    });

    picturesByDate.forEach((pic, date) => {
      const entry = map.get(date) || { comments: [] };
      entry.picture = pic;
      map.set(date, entry);
    });

    return map;
  }, [datesWithSessions, allCommentsByDate, picturesByDate]);

  const timelineRows = useMemo(() => {
    const rows: TimelineRow[] = days.map(day => ({ key: `day:${day.date}`, date: day.date, day }));
    analysisReports.forEach((report, reportIndex) => {
      const date = getLocalDayKey(report.createdAt ?? report.timestamp, timezone);
      if (date) rows.push({ key: `analysis:${report.id}`, date, report, reportIndex });
    });
    return rows.sort((a, b) => a.date.localeCompare(b.date)
      || (a.report && b.report ? b.reportIndex! - a.reportIndex! : a.report ? 1 : b.report ? -1 : 0));
  }, [days, analysisReports, timezone]);
  // @@@ Reload comments for a specific date from backend
  const reloadCommentsForDate = async (dateStr: string) => {
    setLoadingCommentsForDate(dateStr);

    try {
      if (isAuthenticated) {
        const sessionsForDate = Array.from(sessionSummaries.values()).filter(session => session.date_key === dateStr);

        if (sessionsForDate.length === 0) {
          setAllCommentsByDate(prev => {
            const next = new Map(prev);
            next.set(dateStr, []);
            return next;
          });
          return;
        }

        const batch = await getSessionsBatch(sessionsForDate.map(s => s.id), transport);
        const commentsForDate: Commentor[] = [];

        batch.forEach((session) => {
          const comments = session.editor_state?.commentors || [];

          comments.filter((c: Commentor) => c.appliedAt).forEach((comment: Commentor) => {
            const rawTs = comment.appliedAt || comment.computedAt;
            const commentDate = getLocalDayKey(rawTs, timezone)
              || getLocalDateString(new Date(rawTs));
            if (commentDate === dateStr) {
              commentsForDate.push(comment);
            }
          });
        });

        setAllCommentsByDate(prev => {
          const next = new Map(prev);
          next.set(dateStr, commentsForDate);
          return next;
        });
      }
    } catch (error) {
      console.error('Failed to reload comments for date:', error);
    } finally {
      setLoadingCommentsForDate(null);
    }
  };

  const handleImageClick = async (picture: TimelinePicture) => {
    const stored = picturesByDate.get(picture.date) || picture;
    setViewingImage({ ...stored });

    if (!stored.full_base64 && isAuthenticated) {
      try {
        const fullImage = await getDailyPictureFull(stored.date, transport);

        const updatedPicture = { ...stored, full_base64: fullImage };
        setViewingImage(updatedPicture);

        setPicturesByDate(prev => {
          const next = new Map(prev);
          next.set(stored.date, updatedPicture);
          return next;
        });
      } catch (error) {
        console.error('Failed to load full image:', error);
      }
    }

    await reloadCommentsForDate(stored.date);
  };


 return {days,initialLoading,loadingPast,hasMorePast,historyLoading,historyError,hasMoreAnalyses,analysisReports,timelineRows,timelineByDate,textByDate,firstLineByDate,allCommentsByDate,loadingCommentsForDate,viewingImage,setViewingImage,loadAnalysisHistory,loadPastChunk,handleImageClick};
}
