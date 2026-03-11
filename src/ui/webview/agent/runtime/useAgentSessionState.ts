import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { UiAgentData, UiAgentSessionData } from '../../../shared/generated-types';
import { agentApi } from '../api';
import {
  createChatId,
  DEFAULT_CHAT_TITLE,
  deriveChatTitle,
  shortProjectName,
} from '../AgentChatPanel.helpers';
import type { AgentChatSnapshot, AgentMessage } from '../state/types';

interface SessionDeps {
  agentData: UiAgentData;
  projectRoot: string | null;
  input: string;
  setInput: (value: string) => void;
  resetChatUiState: () => void;
}

function snapshotFromAgentSession(summary: UiAgentSessionData): AgentChatSnapshot {
  const messages = summary.messages as AgentMessage[];
  return {
    id: summary.sessionId,
    projectRoot: summary.projectRoot,
    title: deriveChatTitle(messages) || DEFAULT_CHAT_TITLE,
    sessionId: summary.sessionId,
    isSessionLoading: false,
    isSending: summary.activeRunId != null && summary.activeRunStatus === 'running',
    isStopping: summary.activeRunStopRequested,
    activeRunId: summary.activeRunId,
    runStartedAt: summary.runStartedAt ?? null,
    messages,
    input: '',
    error: summary.error,
    activityLabel: summary.activityLabel || (summary.activeRunId ? 'Working' : 'Ready'),
    createdAt: summary.createdAt,
    updatedAt: summary.updatedAt,
  };
}

function mergeSnapshotFromStore(
  current: AgentChatSnapshot,
  storeSnapshot: AgentChatSnapshot,
): AgentChatSnapshot {
  return {
    ...storeSnapshot,
    input: current.input,
    updatedAt: Math.max(current.updatedAt, storeSnapshot.updatedAt),
  };
}

export function useAgentSessionState({
  agentData,
  projectRoot,
  input,
  setInput,
  resetChatUiState,
}: SessionDeps) {
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [chatSnapshots, setChatSnapshots] = useState<AgentChatSnapshot[]>([]);
  const [activeChatByProject, setActiveChatByProject] = useState<Record<string, string>>({});
  const [isSessionsHydrated, setIsSessionsHydrated] = useState(false);

  const chatSnapshotsRef = useRef<AgentChatSnapshot[]>([]);
  const activeChatIdRef = useRef<string | null>(null);
  const loadedChatIdRef = useRef<string | null>(null);
  const handledMutationAtRef = useRef<number | null>(null);

  const projectChats = useMemo(
    () => chatSnapshots
      .filter((chat) => projectRoot !== null && chat.projectRoot === projectRoot)
      .sort((left, right) => right.updatedAt - left.updatedAt),
    [chatSnapshots, projectRoot],
  );

  const activeChatSnapshot = useMemo(() => {
    if (!activeChatId || !projectRoot) return null;
    return chatSnapshots.find((chat) => chat.id === activeChatId && chat.projectRoot === projectRoot) ?? null;
  }, [activeChatId, chatSnapshots, projectRoot]);

  const isReady = Boolean(projectRoot && activeChatSnapshot?.sessionId && !activeChatSnapshot.isSessionLoading);
  const headerTitle = useMemo(() => shortProjectName(projectRoot), [projectRoot]);
  const activeChatTitle = activeChatSnapshot?.title ?? DEFAULT_CHAT_TITLE;

  useEffect(() => {
    chatSnapshotsRef.current = chatSnapshots;
  }, [chatSnapshots]);

  useEffect(() => {
    activeChatIdRef.current = activeChatId;
  }, [activeChatId]);

  const upsertSnapshot = useCallback((snapshot: AgentChatSnapshot) => {
    setChatSnapshots((previous) => {
      const existingIndex = previous.findIndex((chat) => chat.id === snapshot.id);
      if (existingIndex === -1) {
        return [snapshot, ...previous];
      }
      const next = [...previous];
      next[existingIndex] = {
        ...next[existingIndex],
        ...snapshot,
      };
      return next;
    });
  }, []);

  const updateChatSnapshot = useCallback((chatId: string, updater: (chat: AgentChatSnapshot) => AgentChatSnapshot) => {
    setChatSnapshots((previous) => previous.map((chat) => (
      chat.id === chatId
        ? updater({ ...chat, updatedAt: Date.now() })
        : chat
    )));
  }, []);

  const loadSnapshotIntoView = useCallback((snapshot: AgentChatSnapshot) => {
    setInput(snapshot.input);
    resetChatUiState();
  }, [resetChatUiState, setInput]);

  const startChatSession = useCallback((chatId: string, root: string) => {
    try {
      agentApi.createSession(root);
    } catch (sessionError: unknown) {
      const message = sessionError instanceof Error ? sessionError.message : 'Failed to start session.';
      const errorMessage: AgentMessage = {
        id: `${chatId}-session-error`,
        role: 'system',
        content: `Unable to start agent: ${message}`,
      };
      upsertSnapshot({
        id: chatId,
        projectRoot: root,
        title: DEFAULT_CHAT_TITLE,
        sessionId: null,
        isSessionLoading: false,
        isSending: false,
        isStopping: false,
        activeRunId: null,
        runStartedAt: null,
        messages: [errorMessage],
        input: '',
        error: message,
        activityLabel: 'Idle',
        createdAt: Date.now(),
        updatedAt: Date.now(),
      });
    }
  }, [upsertSnapshot]);

  const createAndActivateChat = useCallback((root: string) => {
    const provisionalChatId = createChatId();
    const bootMessage: AgentMessage = {
      id: `${provisionalChatId}-boot`,
      role: 'system',
      content: `Starting session for ${shortProjectName(root)}...`,
    };
    setActiveChatId(provisionalChatId);
    setActiveChatByProject((previous) => ({ ...previous, [root]: provisionalChatId }));
    setInput('');
    resetChatUiState();
    upsertSnapshot({
      id: provisionalChatId,
      projectRoot: root,
      title: DEFAULT_CHAT_TITLE,
      sessionId: null,
      isSessionLoading: true,
      isSending: false,
      isStopping: false,
      activeRunId: null,
      runStartedAt: null,
      messages: [bootMessage],
      input: '',
      error: null,
      activityLabel: 'Starting',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    startChatSession(provisionalChatId, root);
  }, [resetChatUiState, setInput, startChatSession, upsertSnapshot]);

  const activateChat = useCallback((chatId: string) => {
    const snapshot = chatSnapshotsRef.current.find((chat) => chat.id === chatId);
    if (!snapshot) return;
    setActiveChatId(chatId);
    setActiveChatByProject((previous) => ({ ...previous, [snapshot.projectRoot]: chatId }));
    loadedChatIdRef.current = chatId;
    loadSnapshotIntoView(snapshot);
  }, [loadSnapshotIntoView]);

  useEffect(() => {
    if (!projectRoot) {
      loadedChatIdRef.current = null;
      setIsSessionsHydrated(false);
      setActiveChatId(null);
      setInput('');
      resetChatUiState();
      return;
    }
  }, [projectRoot, resetChatUiState, setInput]);

  useEffect(() => {
    if (!projectRoot) return;
    if (!agentData.loaded) {
      setIsSessionsHydrated(false);
      return;
    }

    const restored = agentData.sessions
      .filter((session) => session.projectRoot === projectRoot)
      .map(snapshotFromAgentSession);

    setChatSnapshots((previous) => {
      const otherProjects = previous.filter((chat) => chat.projectRoot !== projectRoot);
      const existingById = new Map(
        previous
          .filter((chat) => chat.projectRoot === projectRoot)
          .map((chat) => [chat.id, chat] as const),
      );
      const synced = restored.map((snapshot) => {
        const existing = existingById.get(snapshot.id);
        return existing ? mergeSnapshotFromStore(existing, snapshot) : snapshot;
      });
      const provisional = previous.filter((chat) => (
        chat.projectRoot === projectRoot
        && chat.sessionId == null
      ));
      return [...synced, ...provisional, ...otherProjects];
    });
    setIsSessionsHydrated(true);
  }, [agentData, projectRoot]);

  useEffect(() => {
    const mutation = agentData.lastMutation;
    if (!mutation?.updatedAt || handledMutationAtRef.current === mutation.updatedAt) return;
    handledMutationAtRef.current = mutation.updatedAt;

    if (mutation.action !== 'agent.createSession') {
      return;
    }

    if (mutation.error) {
      const provisional = chatSnapshotsRef.current.find((chat) => (
        chat.projectRoot === projectRoot
        && chat.sessionId == null
        && chat.isSessionLoading
      ));
      if (!provisional) return;

      const errorMessage: AgentMessage = {
        id: `${provisional.id}-session-error`,
        role: 'system',
        content: `Unable to start agent: ${mutation.error}`,
      };
      updateChatSnapshot(provisional.id, (chat) => ({
        ...chat,
        isSessionLoading: false,
        messages: [errorMessage],
        error: mutation.error ?? 'Failed to start session.',
        activityLabel: 'Idle',
      }));
      return;
    }

    if (!mutation.sessionId) return;
    const summary = agentData.sessions.find((session) => session.sessionId === mutation.sessionId);
    if (!summary) return;

    const snapshot = snapshotFromAgentSession(summary);
    const provisional = chatSnapshotsRef.current.find((chat) => (
      chat.projectRoot === summary.projectRoot
      && chat.sessionId == null
      && chat.isSessionLoading
    ));
    const nextSnapshot = snapshot;

    setChatSnapshots((previous) => {
      if (!provisional) {
        const existing = previous.find((chat) => chat.id === snapshot.id);
        if (existing) {
          return previous.map((chat) => chat.id === snapshot.id ? mergeSnapshotFromStore(chat, nextSnapshot) : chat);
        }
        return [nextSnapshot, ...previous];
      }
      return previous.map((chat) => chat.id === provisional.id ? nextSnapshot : chat);
    });

    if (activeChatIdRef.current === provisional?.id || activeChatIdRef.current === summary.sessionId) {
      setActiveChatId(summary.sessionId);
      setActiveChatByProject((previous) => ({ ...previous, [summary.projectRoot]: summary.sessionId }));
      loadedChatIdRef.current = summary.sessionId;
      loadSnapshotIntoView(nextSnapshot);
    }
  }, [agentData, loadSnapshotIntoView, projectRoot, updateChatSnapshot]);

  useEffect(() => {
    if (!activeChatId) return;
    updateChatSnapshot(activeChatId, (current) => (
      current.input === input
        ? current
        : { ...current, input }
    ));
  }, [activeChatId, input, updateChatSnapshot]);

  useEffect(() => {
    if (!projectRoot || !isSessionsHydrated) return;
    const chatsForProject = chatSnapshotsRef.current
      .filter((chat) => chat.projectRoot === projectRoot)
      .sort((left, right) => right.updatedAt - left.updatedAt);

    if (chatsForProject.length === 0) {
      createAndActivateChat(projectRoot);
      return;
    }

    const currentChat = activeChatId
      ? chatsForProject.find((chat) => chat.id === activeChatId) ?? null
      : null;
    const preferredChatId = activeChatByProject[projectRoot];
    const preferredChat = preferredChatId
      ? chatsForProject.find((chat) => chat.id === preferredChatId) ?? null
      : null;
    const target = currentChat ?? preferredChat ?? chatsForProject[0];

    if (activeChatId !== target.id) {
      setActiveChatId(target.id);
    }
    if (loadedChatIdRef.current !== target.id) {
      loadedChatIdRef.current = target.id;
      loadSnapshotIntoView(target);
    }
  }, [activeChatByProject, activeChatId, createAndActivateChat, isSessionsHydrated, loadSnapshotIntoView, projectRoot]);

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
  };
}
