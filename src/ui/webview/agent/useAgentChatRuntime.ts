import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Build, FileNode, ModuleDefinition } from '../../shared/generated-types';
import { collectChangedFilesSummary, type AgentChangedFile } from './components/viewHelpers';
import { useAgentComposerState } from './runtime/useAgentComposerState';
import { useAgentPanelState } from './runtime/useAgentPanelState';
import { flattenFileNodes } from './runtime/shared';
import { useAgentRunState } from './runtime/useAgentRunState';
import { useAgentSessionState } from './runtime/useAgentSessionState';
import { WebviewRpcClient, rpcClient } from '../shared/rpcClient';
import type { AgentMessage } from './state/types';

export function useAgentChatRuntime(
  projectRoot: string | null,
  selectedTargets: string[],
  projectModules: ModuleDefinition[],
  projectFileNodes: FileNode[],
  projectBuilds: Build[],
  options?: {
    isLoadingModules?: boolean;
    isLoadingFiles?: boolean;
  },
) {
  const [transientError, setTransientError] = useState<string | null>(null);
  const [contextWindow, setContextWindow] = useState<{ usedTokens: number; limitTokens: number } | null>(null);
  const [compactionNotice, setCompactionNotice] = useState<{ nonce: number; status: string; detail: string | null } | null>(null);
  const compactionNoticeTimerRef = useRef<number | null>(null);
  const agentData = WebviewRpcClient.useSubscribe('agentData');

  const projectFiles = useMemo(() => flattenFileNodes(projectFileNodes), [projectFileNodes]);
  const composerState = useAgentComposerState(projectModules, projectFiles, {
    isLoadingModules: options?.isLoadingModules,
    isLoadingFiles: options?.isLoadingFiles,
  });
  const { setMentionToken, setMentionIndex } = composerState;
  const [emptyMessages] = useState<AgentMessage[]>([
    { id: 'agent-empty', role: 'system', content: 'Select a project to start an agent session.' },
  ]);

  const resetChatUiState = useCallback(() => {
    setMentionToken(null);
    setMentionIndex(0);
    setContextWindow(null);
    setCompactionNotice(null);
    if (compactionNoticeTimerRef.current !== null) {
      window.clearTimeout(compactionNoticeTimerRef.current);
      compactionNoticeTimerRef.current = null;
    }
  }, [setMentionIndex, setMentionToken]);

  const sessionState = useAgentSessionState({
    agentData,
    projectRoot,
    input: composerState.input,
    setInput: composerState.setInput,
    resetChatUiState,
  });

  const activeSnapshot = sessionState.activeChatSnapshot;
  const sessionId = activeSnapshot?.sessionId ?? null;
  const messages = activeSnapshot?.messages ?? (projectRoot ? [] : emptyMessages);
  const isSending = activeSnapshot?.isSending ?? false;
  const isStopping = activeSnapshot?.isStopping ?? false;
  const isSessionLoading = activeSnapshot?.isSessionLoading ?? false;
  const error = activeSnapshot?.error ?? transientError;
  const panelState = useAgentPanelState(messages);
  const { resetTransientPanelState } = panelState;

  const runState = useAgentRunState({
    projectRoot,
    selectedTargets,
    input: composerState.input,
    setInput: composerState.setInput,
    sessionId,
    activeChatSnapshot: activeSnapshot,
    chatSnapshotsRef: sessionState.chatSnapshotsRef,
    activeChatIdRef: sessionState.activeChatIdRef,
    compactionNoticeTimerRef,
    setCompactionNotice,
    setContextWindow,
    setMentionToken: composerState.setMentionToken,
    setMentionIndex: composerState.setMentionIndex,
    setTransientError,
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
  const openFileDiff = useCallback((file: AgentChangedFile) => {
    void rpcClient?.requestAction("vscode.openDiff", {
      path: file.payload.path,
      beforeContent: file.payload.before_content,
      afterContent: file.payload.after_content,
      title: `Agent edit diff: ${file.payload.path}`,
    });
  }, []);

  const activateChat = useCallback((chatId: string) => {
    sessionState.activateChat(chatId);
    panelState.setIsChatsPanelOpen(false);
  }, [panelState, sessionState]);

  const statusClass = isSessionLoading || isSending || isStopping ? 'working' : sessionState.isReady ? 'ready' : 'idle';
  const statusText = isSessionLoading ? 'Starting' : (isSending || isStopping) ? 'Working' : sessionState.isReady ? 'Ready' : 'Idle';

  const setInput = useCallback((value: string) => {
    setTransientError(null);
    composerState.setInput(value);
  }, [composerState]);

  useEffect(() => {
    resetTransientPanelState();
  }, [resetTransientPanelState, sessionState.activeChatId]);

  const resetPanelAndInput = useCallback((root: string) => {
    resetTransientPanelState();
    setTransientError(null);
    sessionState.createAndActivateChat(root);
    panelState.setIsChatsPanelOpen(false);
  }, [panelState, resetTransientPanelState, sessionState]);

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
    statusClass,
    statusText,
    setIsChatsPanelOpen: panelState.setIsChatsPanelOpen,
    setChangesExpanded: panelState.setChangesExpanded,
    setInput,
    setMentionToken: composerState.setMentionToken,
    setMentionIndex: composerState.setMentionIndex,
    toggleTraceGroupExpanded: panelState.toggleTraceGroupExpanded,
    toggleTraceExpanded: panelState.toggleTraceExpanded,
    startNewChat: () => {
      if (!projectRoot) return;
      resetPanelAndInput(projectRoot);
    },
    toggleMinimized: panelState.toggleMinimized,
    startResize: panelState.startResize,
    refreshMentionFromInput: composerState.refreshMentionFromInput,
    insertMention: composerState.insertMention,
    stopRun: runState.stopRun,
    sendSteeringMessage: runState.sendSteeringMessage,
    sendInterruptMessage: runState.sendInterruptMessage,
    sendMessage: runState.sendMessage,
    activateChat,
    openFileDiff,
  };
}
