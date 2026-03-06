import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import { agentApi } from '../../api/agent';
import { api } from '../../api/client';
import { postMessage } from '../../api/vscodeApi';
import { useStore } from '../../store';
import {
  createChatId,
  DEFAULT_CHAT_TITLE,
  deriveChatTitle,
  shortProjectName,
} from '../AgentChatPanel.helpers';
import {
  ACTIVE_CHAT_STORAGE_KEY,
  CHAT_SNAPSHOTS_STORAGE_KEY,
  parseStoredActiveChats,
  parseStoredSnapshots,
  persistAgentState,
} from '../state/persistence';
import type { AgentChatSnapshot, AgentMessage } from '../state/types';
import type { FileTreeNode } from '../../types/build';

interface SessionDeps {
  projectRoot: string | null;
  sessionId: string | null;
  setSessionId: (value: string | null) => void;
  messages: AgentMessage[];
  setMessages: Dispatch<SetStateAction<AgentMessage[]>>;
  input: string;
  setInput: (value: string) => void;
  isSessionLoading: boolean;
  setIsSessionLoading: (value: boolean) => void;
  isSending: boolean;
  setIsSending: (value: boolean) => void;
  isStopping: boolean;
  setIsStopping: (value: boolean) => void;
  activeRunId: string | null;
  setActiveRunId: (value: string | null) => void;
  error: string | null;
  setError: (value: string | null) => void;
  activityLabel: string;
  setActivityLabel: (value: string) => void;
  activityElapsedSeconds: number;
  setActivityElapsedSeconds: (value: number) => void;
  resetChatUiState: () => void;
}

export function useAgentSessionState({
  projectRoot,
  sessionId,
  setSessionId,
  messages,
  setMessages,
  input,
  setInput,
  isSessionLoading,
  setIsSessionLoading,
  isSending,
  setIsSending,
  isStopping,
  setIsStopping,
  activeRunId,
  setActiveRunId,
  error,
  setError,
  activityLabel,
  setActivityLabel,
  activityElapsedSeconds,
  setActivityElapsedSeconds,
  resetChatUiState,
}: SessionDeps) {
  const [activeChatId, setActiveChatId] = useState<string | null>(null);

  const activityStartedAtRef = useRef<number | null>(null);
  const chatSnapshotsRef = useRef<AgentChatSnapshot[]>([]);
  const activeChatIdRef = useRef<string | null>(null);
  const loadedChatIdRef = useRef<string | null>(null);

  const projectModules = useStore((state) => (projectRoot ? state.projectModules[projectRoot] ?? [] : []));
  const projectFileNodes = useStore((state) => (projectRoot ? state.projectFiles[projectRoot] ?? [] : []));
  const setProjectModules = useStore((state) => state.setProjectModules);
  const setProjectFiles = useStore((state) => state.setProjectFiles);
  const setLoadingModules = useStore((state) => state.setLoadingModules);
  const setLoadingFiles = useStore((state) => state.setLoadingFiles);
  const chatSnapshots = useStore((state) => state.agentState.snapshots);
  const activeChatByProject = useStore((state) => state.agentState.activeChatByProject);
  const isSnapshotsHydrated = useStore((state) => state.agentState.isHydrated);
  const hydrateAgentState = useStore((state) => state.hydrateAgentState);
  const upsertAgentSnapshot = useStore((state) => state.upsertAgentSnapshot);
  const updateAgentSnapshotInStore = useStore((state) => state.updateAgentSnapshot);
  const setAgentActiveChat = useStore((state) => state.setAgentActiveChat);

  const projectChats = useMemo(() => (
    chatSnapshots
      .filter((chat) => projectRoot !== null && chat.projectRoot === projectRoot)
      .sort((left, right) => right.updatedAt - left.updatedAt)
  ), [chatSnapshots, projectRoot]);

  const activeChatSnapshot = useMemo(() => {
    if (!activeChatId || !projectRoot) return null;
    return chatSnapshots.find((chat) => chat.id === activeChatId && chat.projectRoot === projectRoot) ?? null;
  }, [activeChatId, chatSnapshots, projectRoot]);

  const isReady = Boolean(projectRoot && sessionId && !isSessionLoading);
  const headerTitle = useMemo(() => shortProjectName(projectRoot), [projectRoot]);
  const activeChatTitle = activeChatSnapshot?.title ?? DEFAULT_CHAT_TITLE;

  useEffect(() => {
    chatSnapshotsRef.current = chatSnapshots;
  }, [chatSnapshots]);

  useEffect(() => {
    activeChatIdRef.current = activeChatId;
  }, [activeChatId]);

  useEffect(() => {
    if (!isSnapshotsHydrated || !projectRoot || !activeChatId) return;
    const activeSnapshot = chatSnapshotsRef.current.find((chat) => chat.id === activeChatId);
    if (!activeSnapshot || activeSnapshot.projectRoot !== projectRoot) return;
    if (activeChatByProject[projectRoot] === activeChatId) return;
    setAgentActiveChat(projectRoot, activeChatId);
  }, [activeChatByProject, activeChatId, isSnapshotsHydrated, projectRoot, setAgentActiveChat]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      hydrateAgentState({ isHydrated: true });
      return;
    }
    hydrateAgentState({
      snapshots: parseStoredSnapshots(window.localStorage.getItem(CHAT_SNAPSHOTS_STORAGE_KEY)),
      activeChatByProject: parseStoredActiveChats(window.localStorage.getItem(ACTIVE_CHAT_STORAGE_KEY)),
      isHydrated: true,
    });
  }, [hydrateAgentState]);

  useEffect(() => {
    if (!isSnapshotsHydrated) return;
    persistAgentState(chatSnapshots, activeChatByProject);
  }, [activeChatByProject, chatSnapshots, isSnapshotsHydrated]);

  const loadSnapshotIntoView = useCallback((snapshot: AgentChatSnapshot) => {
    setSessionId(snapshot.sessionId);
    setMessages(snapshot.messages);
    setInput(snapshot.input);
    setError(snapshot.error);
    setActivityLabel(snapshot.activityLabel || (snapshot.sessionId ? 'Ready' : 'Idle'));
    setIsSessionLoading(snapshot.isSessionLoading);
    setIsSending(snapshot.isSending);
    setIsStopping(snapshot.isStopping);
    setActiveRunId(snapshot.activeRunId);
    setActivityElapsedSeconds(snapshot.activityElapsedSeconds);
    resetChatUiState();
    if (snapshot.isSending || snapshot.isStopping) {
      activityStartedAtRef.current = Date.now() - (snapshot.activityElapsedSeconds * 1000);
    }
  }, [resetChatUiState, setActivityElapsedSeconds, setActivityLabel, setActiveRunId, setError, setInput, setIsSending, setIsSessionLoading, setIsStopping, setMessages, setSessionId]);

  const upsertSnapshot = useCallback((snapshot: AgentChatSnapshot) => {
    upsertAgentSnapshot(snapshot);
  }, [upsertAgentSnapshot]);

  const updateChatSnapshot = useCallback((chatId: string, updater: (chat: AgentChatSnapshot) => AgentChatSnapshot) => {
    updateAgentSnapshotInStore(chatId, updater);
  }, [updateAgentSnapshotInStore]);

  const startChatSession = useCallback(async (chatId: string, root: string) => {
    if (activeChatIdRef.current === chatId) {
      setIsSessionLoading(true);
      setError(null);
      setActivityLabel('Starting');
    }
    try {
      const response = await agentApi.createSession(root);
      const readyMessage: AgentMessage = {
        id: `${chatId}-welcome-${response.sessionId}`,
        role: 'system',
        content: `Session ready for ${shortProjectName(root)}. Ask me to inspect, edit, build, or install.`,
      };
      if (activeChatIdRef.current === chatId) {
        setSessionId(response.sessionId);
        setMessages([readyMessage]);
        setActivityLabel('Ready');
        setIsSessionLoading(false);
        setIsSending(false);
        setIsStopping(false);
        setActiveRunId(null);
        setActivityElapsedSeconds(0);
      }
      upsertSnapshot({
        id: chatId,
        projectRoot: root,
        title: DEFAULT_CHAT_TITLE,
        sessionId: response.sessionId,
        isSessionLoading: false,
        isSending: false,
        isStopping: false,
        activeRunId: null,
        pendingRunId: null,
        pendingAssistantId: null,
        cancelRequested: false,
        activityElapsedSeconds: 0,
        messages: [readyMessage],
        packageWorkers: [],
        input: '',
        error: null,
        activityLabel: 'Ready',
        createdAt: Date.now(),
        updatedAt: Date.now(),
      });
    } catch (sessionError: unknown) {
      const message = sessionError instanceof Error ? sessionError.message : 'Failed to start session.';
      const errorMessage: AgentMessage = {
        id: `${chatId}-session-error`,
        role: 'system',
        content: `Unable to start agent: ${message}`,
      };
      if (activeChatIdRef.current === chatId) {
        setSessionId(null);
        setMessages([errorMessage]);
        setError(message);
        setActivityLabel('Idle');
        setIsSessionLoading(false);
        setIsSending(false);
        setIsStopping(false);
        setActiveRunId(null);
        setActivityElapsedSeconds(0);
      }
      upsertSnapshot({
        id: chatId,
        projectRoot: root,
        title: DEFAULT_CHAT_TITLE,
        sessionId: null,
        isSessionLoading: false,
        isSending: false,
        isStopping: false,
        activeRunId: null,
        pendingRunId: null,
        pendingAssistantId: null,
        cancelRequested: false,
        activityElapsedSeconds: 0,
        messages: [errorMessage],
        packageWorkers: [],
        input: '',
        error: message,
        activityLabel: 'Idle',
        createdAt: Date.now(),
        updatedAt: Date.now(),
      });
    }
  }, [setActivityElapsedSeconds, setActivityLabel, setActiveRunId, setError, setIsSending, setIsSessionLoading, setIsStopping, setMessages, setSessionId, upsertSnapshot]);

  const createAndActivateChat = useCallback((root: string) => {
    const chatId = createChatId();
    const bootMessage: AgentMessage = {
      id: `${chatId}-boot`,
      role: 'system',
      content: `Starting session for ${shortProjectName(root)}...`,
    };
    setActiveChatId(chatId);
    setSessionId(null);
    setMessages([bootMessage]);
    setInput('');
    setError(null);
    setActivityLabel('Starting');
    setIsSessionLoading(true);
    resetChatUiState();
    upsertSnapshot({
      id: chatId,
      projectRoot: root,
      title: DEFAULT_CHAT_TITLE,
      sessionId: null,
      isSessionLoading: true,
      isSending: false,
      isStopping: false,
      activeRunId: null,
      pendingRunId: null,
      pendingAssistantId: null,
      cancelRequested: false,
      activityElapsedSeconds: 0,
      messages: [bootMessage],
      packageWorkers: [],
      input: '',
      error: null,
      activityLabel: 'Starting',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    void startChatSession(chatId, root);
  }, [resetChatUiState, setActivityLabel, setError, setInput, setIsSessionLoading, setMessages, setSessionId, startChatSession, upsertSnapshot]);

  const activateChat = useCallback((chatId: string) => {
    const snapshot = chatSnapshotsRef.current.find((chat) => chat.id === chatId);
    if (!snapshot) return;
    setActiveChatId(chatId);
    loadedChatIdRef.current = chatId;
    loadSnapshotIntoView(snapshot);
  }, [loadSnapshotIntoView]);

  useEffect(() => {
    if (!activeChatId || !projectRoot) return;
    const liveSnapshot = chatSnapshotsRef.current.find((chat) => chat.id === activeChatId);
    if (liveSnapshot && liveSnapshot.projectRoot !== projectRoot) return;
    const nextTitle = deriveChatTitle(messages);
    updateAgentSnapshotInStore(activeChatId, (current) => ({
      ...current,
      title: nextTitle,
      sessionId,
      isSessionLoading,
      isSending,
      isStopping,
      activeRunId,
      activityElapsedSeconds,
      messages,
      input,
      error,
      activityLabel,
    }));
  }, [activeChatId, activeRunId, activityElapsedSeconds, activityLabel, error, input, isSending, isSessionLoading, isStopping, messages, projectRoot, sessionId, updateAgentSnapshotInStore]);

  useEffect(() => {
    if (!projectRoot) return;
    if (projectModules.length > 0) return;
    let cancelled = false;
    setLoadingModules(true);
    void api.modules.list(projectRoot)
      .then((result) => {
        if (cancelled) return;
        setProjectModules(projectRoot, result.modules || []);
      })
      .catch(() => {
        if (!cancelled) setLoadingModules(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectModules.length, projectRoot, setLoadingModules, setProjectModules]);

  useEffect(() => {
    if (!projectRoot) return;
    const handleMessage = (event: MessageEvent) => {
      const message = event.data as { type?: string; projectRoot?: string; files?: FileTreeNode[] };
      if (message?.type !== 'filesListed') return;
      if (message.projectRoot !== projectRoot) return;
      setProjectFiles(projectRoot, message.files || []);
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [projectRoot, setProjectFiles]);

  useEffect(() => {
    if (!projectRoot) return;
    if (projectFileNodes.length > 0) return;
    setLoadingFiles(true);
    postMessage({ type: 'listFiles', projectRoot, includeAll: true });
  }, [projectFileNodes.length, projectRoot, setLoadingFiles]);

  useEffect(() => {
    if (isSessionLoading) {
      setActivityLabel('Starting');
      return;
    }
    if (!projectRoot || !sessionId) {
      setActivityLabel('Idle');
      return;
    }
    if (!isSending && !isStopping) {
      setActivityLabel('Ready');
    }
  }, [isSending, isSessionLoading, isStopping, projectRoot, sessionId, setActivityLabel]);

  useEffect(() => {
    if (!(isSending || isStopping)) {
      activityStartedAtRef.current = null;
      setActivityElapsedSeconds(0);
      return;
    }
    if (activityStartedAtRef.current == null) {
      activityStartedAtRef.current = Date.now();
    }
    const updateElapsed = () => {
      const startedAt = activityStartedAtRef.current;
      if (!startedAt) {
        setActivityElapsedSeconds(0);
        return;
      }
      setActivityElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    };
    updateElapsed();
    const timerId = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(timerId);
  }, [isSending, isStopping, setActivityElapsedSeconds]);

  useEffect(() => {
    if (!projectRoot) {
      loadedChatIdRef.current = null;
      setActiveChatId(null);
      setSessionId(null);
      setMessages([{ id: 'agent-empty', role: 'system', content: 'Select a project to start an agent session.' }]);
      setInput('');
      setError(null);
      setActivityLabel('Idle');
      setIsSessionLoading(false);
      setIsSending(false);
      setIsStopping(false);
      setActiveRunId(null);
      setActivityElapsedSeconds(0);
      resetChatUiState();
      return;
    }
    if (!isSnapshotsHydrated) return;

    const chatsForProject = chatSnapshotsRef.current
      .filter((chat) => chat.projectRoot === projectRoot)
      .sort((left, right) => right.updatedAt - left.updatedAt);
    if (chatsForProject.length === 0) {
      createAndActivateChat(projectRoot);
      return;
    }

    const currentChat = activeChatId ? chatsForProject.find((chat) => chat.id === activeChatId) ?? null : null;
    const preferredChatId = activeChatByProject[projectRoot];
    const preferredChat = preferredChatId ? chatsForProject.find((chat) => chat.id === preferredChatId) ?? null : null;
    const target = currentChat ?? preferredChat ?? chatsForProject[0];
    if (activeChatId !== target.id) {
      setActiveChatId(target.id);
    }
    if (loadedChatIdRef.current !== target.id) {
      loadedChatIdRef.current = target.id;
      loadSnapshotIntoView(target);
    }
  }, [activeChatByProject, activeChatId, createAndActivateChat, isSnapshotsHydrated, loadSnapshotIntoView, projectRoot, resetChatUiState, setActivityElapsedSeconds, setActivityLabel, setActiveRunId, setError, setInput, setIsSending, setIsSessionLoading, setIsStopping, setMessages, setSessionId]);

  return {
    activeChatId,
    activeChatSnapshot,
    projectChats,
    isReady,
    headerTitle,
    activeChatTitle,
    chatSnapshotsRef,
    activeChatIdRef,
    activateChat,
    createAndActivateChat,
    updateChatSnapshot,
    setActiveChatId,
    setSessionId,
  };
}
