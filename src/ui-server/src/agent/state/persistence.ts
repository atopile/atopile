import { DEFAULT_CHAT_TITLE, deriveChatTitle } from '../AgentChatPanel.helpers';
import type { AgentChatSnapshot, AgentMessage } from './types';

export const CHAT_SNAPSHOTS_STORAGE_KEY = 'atopile.agentChatSnapshots.v1';
export const ACTIVE_CHAT_STORAGE_KEY = 'atopile.agentActiveChatByProject.v1';
const MAX_PERSISTED_CHATS = 48;
const MAX_PERSISTED_MESSAGES_PER_CHAT = 120;
const MAX_PERSISTED_MESSAGE_CHARS = 12_000;
const MAX_PERSISTED_INPUT_CHARS = 4_000;

function isValidMessageRole(value: unknown): value is AgentMessage['role'] {
  return value === 'user' || value === 'assistant' || value === 'system';
}

export function normalizeMessageForPersistence(value: unknown): AgentMessage | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as Partial<AgentMessage>;
  if (!isValidMessageRole(candidate.role)) return null;
  if (typeof candidate.id !== 'string' || !candidate.id) return null;
  if (typeof candidate.content !== 'string') return null;
  const content = candidate.content.length > MAX_PERSISTED_MESSAGE_CHARS
    ? `${candidate.content.slice(0, MAX_PERSISTED_MESSAGE_CHARS)}...`
    : candidate.content;
  return {
    id: candidate.id,
    role: candidate.role,
    content,
  };
}

export function normalizeSnapshotForPersistence(value: unknown): AgentChatSnapshot | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as Partial<AgentChatSnapshot>;
  if (typeof candidate.id !== 'string' || !candidate.id) return null;
  if (typeof candidate.projectRoot !== 'string' || !candidate.projectRoot) return null;

  const rawMessages = Array.isArray(candidate.messages) ? candidate.messages : [];
  const messages = rawMessages
    .map((message) => normalizeMessageForPersistence(message))
    .filter((message): message is AgentMessage => Boolean(message))
    .slice(-MAX_PERSISTED_MESSAGES_PER_CHAT);

  const createdAt = typeof candidate.createdAt === 'number' && Number.isFinite(candidate.createdAt)
    ? candidate.createdAt
    : Date.now();
  const updatedAt = typeof candidate.updatedAt === 'number' && Number.isFinite(candidate.updatedAt)
    ? candidate.updatedAt
    : createdAt;

  const input = typeof candidate.input === 'string'
    ? candidate.input.slice(0, MAX_PERSISTED_INPUT_CHARS)
    : '';
  const title = typeof candidate.title === 'string' && candidate.title.trim()
    ? candidate.title
    : deriveChatTitle(messages);

  const resumedWithSession = typeof candidate.sessionId === 'string' && candidate.sessionId.length > 0;
  return {
    id: candidate.id,
    projectRoot: candidate.projectRoot,
    title: title || DEFAULT_CHAT_TITLE,
    sessionId: resumedWithSession ? String(candidate.sessionId) : null,
    isSessionLoading: false,
    isSending: false,
    isStopping: false,
    activeRunId: null,
    pendingRunId: null,
    pendingAssistantId: null,
    cancelRequested: false,
    activityElapsedSeconds: 0,
    messages,
    packageWorkers: [],
    input,
    error: typeof candidate.error === 'string' ? candidate.error : null,
    activityLabel: resumedWithSession ? 'Ready' : 'Idle',
    createdAt,
    updatedAt,
  };
}

export function parseStoredSnapshots(raw: string | null): AgentChatSnapshot[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as { chats?: unknown };
    const rawChats = Array.isArray(parsed?.chats) ? parsed.chats : [];
    return rawChats
      .map((chat) => normalizeSnapshotForPersistence(chat))
      .filter((chat): chat is AgentChatSnapshot => Boolean(chat))
      .sort((left, right) => right.updatedAt - left.updatedAt)
      .slice(0, MAX_PERSISTED_CHATS);
  } catch {
    return [];
  }
}

export function parseStoredActiveChats(raw: string | null): Record<string, string> {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    const entries = Object.entries(parsed as Record<string, unknown>);
    const out: Record<string, string> = {};
    for (const [project, chatId] of entries) {
      if (typeof project !== 'string' || !project) continue;
      if (typeof chatId !== 'string' || !chatId) continue;
      out[project] = chatId;
    }
    return out;
  } catch {
    return {};
  }
}

export function persistAgentState(
  snapshots: AgentChatSnapshot[],
  activeChatByProject: Record<string, string>,
): void {
  if (typeof window === 'undefined') return;

  const persistedChats = snapshots
    .map((chat) => normalizeSnapshotForPersistence(chat))
    .filter((chat): chat is AgentChatSnapshot => Boolean(chat))
    .sort((left, right) => right.updatedAt - left.updatedAt)
    .slice(0, MAX_PERSISTED_CHATS);
  const payload = {
    version: 1,
    chats: persistedChats,
  };

  try {
    window.localStorage.setItem(CHAT_SNAPSHOTS_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    const trimmedPayload = {
      version: 1,
      chats: persistedChats.slice(0, 16).map((chat) => ({
        ...chat,
        messages: chat.messages.slice(-40),
      })),
    };
    try {
      window.localStorage.setItem(CHAT_SNAPSHOTS_STORAGE_KEY, JSON.stringify(trimmedPayload));
    } catch {
      // Ignore storage failures; chat remains fully functional in-memory.
    }
  }

  const activeMap = { ...activeChatByProject };
  const validProjectRoots = new Set(persistedChats.map((chat) => chat.projectRoot));
  Object.keys(activeMap).forEach((root) => {
    if (!validProjectRoots.has(root)) {
      delete activeMap[root];
    }
  });
  try {
    window.localStorage.setItem(ACTIVE_CHAT_STORAGE_KEY, JSON.stringify(activeMap));
  } catch {
    // Ignore storage failures; active chat defaults to most recent.
  }
}
