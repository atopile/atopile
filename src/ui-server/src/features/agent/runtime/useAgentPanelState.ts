import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import type { AgentMessage } from '../state/types';

export function useAgentPanelState(messages: AgentMessage[]) {
  const minimizedDockHeight = 54;
  const defaultDockHeight = useMemo(() => {
    if (typeof window === 'undefined') return 460;
    const maxHeight = Math.floor(window.innerHeight * 0.78);
    return Math.max(320, Math.min(520, maxHeight));
  }, []);

  const [isChatsPanelOpen, setIsChatsPanelOpen] = useState(false);
  const [dockHeight, setDockHeight] = useState<number>(defaultDockHeight);
  const [isMinimized, setIsMinimized] = useState(false);
  const [changesExpanded, setChangesExpanded] = useState(false);
  const [expandedTraceGroups, setExpandedTraceGroups] = useState<Set<string>>(new Set());
  const [expandedTraceKeys, setExpandedTraceKeys] = useState<Set<string>>(new Set());
  const [resizingDock, setResizingDock] = useState(false);

  const messagesRef = useRef<HTMLDivElement | null>(null);
  const chatsPanelRef = useRef<HTMLDivElement | null>(null);
  const chatsPanelToggleRef = useRef<HTMLButtonElement | null>(null);
  const resizeStartRef = useRef<{ y: number; height: number } | null>(null);

  useEffect(() => {
    const element = messagesRef.current;
    if (!element) return;
    element.scrollTop = element.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const raw = window.sessionStorage.getItem('atopile.agentChatDockHeight');
    if (!raw) return;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return;
    const maxHeight = Math.max(260, Math.floor(window.innerHeight * 0.88));
    setDockHeight(Math.max(280, Math.min(parsed, maxHeight)));
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setIsMinimized(window.sessionStorage.getItem('atopile.agentChatMinimized') === '1');
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.sessionStorage.setItem('atopile.agentChatDockHeight', String(Math.round(dockHeight)));
  }, [dockHeight]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.sessionStorage.setItem('atopile.agentChatMinimized', isMinimized ? '1' : '0');
  }, [isMinimized]);

  useEffect(() => {
    if (!isChatsPanelOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (chatsPanelRef.current?.contains(target)) return;
      if (chatsPanelToggleRef.current?.contains(target)) return;
      setIsChatsPanelOpen(false);
    };
    window.addEventListener('mousedown', onPointerDown);
    return () => window.removeEventListener('mousedown', onPointerDown);
  }, [isChatsPanelOpen]);

  useEffect(() => {
    if (!resizingDock) return;
    const onMouseMove = (event: MouseEvent) => {
      const start = resizeStartRef.current;
      if (!start) return;
      const delta = start.y - event.clientY;
      const maxHeight = Math.max(300, Math.floor(window.innerHeight * 0.88));
      setDockHeight(Math.max(280, Math.min(start.height + delta, maxHeight)));
    };
    const onMouseUp = () => {
      setResizingDock(false);
      resizeStartRef.current = null;
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [resizingDock]);

  const toggleTraceGroupExpanded = useCallback((messageId: string) => {
    setExpandedTraceGroups((previous) => {
      const next = new Set(previous);
      if (next.has(messageId)) next.delete(messageId);
      else next.add(messageId);
      return next;
    });
  }, []);

  const toggleTraceExpanded = useCallback((traceKey: string) => {
    setExpandedTraceKeys((previous) => {
      const next = new Set(previous);
      if (next.has(traceKey)) next.delete(traceKey);
      else next.add(traceKey);
      return next;
    });
  }, []);

  const toggleMinimized = useCallback(() => {
    setIsMinimized((current) => !current);
  }, []);

  const resetTransientPanelState = useCallback(() => {
    setChangesExpanded(false);
    setExpandedTraceGroups(new Set());
    setExpandedTraceKeys(new Set());
  }, []);

  const startResize = useCallback((event: ReactMouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    resizeStartRef.current = { y: event.clientY, height: dockHeight };
    setResizingDock(true);
  }, [dockHeight]);

  return {
    minimizedDockHeight,
    messagesRef,
    chatsPanelRef,
    chatsPanelToggleRef,
    isChatsPanelOpen,
    setIsChatsPanelOpen,
    dockHeight,
    isMinimized,
    changesExpanded,
    setChangesExpanded,
    resetTransientPanelState,
    expandedTraceGroups,
    expandedTraceKeys,
    resizingDock,
    toggleTraceGroupExpanded,
    toggleTraceExpanded,
    toggleMinimized,
    startResize,
  };
}
