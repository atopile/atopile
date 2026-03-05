import { useCallback, useMemo, useRef, useState } from 'react';
import { collectChangedFilesSummary, type AgentChangedFile } from './components/viewHelpers';
import { findLatestBuildStatus } from './runtime/buildStatus';
import { useAgentComposerState } from './runtime/useAgentComposerState';
import { useAgentPanelState } from './runtime/useAgentPanelState';
import { flattenFileNodes } from './runtime/shared';
import { useAgentRunState } from './runtime/useAgentRunState';
import { useAgentSessionState } from './runtime/useAgentSessionState';
import { useStore } from '../../store';
import { postMessage } from '../../api/vscodeApi';
import type { AgentMessage } from './state/types';

export function useAgentChatRuntime(projectRoot: string | null, selectedTargets: string[]) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activityLabel, setActivityLabel] = useState<string>('Idle');
  const [activityElapsedSeconds, setActivityElapsedSeconds] = useState(0);
  const [contextWindow, setContextWindow] = useState<{ usedTokens: number; limitTokens: number } | null>(null);
  const [compactionNotice, setCompactionNotice] = useState<{ nonce: number; status: string; detail: string | null } | null>(null);
  const pendingSteeringByChatRef = useRef<Record<string, string[]>>({});
  const compactionNoticeTimerRef = useRef<number | null>(null);

  const projectModules = useStore((state) => (projectRoot ? state.projectModules[projectRoot] ?? [] : []));
  const projectFileNodes = useStore((state) => (projectRoot ? state.projectFiles[projectRoot] ?? [] : []));
  const isLoadingModules = useStore((state) => state.isLoadingModules);
  const isLoadingFiles = useStore((state) => state.isLoadingFiles);
  const queuedBuilds = useStore((state) => state.queuedBuilds);

  const projectFiles = useMemo(() => flattenFileNodes(projectFileNodes), [projectFileNodes]);
  const composerState = useAgentComposerState(projectModules, projectFiles, {
    isLoadingModules,
    isLoadingFiles,
  });
  const panelState = useAgentPanelState(messages);

  const resetChatUiState = useCallback(() => {
    composerState.setMentionToken(null);
    composerState.setMentionIndex(0);
    panelState.resetTransientPanelState();
    setContextWindow(null);
    setCompactionNotice(null);
    if (compactionNoticeTimerRef.current !== null) {
      window.clearTimeout(compactionNoticeTimerRef.current);
      compactionNoticeTimerRef.current = null;
    }
  }, [composerState, panelState]);

  const sessionState = useAgentSessionState({
    projectRoot,
    sessionId,
    setSessionId,
    messages,
    setMessages,
    input: composerState.input,
    setInput: composerState.setInput,
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
  });

  const runState = useAgentRunState({
    projectRoot,
    selectedTargets,
    input: composerState.input,
    setInput: composerState.setInput,
    sessionId,
    setSessionId,
    activeChatId: sessionState.activeChatId,
    activeChatSnapshot: sessionState.activeChatSnapshot,
    activeRunId,
    setActiveRunId,
    isSending,
    setIsSending,
    setIsStopping,
    setError,
    setActivityLabel,
    updateChatSnapshot: sessionState.updateChatSnapshot,
    chatSnapshotsRef: sessionState.chatSnapshotsRef,
    pendingSteeringByChatRef,
    activeChatIdRef: sessionState.activeChatIdRef,
    compactionNoticeTimerRef,
    setCompactionNotice,
    setContextWindow,
    setMessages,
    setMentionToken: composerState.setMentionToken,
    setMentionIndex: composerState.setMentionIndex,
  });

  const changedFilesSummary = useMemo(() => collectChangedFilesSummary(messages), [messages]);
  const contextUsage = useMemo(() => {
    if (!contextWindow || contextWindow.limitTokens <= 0) return null;
    const used = Math.max(0, Math.min(contextWindow.usedTokens, contextWindow.limitTokens));
    const usedPercent = Math.max(0, Math.min(100, Math.round((used / contextWindow.limitTokens) * 100)));
    return {
      usedTokens: used,
      limitTokens: contextWindow.limitTokens,
      usedPercent,
      leftPercent: Math.max(0, 100 - usedPercent),
    };
  }, [contextWindow]);
  const projectQueuedBuilds = useMemo(
    () => (projectRoot ? queuedBuilds.filter((build) => build.projectRoot === projectRoot) : []),
    [projectRoot, queuedBuilds],
  );
  const latestBuildStatus = useMemo(
    () => findLatestBuildStatus(messages, projectQueuedBuilds, projectRoot),
    [messages, projectQueuedBuilds, projectRoot],
  );

  const openFileDiff = useCallback((file: AgentChangedFile) => {
    postMessage({
      type: 'openDiff',
      path: file.payload.path,
      beforeContent: file.payload.before_content,
      afterContent: file.payload.after_content,
      title: `Agent edit diff: ${file.payload.path}`,
    });
  }, []);

  const startNewChat = useCallback(() => {
    if (!projectRoot) return;
    sessionState.createAndActivateChat(projectRoot);
    panelState.setIsChatsPanelOpen(false);
  }, [panelState, projectRoot, sessionState]);

  const activateChat = useCallback((chatId: string) => {
    sessionState.activateChat(chatId);
    panelState.setIsChatsPanelOpen(false);
  }, [panelState, sessionState]);

  const statusClass = isSessionLoading || isSending || isStopping ? 'working' : sessionState.isReady ? 'ready' : 'idle';
  const statusText = isSessionLoading ? 'Starting' : (isSending || isStopping) ? 'Working' : sessionState.isReady ? 'Ready' : 'Idle';

  return {
    minimizedDockHeight: panelState.minimizedDockHeight,
    activeChatId: sessionState.activeChatId,
    isChatsPanelOpen: panelState.isChatsPanelOpen,
    sessionId,
    messages,
    input: composerState.input,
    isSending,
    isStopping,
    isSessionLoading,
    error,
    dockHeight: panelState.dockHeight,
    isMinimized: panelState.isMinimized,
    changesExpanded: panelState.changesExpanded,
    expandedTraceGroups: panelState.expandedTraceGroups,
    expandedTraceKeys: panelState.expandedTraceKeys,
    resizingDock: panelState.resizingDock,
    compactionNotice,
    mentionToken: composerState.mentionToken,
    mentionItems: composerState.mentionItems,
    isLoadingMentions: composerState.isLoadingMentions,
    mentionIndex: composerState.mentionIndex,
    messagesRef: panelState.messagesRef,
    composerInputRef: composerState.composerInputRef,
    chatsPanelRef: panelState.chatsPanelRef,
    chatsPanelToggleRef: panelState.chatsPanelToggleRef,
    projectChats: sessionState.projectChats,
    isReady: sessionState.isReady,
    headerTitle: sessionState.headerTitle,
    activeChatTitle: sessionState.activeChatTitle,
    changedFilesSummary,
    contextUsage,
    latestBuildStatus,
    statusClass,
    statusText,
    setIsChatsPanelOpen: panelState.setIsChatsPanelOpen,
    setChangesExpanded: panelState.setChangesExpanded,
    setInput: composerState.setInput,
    setMentionToken: composerState.setMentionToken,
    setMentionIndex: composerState.setMentionIndex,
    toggleTraceGroupExpanded: panelState.toggleTraceGroupExpanded,
    toggleTraceExpanded: panelState.toggleTraceExpanded,
    startNewChat,
    toggleMinimized: panelState.toggleMinimized,
    startResize: panelState.startResize,
    refreshMentionFromInput: composerState.refreshMentionFromInput,
    insertMention: composerState.insertMention,
    stopRun: runState.stopRun,
    sendSteeringMessage: runState.sendSteeringMessage,
    sendMessage: runState.sendMessage,
    activateChat,
    openFileDiff,
  };
}
