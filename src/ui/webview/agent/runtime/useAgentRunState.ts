import { useCallback, useEffect, type MutableRefObject } from 'react';
import { addAgentProgressListener, agentApi } from '../api';
import { readProgressPayload } from '../state/progress';
import type { AgentChatSnapshot } from '../state/types';

interface RunStateDeps {
  projectRoot: string | null;
  selectedTargets: string[];
  input: string;
  setInput: (value: string) => void;
  sessionId: string | null;
  activeChatSnapshot: AgentChatSnapshot | null;
  chatSnapshotsRef: MutableRefObject<AgentChatSnapshot[]>;
  activeChatIdRef: MutableRefObject<string | null>;
  compactionNoticeTimerRef: MutableRefObject<number | null>;
  setCompactionNotice: (value: { nonce: number; status: string; detail: string | null } | null | ((current: { nonce: number; status: string; detail: string | null } | null) => { nonce: number; status: string; detail: string | null } | null)) => void;
  setContextWindow: (value: { usedTokens: number; limitTokens: number } | null) => void;
  setMentionToken: (value: null) => void;
  setMentionIndex: (value: number) => void;
  setTransientError: (value: string | null) => void;
}

export function useAgentRunState({
  projectRoot,
  selectedTargets,
  input,
  setInput,
  sessionId,
  activeChatSnapshot,
  chatSnapshotsRef,
  activeChatIdRef,
  compactionNoticeTimerRef,
  setCompactionNotice,
  setContextWindow,
  setMentionToken,
  setMentionIndex,
  setTransientError,
}: RunStateDeps) {
  useEffect(() => {
    return () => {
      if (compactionNoticeTimerRef.current !== null) {
        window.clearTimeout(compactionNoticeTimerRef.current);
        compactionNoticeTimerRef.current = null;
      }
    };
  }, [compactionNoticeTimerRef]);

  useEffect(() => {
    return addAgentProgressListener((payload) => {
      const parsed = readProgressPayload(payload);
      const activeChatId = activeChatIdRef.current;
      if (!activeChatId || !parsed.sessionId) return;
      const activeChat = chatSnapshotsRef.current.find((chat) => chat.id === activeChatId);
      if (!activeChat || activeChat.sessionId !== parsed.sessionId) return;
      if (parsed.runId && activeChat.activeRunId && activeChat.activeRunId !== parsed.runId) return;

      const usedTokens = parsed.inputTokens ?? parsed.totalTokens;
      const limitTokens = parsed.contextLimitTokens;
      if (
        typeof usedTokens === 'number'
        && Number.isFinite(usedTokens)
        && typeof limitTokens === 'number'
        && Number.isFinite(limitTokens)
        && limitTokens > 0
      ) {
        setContextWindow({ usedTokens: Math.max(0, Math.min(usedTokens, limitTokens)), limitTokens });
      }

      if (parsed.phase === 'compacting') {
        const status = parsed.statusText || 'Compacting context';
        const nonce = Date.now();
        setCompactionNotice({ nonce, status, detail: parsed.detailText });
        if (compactionNoticeTimerRef.current !== null) {
          window.clearTimeout(compactionNoticeTimerRef.current);
        }
        compactionNoticeTimerRef.current = window.setTimeout(() => {
          setCompactionNotice((current) => (current && current.nonce === nonce ? null : current));
          compactionNoticeTimerRef.current = null;
        }, 8000);
      }
    });
  }, [activeChatIdRef, chatSnapshotsRef, compactionNoticeTimerRef, setCompactionNotice, setContextWindow]);

  useEffect(() => {
    if (activeChatSnapshot?.isSending) return;
    setContextWindow(null);
  }, [activeChatSnapshot?.isSending, setContextWindow]);

  const stopRun = useCallback(() => {
    if (!sessionId || !activeChatSnapshot?.activeRunId || !activeChatSnapshot.isSending) return;
    setTransientError(null);
    try {
      agentApi.cancelRun(sessionId, activeChatSnapshot.activeRunId);
    } catch (stopError: unknown) {
      setTransientError(stopError instanceof Error ? stopError.message : 'Unable to stop the active run.');
    }
  }, [activeChatSnapshot, sessionId, setTransientError]);

  const sendSteeringMessage = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || !sessionId || !activeChatSnapshot?.activeRunId || !activeChatSnapshot.isSending) return;
    setTransientError(null);
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);
    try {
      agentApi.steerRun(sessionId, activeChatSnapshot.activeRunId, { message: trimmed });
    } catch (steerError: unknown) {
      setTransientError(steerError instanceof Error ? steerError.message : 'Unable to send steering guidance.');
    }
  }, [activeChatSnapshot, input, sessionId, setInput, setMentionIndex, setMentionToken, setTransientError]);

  const sendInterruptMessage = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || !sessionId || !activeChatSnapshot?.activeRunId || !activeChatSnapshot.isSending) return;
    setTransientError(null);
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);
    try {
      agentApi.interruptRun(sessionId, activeChatSnapshot.activeRunId, { message: trimmed });
    } catch (interruptError: unknown) {
      setTransientError(interruptError instanceof Error ? interruptError.message : 'Unable to interrupt the active run.');
    }
  }, [activeChatSnapshot, input, sessionId, setInput, setMentionIndex, setMentionToken, setTransientError]);

  const sendMessage = useCallback((options?: string | { directMessage?: string; hideUserMessage?: boolean }) => {
    const directMessage = typeof options === 'string' ? options : options?.directMessage;
    const trimmed = (directMessage ?? input).trim();
    if (!trimmed || !projectRoot || !sessionId || !activeChatSnapshot?.sessionId || activeChatSnapshot.isSending) return;
    setTransientError(null);
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);
    try {
      agentApi.createRun(sessionId, { message: trimmed, projectRoot, selectedTargets });
    } catch (sendError: unknown) {
      setTransientError(sendError instanceof Error ? sendError.message : 'Agent request failed.');
    }
  }, [activeChatSnapshot, input, projectRoot, selectedTargets, sessionId, setInput, setMentionIndex, setMentionToken, setTransientError]);

  return {
    stopRun,
    sendSteeringMessage,
    sendInterruptMessage,
    sendMessage,
  };
}
