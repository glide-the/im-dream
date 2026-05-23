import {
  createContext,
  useContext,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react';

interface WorkspaceContextValue {
  activeSessionId: string | null;
  setActiveSessionId: Dispatch<SetStateAction<string | null>>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const value = useMemo(
    () => ({ activeSessionId, setActiveSessionId }),
    [activeSessionId],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspaceSession() {
  const context = useContext(WorkspaceContext);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  return context ?? { activeSessionId, setActiveSessionId };
}
