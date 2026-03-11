import { useCallback, useEffect, type Dispatch, type MutableRefObject, type SetStateAction } from 'react';
import { AgentApiError, agentApi } from '../../api/agent';
import { normalizeAssistantText } from '../AgentChatPanel.helpers';
import { applyProgressToMessages, inferActivityFromProgress, readProgressPayload } from '../state/progress';
import type { AgentChatSnapshot, AgentMessage } from '../state/types';
import { withCompletionNudge } from './shared';

const RUN_CANCELLED_MARKER = '__ATOPILE_AGENT_RUN_CANCELLED__';
const RUN_LOST_MARKER = '__ATOPILE_AGENT_RUN_LOST__';

function isSessionNotFoundError(error: unknown): boolean {
  return error instanceof AgentApiError
    && error.status === 404
    && error.message.includes('Session not found:');
}

function isRunNotFoundError(error: unknown): boolean {
  return error instanceof AgentApiError
    && error.status === 404
    && error.message.includes('Run not found:');
}

interface RunStateDeps {
  projectRoot: string | null;
  selectedTargets: string[];
  input: string;
  setInput: (value: string) => void;
  sessionId: string | null;
  setSessionId: (value: string | null) => void;
  activeChatId: string | null;
  activeChatSnapshot: AgentChatSnapshot | null;
  activeRunId: string | null;
  setActiveRunId: (value: string | null) => void;
  isSending: boolean;
  setIsSending: (value: boolean) => void;
  setIsStopping: (value: boolean) => void;
  setError: (value: string | null) => void;
  setActivityLabel: (value: string) => void;
  updateChatSnapshot: (chatId: string, updater: (chat: AgentChatSnapshot) => AgentChatSnapshot) => void;
  chatSnapshotsRef: MutableRefObject<AgentChatSnapshot[]>;
  pendingSteeringByChatRef: MutableRefObject<Record<string, string[]>>;
  activeChatIdRef: MutableRefObject<string | null>;
  compactionNoticeTimerRef: MutableRefObject<number | null>;
  setCompactionNotice: (value: { nonce: number; status: string; detail: string | null } | null | ((current: { nonce: number; status: string; detail: string | null } | null) => { nonce: number; status: string; detail: string | null } | null)) => void;
  setContextWindow: (value: { usedTokens: number; limitTokens: number } | null) => void;
  setMessages: Dispatch<SetStateAction<AgentMessage[]>>;
  setMentionToken: (value: null) => void;
  setMentionIndex: (value: number) => void;
}

interface SendMessageOptions {
  directMessage?: string;
  hideUserMessage?: boolean;
}

export function useAgentRunState({
  projectRoot,
  selectedTargets,
  input,
  setInput,
  sessionId,
  setSessionId,
  activeChatId,
  activeChatSnapshot,
  activeRunId,
  setActiveRunId,
  isSending,
  setIsSending,
  setIsStopping,
  setError,
  setActivityLabel,
  updateChatSnapshot,
  chatSnapshotsRef,
  pendingSteeringByChatRef,
  activeChatIdRef,
  compactionNoticeTimerRef,
  setCompactionNotice,
  setContextWindow,
  setMessages,
  setMentionToken,
  setMentionIndex,
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
    const onProgress = (event: Event) => {
      const customEvent = event as CustomEvent;
      const parsed = readProgressPayload(customEvent.detail);
      if (!parsed.sessionId) return;
      const targetChat = chatSnapshotsRef.current.find((chat) => {
        if (chat.sessionId !== parsed.sessionId) return false;
        if (!parsed.runId) return true;
        return !chat.pendingRunId || chat.pendingRunId === parsed.runId || chat.activeRunId === parsed.runId;
      });
      if (!targetChat) return;
      const pendingId = targetChat.pendingAssistantId;
      if (!pendingId) return;
      const nextActivity = inferActivityFromProgress(parsed);

      updateChatSnapshot(targetChat.id, (chat) => {
        const next: AgentChatSnapshot = {
          ...chat,
          messages: applyProgressToMessages(chat.messages, pendingId, parsed, nextActivity),
        };
        if (nextActivity) next.activityLabel = nextActivity;
        if (parsed.phase === 'design_questions' || parsed.phase === 'done' || parsed.phase === 'stopped' || parsed.phase === 'error') {
          next.isSending = false;
          next.isStopping = false;
          next.activeRunId = null;
          next.pendingRunId = null;
          next.pendingAssistantId = null;
          next.cancelRequested = false;
        }
        return next;
      });

      if (activeChatIdRef.current === targetChat.id) {
        const usedTokens = parsed.inputTokens ?? parsed.totalTokens;
        const limitTokens = parsed.contextLimitTokens;
        if (typeof usedTokens === 'number' && Number.isFinite(usedTokens) && typeof limitTokens === 'number' && Number.isFinite(limitTokens) && limitTokens > 0) {
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
        if (nextActivity) setActivityLabel(nextActivity);
        setMessages((previous) => applyProgressToMessages(previous, pendingId, parsed, nextActivity));
        if (parsed.phase === 'design_questions' || parsed.phase === 'done' || parsed.phase === 'stopped' || parsed.phase === 'error') {
          setIsSending(false);
          setIsStopping(false);
          setActiveRunId(null);
        }
      }
    };

    window.addEventListener('atopile:agent_progress', onProgress as EventListener);
    return () => window.removeEventListener('atopile:agent_progress', onProgress as EventListener);
  }, [activeChatIdRef, chatSnapshotsRef, compactionNoticeTimerRef, setActivityLabel, setCompactionNotice, setContextWindow, setIsSending, setIsStopping, setMessages, setActiveRunId, updateChatSnapshot]);

  const waitForRunCompletion = useCallback(async (currentSessionId: string, runId: string) => {
    const startedAt = Date.now();
    const hardTimeoutMs = 2 * 60 * 60 * 1000;
    let pollErrorCount = 0;

    while ((Date.now() - startedAt) < hardTimeoutMs) {
      try {
        const runStatus = await agentApi.getRunStatus(currentSessionId, runId);
        pollErrorCount = 0;
        if (runStatus.status === 'completed' && runStatus.response) return runStatus.response;
        if (runStatus.status === 'cancelled') throw new Error(`${RUN_CANCELLED_MARKER}:${runStatus.error ?? 'Cancelled'}`);
        if (runStatus.status === 'failed') throw new Error(runStatus.error ?? 'Agent run failed.');
      } catch (pollError: unknown) {
        pollErrorCount += 1;
        if (pollError instanceof Error && pollError.message.startsWith(RUN_CANCELLED_MARKER)) throw pollError;
        if (isRunNotFoundError(pollError)) {
          throw new Error(`${RUN_LOST_MARKER}:Active run was lost (the backend likely restarted). Please resend your message.`);
        }
        if (pollErrorCount >= 20) {
          const message = pollError instanceof Error ? pollError.message : 'Unable to poll agent run status.';
          throw new Error(`Lost contact while waiting for the active run. ${message}`);
        }
      }

      const delayMs = pollErrorCount > 0 ? Math.min(2500, 350 * (2 ** Math.min(5, pollErrorCount - 1))) : 350;
      await new Promise<void>((resolve) => {
        window.setTimeout(() => resolve(), delayMs);
      });
    }

    throw new Error('Agent run is still in progress after a long wait. Stop it or keep waiting.');
  }, []);

  const stopRun = useCallback(async () => {
    if (!activeChatId || !sessionId || !isSending) return;
    setIsStopping(true);
    setActivityLabel('Stopping');
    const pendingId = activeChatSnapshot?.pendingAssistantId ?? null;
    updateChatSnapshot(activeChatId, (chat) => ({
      ...chat,
      isStopping: true,
      cancelRequested: true,
      activityLabel: 'Stopping',
      messages: pendingId
        ? chat.messages.map((message) => message.id === pendingId ? { ...message, content: 'Stopping...', activity: 'Stopping' } : message)
        : chat.messages,
    }));
    if (pendingId) {
      setMessages((previous) => previous.map((message) => message.id === pendingId ? { ...message, content: 'Stopping...', activity: 'Stopping' } : message));
    }

    const runId = activeRunId ?? activeChatSnapshot?.pendingRunId ?? null;
    if (!runId) return;

    try {
      await agentApi.cancelRun(sessionId, runId);
    } catch (stopError: unknown) {
      if (isRunNotFoundError(stopError)) {
        updateChatSnapshot(activeChatId, (chat) => ({
          ...chat,
          isSending: false,
          isStopping: false,
          activeRunId: null,
          pendingRunId: null,
          pendingAssistantId: null,
          cancelRequested: false,
          activityLabel: 'Stopped',
          error: null,
        }));
        setIsSending(false);
        setIsStopping(false);
        setActiveRunId(null);
        setError(null);
        setActivityLabel('Stopped');
        return;
      }
      const message = stopError instanceof Error ? stopError.message : 'Unable to stop the active run.';
      setError(message);
      updateChatSnapshot(activeChatId, (chat) => ({ ...chat, error: message }));
    }
  }, [activeChatId, activeChatSnapshot, activeRunId, isSending, sessionId, setActivityLabel, setActiveRunId, setError, setIsSending, setIsStopping, setMessages, updateChatSnapshot]);

  const sendSteeringMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || !projectRoot || !sessionId || !activeChatId || !isSending) return;
    const chatId = activeChatId;
    const chatPrefix = chatId;
    const pendingAssistantId = activeChatSnapshot?.pendingAssistantId ?? null;
    const userMessage: AgentMessage = { id: `${chatPrefix}-user-steer-${Date.now()}`, role: 'user', content: trimmed };

    const applySteerPendingState = (entries: AgentMessage[]): AgentMessage[] => {
      const withUser = [...entries, userMessage];
      if (!pendingAssistantId) return withUser;
      return withUser.map((message) => message.id === pendingAssistantId ? { ...message, content: 'Incorporating latest guidance...', activity: 'Steering' } : message);
    };

    updateChatSnapshot(chatId, (chat) => ({ ...chat, messages: applySteerPendingState(chat.messages), input: '', error: null, activityLabel: 'Steering' }));
    if (activeChatIdRef.current === chatId) {
      setMessages((previous) => applySteerPendingState(previous));
      setActivityLabel('Steering');
      setError(null);
    }
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);

    const runId = activeRunId ?? activeChatSnapshot?.pendingRunId ?? null;
    if (!runId) {
      const queued = pendingSteeringByChatRef.current[chatId] ?? [];
      pendingSteeringByChatRef.current[chatId] = [...queued, trimmed];
      return;
    }

    try {
      const steerResult = await agentApi.steerRun(sessionId, runId, { message: trimmed });
      if (steerResult.status !== 'running') throw new Error('Active run is no longer running. Please resend your request.');
    } catch (steerError: unknown) {
      const message = steerError instanceof Error ? steerError.message : 'Unable to send steering guidance.';
      const steerErrorMessage: AgentMessage = { id: `${chatPrefix}-steer-error-${Date.now()}`, role: 'system', content: `Steering failed: ${message}` };
      updateChatSnapshot(chatId, (chat) => ({ ...chat, messages: [...chat.messages, steerErrorMessage], error: message }));
      if (activeChatIdRef.current === chatId) {
        setMessages((previous) => [...previous, steerErrorMessage]);
        setError(message);
      }
    }
  }, [activeChatId, activeChatSnapshot, activeRunId, input, isSending, projectRoot, sessionId, setActivityLabel, setError, setInput, setMentionIndex, setMentionToken, setMessages, pendingSteeringByChatRef, activeChatIdRef, updateChatSnapshot]);

  const sendInterruptMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || !projectRoot || !sessionId || !activeChatId || !isSending) return;
    const chatId = activeChatId;
    const chatPrefix = chatId;
    const pendingAssistantId = activeChatSnapshot?.pendingAssistantId ?? null;
    const userMessage: AgentMessage = {
      id: `${chatPrefix}-user-interrupt-${Date.now()}`,
      role: 'user',
      content: trimmed,
    };

    const applyInterruptPendingState = (entries: AgentMessage[]): AgentMessage[] => {
      const withUser = [...entries, userMessage];
      if (!pendingAssistantId) return withUser;
      return withUser.map((message) => (
        message.id === pendingAssistantId
          ? { ...message, content: 'Interrupting after the current step...', activity: 'Interrupting' }
          : message
      ));
    };

    updateChatSnapshot(chatId, (chat) => ({
      ...chat,
      messages: applyInterruptPendingState(chat.messages),
      input: '',
      error: null,
      activityLabel: 'Interrupting',
      isStopping: true,
      cancelRequested: true,
    }));
    if (activeChatIdRef.current === chatId) {
      setMessages((previous) => applyInterruptPendingState(previous));
      setActivityLabel('Interrupting');
      setError(null);
      setIsStopping(true);
    }
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);

    const runId = activeRunId ?? activeChatSnapshot?.pendingRunId ?? null;
    if (!runId) return;

    try {
      const interruptResult = await agentApi.interruptRun(sessionId, runId, { message: trimmed });
      if (interruptResult.status !== 'running') {
        throw new Error('Active run is no longer running. Please resend your request.');
      }
    } catch (interruptError: unknown) {
      const message = interruptError instanceof Error ? interruptError.message : 'Unable to interrupt the active run.';
      const interruptErrorMessage: AgentMessage = {
        id: `${chatPrefix}-interrupt-error-${Date.now()}`,
        role: 'system',
        content: `Interrupt failed: ${message}`,
      };
      updateChatSnapshot(chatId, (chat) => ({
        ...chat,
        messages: [...chat.messages, interruptErrorMessage],
        error: message,
        isStopping: false,
        cancelRequested: false,
      }));
      if (activeChatIdRef.current === chatId) {
        setMessages((previous) => [...previous, interruptErrorMessage]);
        setError(message);
        setIsStopping(false);
      }
    }
  }, [activeChatId, activeChatSnapshot, activeRunId, input, isSending, projectRoot, sessionId, setActivityLabel, setError, setInput, setIsStopping, setMentionIndex, setMentionToken, setMessages, activeChatIdRef, updateChatSnapshot]);

  const sendMessage = useCallback(async (options?: string | SendMessageOptions) => {
    const directMessage = typeof options === 'string' ? options : options?.directMessage;
    const hideUserMessage = typeof options === 'object' && options !== null
      ? options.hideUserMessage === true
      : false;
    const trimmed = (directMessage ?? input).trim();
    if (!trimmed || !projectRoot || !sessionId || !activeChatId || isSending) return;
    const chatId = activeChatId;
    const chatPrefix = chatId;

    const userMessage: AgentMessage = { id: `${chatPrefix}-user-${Date.now()}`, role: 'user', content: trimmed };
    const pendingAssistantId = `${chatPrefix}-assistant-pending-${Date.now()}`;
    const pendingAssistantMessage: AgentMessage = {
      id: pendingAssistantId,
      role: 'assistant',
      content: 'Thinking...',
      activity: 'Planning',
      pending: true,
      toolTraces: [],
    };

    updateChatSnapshot(chatId, (chat) => ({
      ...chat,
      messages: [...chat.messages, ...(hideUserMessage ? [] : [userMessage]), pendingAssistantMessage],
      input: '',
      error: null,
      activityLabel: 'Planning',
      isSending: true,
      isStopping: false,
      activeRunId: null,
      pendingRunId: null,
      pendingAssistantId,
      cancelRequested: false,
      activityElapsedSeconds: 0,
    }));

    setMessages((previous) => [...previous, ...(hideUserMessage ? [] : [userMessage]), pendingAssistantMessage]);
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);
    setActiveRunId(null);
    setIsStopping(false);
    setIsSending(true);
    setError(null);
    setActivityLabel('Planning');

    try {
      let currentSessionId = sessionId;
      let run: { runId: string; status: string };
      try {
        run = await agentApi.createRun(currentSessionId, { message: trimmed, projectRoot, selectedTargets });
      } catch (runStartError: unknown) {
        if (!isSessionNotFoundError(runStartError)) throw runStartError;
        const recoveredSession = await agentApi.createSession(projectRoot);
        currentSessionId = recoveredSession.sessionId;
        const recoveredNotice: AgentMessage = {
          id: `${chatPrefix}-session-recovered-${Date.now()}`,
          role: 'system',
          content: 'Previous agent session expired. Reconnected with a new session and retrying.',
        };
        updateChatSnapshot(chatId, (chat) => ({ ...chat, sessionId: currentSessionId, messages: [...chat.messages, recoveredNotice] }));
        if (activeChatIdRef.current === chatId) {
          setSessionId(currentSessionId);
          setMessages((previous) => [...previous, recoveredNotice]);
        }
        run = await agentApi.createRun(currentSessionId, { message: trimmed, projectRoot, selectedTargets });
      }

      updateChatSnapshot(chatId, (chat) => ({ ...chat, pendingRunId: run.runId, activeRunId: run.runId }));
      setActiveRunId(run.runId);

      const queuedSteeringMessages = pendingSteeringByChatRef.current[chatId] ?? [];
      if (queuedSteeringMessages.length > 0) {
        delete pendingSteeringByChatRef.current[chatId];
        for (const steeringMessage of queuedSteeringMessages) {
          try {
            const steerResult = await agentApi.steerRun(currentSessionId, run.runId, { message: steeringMessage });
            if (steerResult.status !== 'running') break;
          } catch {
            break;
          }
        }
      }

      const cancelledEarly = chatSnapshotsRef.current.find((chat) => chat.id === chatId)?.cancelRequested;
      if (cancelledEarly) {
        if (activeChatIdRef.current === chatId) setIsStopping(true);
        await agentApi.cancelRun(currentSessionId, run.runId);
      }

      const response = await waitForRunCompletion(currentSessionId, run.runId);
      const finalizedTraces = response.toolTraces.map((trace) => ({ ...trace, running: false }));

      const buildFinalMessage = (pending: AgentMessage | undefined): AgentMessage => ({
        id: pending?.id ?? pendingAssistantId,
        role: 'assistant',
        content: pending?.designQuestions
          ? normalizeAssistantText(response.assistantMessage)
          : withCompletionNudge(normalizeAssistantText(response.assistantMessage), finalizedTraces),
        toolTraces: finalizedTraces,
        designQuestions: pending?.designQuestions ?? null,
        checklist: pending?.checklist ?? null,
      });

      updateChatSnapshot(chatId, (chat) => {
        const pending = chat.messages.find((message) => message.id === pendingAssistantId);
        const finalMsg = buildFinalMessage(pending);
        return {
          ...chat,
          messages: chat.messages.map((message) => message.id === pendingAssistantId ? finalMsg : message),
          isSending: false,
          isStopping: false,
          activeRunId: null,
          pendingRunId: null,
          pendingAssistantId: null,
          cancelRequested: false,
          activityLabel: 'Ready',
          error: null,
        };
      });
      if (activeChatIdRef.current === chatId) {
        setMessages((previous) => {
          const pending = previous.find((message) => message.id === pendingAssistantId);
          const finalMsg = buildFinalMessage(pending);
          return previous.map((message) => message.id === pendingAssistantId ? finalMsg : message);
        });
      }
    } catch (sendError: unknown) {
      const rawMessage = sendError instanceof Error ? sendError.message : 'Agent request failed.';
      const cancelled = rawMessage.startsWith(RUN_CANCELLED_MARKER);
      const runLost = rawMessage.startsWith(RUN_LOST_MARKER);
      const message = cancelled
        ? rawMessage.split(':').slice(1).join(':').trim() || 'Cancelled by user'
        : runLost
          ? rawMessage.split(':').slice(1).join(':').trim() || 'Active run was lost. Please resend your message.'
          : rawMessage;
      updateChatSnapshot(chatId, (chat) => ({
        ...chat,
        messages: chat.messages.map((entry) =>
          entry.id === pendingAssistantId
            ? {
                id: entry.id,
                role: 'assistant',
                content: cancelled ? `Stopped: ${message}` : runLost ? `Request interrupted: ${message}` : `Request failed: ${message}`,
                activity: cancelled ? 'Stopped' : runLost ? 'Interrupted' : 'Errored',
              }
            : entry
        ),
        isSending: false,
        isStopping: false,
        activeRunId: null,
        pendingRunId: null,
        pendingAssistantId: null,
        cancelRequested: false,
        activityLabel: cancelled ? 'Stopped' : runLost ? 'Interrupted' : 'Errored',
        error: cancelled ? null : message,
      }));
      if (activeChatIdRef.current === chatId) {
        if (!cancelled) setError(message);
        setMessages((previous) => previous.map((entry) =>
          entry.id === pendingAssistantId
            ? {
                id: entry.id,
                role: 'assistant',
                content: cancelled ? `Stopped: ${message}` : runLost ? `Request interrupted: ${message}` : `Request failed: ${message}`,
                activity: cancelled ? 'Stopped' : runLost ? 'Interrupted' : 'Errored',
              }
            : entry,
        ));
        setActivityLabel(cancelled ? 'Stopped' : runLost ? 'Interrupted' : 'Errored');
      }
    } finally {
      delete pendingSteeringByChatRef.current[chatId];
      if (activeChatIdRef.current === chatId) {
        setActiveRunId(null);
        setIsStopping(false);
        setIsSending(false);
      }
    }
  }, [activeChatId, activeChatSnapshot, activeRunId, input, isSending, projectRoot, selectedTargets, sessionId, setActivityLabel, setActiveRunId, setError, setInput, setIsSending, setIsStopping, setMentionIndex, setMentionToken, setMessages, setSessionId, updateChatSnapshot, waitForRunCompletion, pendingSteeringByChatRef, activeChatIdRef, chatSnapshotsRef]);

  return {
    stopRun,
    sendSteeringMessage,
    sendInterruptMessage,
    sendMessage,
  };
}
