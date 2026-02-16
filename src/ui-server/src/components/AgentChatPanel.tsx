import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import {
  ArrowUp,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  Loader2,
  Square,
  Plus,
  Minimize2,
  Maximize2,
  MessageSquareText,
  X,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  AgentApiError,
  agentApi,
  type AgentToolTrace,
} from '../api/agent';
import { api } from '../api/client';
import { postMessage } from '../api/vscodeApi';
import { useStore } from '../store';
import { BuildQueueItem } from './BuildQueueItem';
import {
  createChatId,
  DEFAULT_CHAT_TITLE,
  deriveChatTitle,
  formatChatTimestamp,
  normalizeAssistantText,
  shortProjectName,
  summarizeChatPreview,
  trimSingleLine,
} from './AgentChatPanel.helpers';
import type { Build, FileTreeNode, ModuleDefinition, QueuedBuild } from '../types/build';
import './AgentChatPanel.css';

type MessageRole = 'user' | 'assistant' | 'system';

type AgentProgressPhase = 'thinking' | 'tool_start' | 'tool_end' | 'done' | 'stopped' | 'error' | 'compacting';

interface AgentProgressPayload {
  session_id?: unknown;
  run_id?: unknown;
  phase?: unknown;
  call_id?: unknown;
  name?: unknown;
  args?: unknown;
  trace?: unknown;
  status_text?: unknown;
  detail_text?: unknown;
  loop?: unknown;
  tool_index?: unknown;
  tool_count?: unknown;
  input_tokens?: unknown;
  output_tokens?: unknown;
  total_tokens?: unknown;
  usage?: unknown;
}

interface AgentTraceView extends AgentToolTrace {
  callId?: string;
  running?: boolean;
}

interface AgentEditDiffUiPayload {
  path: string;
  before_content: string;
  after_content: string;
}

interface AgentMessage {
  id: string;
  role: MessageRole;
  content: string;
  pending?: boolean;
  activity?: string;
  toolTraces?: AgentTraceView[];
}

interface AgentChangedFile {
  path: string;
  added: number;
  removed: number;
  payload: AgentEditDiffUiPayload;
}

interface AgentChangedFilesSummary {
  messageId: string;
  files: AgentChangedFile[];
  totalAdded: number;
  totalRemoved: number;
}

interface BuildRunReferences {
  hasBuildRun: boolean;
  hasRunningBuildRun: boolean;
  buildIds: string[];
  targets: string[];
}

interface MessageBuildStatusState {
  messageId: string;
  builds: QueuedBuild[];
  pendingBuildIds: string[];
}

interface MentionToken {
  start: number;
  end: number;
  query: string;
}

interface MentionItem {
  kind: 'file' | 'module';
  label: string;
  token: string;
  subtitle?: string;
}

interface AgentChatSnapshot {
  id: string;
  projectRoot: string;
  title: string;
  sessionId: string | null;
  isSessionLoading: boolean;
  isSending: boolean;
  isStopping: boolean;
  activeRunId: string | null;
  pendingRunId: string | null;
  pendingAssistantId: string | null;
  cancelRequested: boolean;
  activityElapsedSeconds: number;
  messages: AgentMessage[];
  input: string;
  error: string | null;
  activityLabel: string;
  createdAt: number;
  updatedAt: number;
}

interface AgentLiveProgressState {
  phase: AgentProgressPhase | null;
  statusText: string | null;
  detailText: string | null;
  loop: number | null;
  toolIndex: number | null;
  toolCount: number | null;
  totalTokens: number | null;
}

interface ThinkingMeterSignal {
  percent: number;
  tokenText: string;
  description: string;
  isApproximate: boolean;
}

interface AgentChatPanelProps {
  projectRoot: string | null;
  selectedTargets: string[];
}

const RUN_CANCELLED_MARKER = '__ATOPILE_AGENT_RUN_CANCELLED__';
const RUN_LOST_MARKER = '__ATOPILE_AGENT_RUN_LOST__';
const TRACE_DETAIL_LIMIT = 5;
const TRACE_INPUT_PREFERRED_KEYS = [
  'path',
  'query',
  'target',
  'targets',
  'name',
  'module',
  'build_id',
  'stage',
  'log_levels',
  'audience',
  'limit',
  'start_line',
  'max_lines',
  'entry',
  'old_path',
  'new_path',
];
const TRACE_OUTPUT_PREFERRED_KEYS = [
  'message',
  'path',
  'build_id',
  'build_target',
  'target',
  'status',
  'total',
  'count',
  'operations_applied',
  'first_changed_line',
  'error',
  'error_type',
];
const TRACE_RESULT_EXCLUDED_KEYS = new Set<string>(['_ui']);
const TOOL_TRACE_PREVIEW_COUNT = 5;
const CHAT_SNAPSHOTS_STORAGE_KEY = 'atopile.agentChatSnapshots.v1';
const ACTIVE_CHAT_STORAGE_KEY = 'atopile.agentActiveChatByProject.v1';
const MAX_PERSISTED_CHATS = 48;
const MAX_PERSISTED_MESSAGES_PER_CHAT = 120;
const MAX_PERSISTED_MESSAGE_CHARS = 12_000;
const MAX_PERSISTED_INPUT_CHARS = 4_000;
const THINKING_STREAM_MAX_ITEMS = 6;
const THINKING_PROXY_TOKEN_BUDGET = 6_000;
const PROGRESS_QUIET_THRESHOLD_SECONDS = 12;
const DEFAULT_LIVE_PROGRESS_STATE: AgentLiveProgressState = {
  phase: null,
  statusText: null,
  detailText: null,
  loop: null,
  toolIndex: null,
  toolCount: null,
  totalTokens: null,
};

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

function isValidMessageRole(value: unknown): value is MessageRole {
  return value === 'user' || value === 'assistant' || value === 'system';
}

function normalizeMessageForPersistence(value: unknown): AgentMessage | null {
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

function normalizeSnapshotForPersistence(value: unknown): AgentChatSnapshot | null {
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
    input,
    error: typeof candidate.error === 'string' ? candidate.error : null,
    activityLabel: resumedWithSession ? 'Ready' : 'Idle',
    createdAt,
    updatedAt,
  };
}

function parseStoredSnapshots(raw: string | null): AgentChatSnapshot[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as { chats?: unknown };
    const rawChats = Array.isArray(parsed?.chats) ? parsed.chats : [];
    const chats = rawChats
      .map((chat) => normalizeSnapshotForPersistence(chat))
      .filter((chat): chat is AgentChatSnapshot => Boolean(chat))
      .sort((left, right) => right.updatedAt - left.updatedAt)
      .slice(0, MAX_PERSISTED_CHATS);
    return chats;
  } catch {
    return [];
  }
}

function parseStoredActiveChats(raw: string | null): Record<string, string> {
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

interface TraceDetailsSummary {
  statusText: string;
  input: {
    text: string | null;
    hiddenCount: number;
  };
  output: {
    text: string | null;
    hiddenCount: number;
  };
}

function formatTracePreviewValue(value: unknown, maxLength = 88): string {
  if (value === null) return 'null';
  if (typeof value === 'undefined') return 'undefined';
  if (typeof value === 'string') {
    const compact = trimSingleLine(value, maxLength);
    return compact.length > 0 ? compact : '""';
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '[]';
    const preview = value
      .slice(0, 2)
      .map((item) => formatTracePreviewValue(item, Math.max(18, Math.floor(maxLength / 2))))
      .join(', ');
    return `[${preview}${value.length > 2 ? ', ...' : ''}] (${value.length})`;
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length === 0) return '{}';
    return `{${keys.slice(0, 3).join(', ')}${keys.length > 3 ? ', ...' : ''}}`;
  }
  return String(value);
}

function isTraceValuePresent(value: unknown): boolean {
  if (value == null) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  return true;
}

function collectTraceEntries(
  source: Record<string, unknown>,
  preferredKeys: string[],
  limit: number,
  excludedKeys?: Set<string>,
): {
  entries: Array<[string, unknown]>;
  hiddenCount: number;
} {
  const availableEntries = Object.entries(source).filter(([key, value]) => {
    if (excludedKeys?.has(key)) return false;
    return isTraceValuePresent(value);
  });
  if (availableEntries.length === 0 || limit < 1) {
    return { entries: [], hiddenCount: availableEntries.length };
  }

  const entriesByKey = new Map<string, unknown>(availableEntries);
  const selected: Array<[string, unknown]> = [];
  const selectedKeys = new Set<string>();

  for (const key of preferredKeys) {
    if (selected.length >= limit) break;
    if (!entriesByKey.has(key)) continue;
    selected.push([key, entriesByKey.get(key)]);
    selectedKeys.add(key);
  }

  for (const [key, value] of availableEntries) {
    if (selected.length >= limit) break;
    if (selectedKeys.has(key)) continue;
    selected.push([key, value]);
    selectedKeys.add(key);
  }

  return {
    entries: selected,
    hiddenCount: Math.max(0, availableEntries.length - selected.length),
  };
}

function summarizeTraceEntries(entries: Array<[string, unknown]>): string | null {
  if (entries.length === 0) return null;
  return entries
    .map(([key, value]) => `${key}: ${formatTracePreviewValue(value)}`)
    .join('  •  ');
}

function summarizeTraceDetails(trace: AgentTraceView): TraceDetailsSummary {
  const inputSelection = collectTraceEntries(
    trace.args,
    TRACE_INPUT_PREFERRED_KEYS,
    TRACE_DETAIL_LIMIT,
  );

  const outputSelection = collectTraceEntries(
    trace.result,
    TRACE_OUTPUT_PREFERRED_KEYS,
    TRACE_DETAIL_LIMIT,
    TRACE_RESULT_EXCLUDED_KEYS,
  );

  let outputHiddenCount = outputSelection.hiddenCount;
  const outputPreviewEntries = [...outputSelection.entries];

  if (trace.name === 'project_edit_file') {
    const editPayload = readTraceEditDiffPayload(trace);
    if (editPayload && !outputPreviewEntries.some(([key]) => key === 'path')) {
      if (outputPreviewEntries.length < TRACE_DETAIL_LIMIT) {
        outputPreviewEntries.unshift(['path', editPayload.path]);
      } else {
        outputHiddenCount += 1;
      }
    }
    const diff = readTraceDiff(trace);
    if (diff && !outputPreviewEntries.some(([key]) => key === 'diff')) {
      if (outputPreviewEntries.length < TRACE_DETAIL_LIMIT) {
        outputPreviewEntries.push(['diff', `+${diff.added} -${diff.removed}`]);
      } else {
        outputHiddenCount += 1;
      }
    }
  }

  return {
    statusText: trace.running ? 'running' : trace.ok ? 'ok' : 'failed',
    input: {
      text: summarizeTraceEntries(inputSelection.entries),
      hiddenCount: inputSelection.hiddenCount,
    },
    output: {
      text: summarizeTraceEntries(outputPreviewEntries),
      hiddenCount: outputHiddenCount,
    },
  };
}

function traceExpansionKey(messageId: string, trace: AgentTraceView, index: number): string {
  return `${messageId}:${trace.callId ?? `${trace.name}:${index}`}`;
}

function summarizeToolTrace(trace: AgentTraceView): string {
  if (trace.running) {
    return 'running...';
  }
  if (trace.ok) {
    if (trace.name === 'project_edit_file') {
      const diff = readTraceDiff(trace);
      const operationsApplied =
        typeof trace.result.operations_applied === 'number'
          ? trace.result.operations_applied
          : null;
      const firstChangedLine =
        typeof trace.result.first_changed_line === 'number'
          ? trace.result.first_changed_line
          : null;
      if (operationsApplied !== null && firstChangedLine !== null) {
        return `${operationsApplied} edits at line ${firstChangedLine}`;
      }
      if (operationsApplied !== null) {
        return `${operationsApplied} edits applied`;
      }
      if (diff) {
        return 'line changes';
      }
    }
    if (typeof trace.result.message === 'string') {
      return trace.result.message;
    }
    if (typeof trace.result.total === 'number') {
      return `${trace.result.total} items`;
    }
    return 'ok';
  }
  if (typeof trace.result.error === 'string') {
    return trace.result.error;
  }
  return 'failed';
}

function readProgressPayload(detail: unknown): {
  sessionId: string | null;
  runId: string | null;
  phase: AgentProgressPhase | null;
  callId: string | null;
  trace: AgentToolTrace | null;
  name: string | null;
  args: Record<string, unknown>;
  statusText: string | null;
  detailText: string | null;
  loop: number | null;
  toolIndex: number | null;
  toolCount: number | null;
  totalTokens: number | null;
} {
  if (!detail || typeof detail !== 'object') {
    return {
      sessionId: null,
      runId: null,
      phase: null,
      callId: null,
      trace: null,
      name: null,
      args: {},
      statusText: null,
      detailText: null,
      loop: null,
      toolIndex: null,
      toolCount: null,
      totalTokens: null,
    };
  }

  const payload = detail as AgentProgressPayload;
  const phase = normalizeProgressPhase(payload.phase);
  const sessionId = typeof payload.session_id === 'string' ? payload.session_id : null;
  const runId = typeof payload.run_id === 'string' ? payload.run_id : null;
  const callId = typeof payload.call_id === 'string' ? payload.call_id : null;
  const name = typeof payload.name === 'string' ? payload.name : null;
  const args = payload.args && typeof payload.args === 'object'
    ? payload.args as Record<string, unknown>
    : {};
  const statusText = typeof payload.status_text === 'string' ? payload.status_text : null;
  const detailText = typeof payload.detail_text === 'string' ? payload.detail_text : null;
  const loop = toFiniteNumber(payload.loop);
  const toolIndex = toFiniteNumber(payload.tool_index);
  const toolCount = toFiniteNumber(payload.tool_count);

  const usage = payload.usage && typeof payload.usage === 'object'
    ? payload.usage as Record<string, unknown>
    : null;
  const totalTokens = toFiniteNumber(payload.total_tokens)
    ?? (usage ? toFiniteNumber(usage.total_tokens) : null)
    ?? (usage ? toFiniteNumber(usage.totalTokens) : null)
    ?? ((() => {
      const input = toFiniteNumber(payload.input_tokens)
        ?? (usage ? toFiniteNumber(usage.input_tokens) : null)
        ?? (usage ? toFiniteNumber(usage.inputTokens) : null);
      const output = toFiniteNumber(payload.output_tokens)
        ?? (usage ? toFiniteNumber(usage.output_tokens) : null)
        ?? (usage ? toFiniteNumber(usage.outputTokens) : null);
      if (input === null && output === null) return null;
      return (input ?? 0) + (output ?? 0);
    })());

  const trace = payload.trace && typeof payload.trace === 'object'
    ? payload.trace as AgentToolTrace
    : null;

  return {
    sessionId,
    runId,
    phase,
    callId,
    trace,
    name,
    args,
    statusText,
    detailText,
    loop,
    toolIndex,
    toolCount,
    totalTokens,
  };
}

function readTraceDiff(trace: AgentTraceView): { added: number; removed: number } | null {
  const raw = trace.result.diff;
  if (!raw || typeof raw !== 'object') return null;
  const diff = raw as Record<string, unknown>;
  const added = typeof diff.added_lines === 'number' ? diff.added_lines : null;
  const removed = typeof diff.removed_lines === 'number' ? diff.removed_lines : null;
  if (added == null || removed == null) return null;
  return { added, removed };
}

function readTraceEditDiffPayload(trace: AgentTraceView): AgentEditDiffUiPayload | null {
  const rawUi = trace.result._ui;
  if (!rawUi || typeof rawUi !== 'object') return null;
  const ui = rawUi as Record<string, unknown>;
  const rawEditDiff = ui.edit_diff;
  if (!rawEditDiff || typeof rawEditDiff !== 'object') return null;
  const editDiff = rawEditDiff as Record<string, unknown>;

  const path = typeof editDiff.path === 'string' ? editDiff.path : null;
  const before = typeof editDiff.before_content === 'string' ? editDiff.before_content : null;
  const after = typeof editDiff.after_content === 'string' ? editDiff.after_content : null;

  if (!path || before == null || after == null) return null;
  return {
    path,
    before_content: before,
    after_content: after,
  };
}

function findMentionToken(input: string, caret: number): MentionToken | null {
  if (caret < 1 || caret > input.length) return null;

  let index = caret - 1;
  while (index >= 0) {
    const char = input[index];
    if (char === '@') {
      if (index > 0 && !/\s/.test(input[index - 1])) {
        return null;
      }
      const query = input.slice(index + 1, caret);
      if (/\s/.test(query)) return null;
      return { start: index, end: caret, query };
    }
    if (/\s/.test(char)) break;
    index -= 1;
  }
  return null;
}

function flattenFileNodes(nodes: FileTreeNode[] | undefined): string[] {
  if (!nodes || nodes.length === 0) return [];
  const files: string[] = [];
  const stack = [...nodes];
  while (stack.length > 0) {
    const node = stack.pop();
    if (!node) continue;
    if (node.type === 'file') {
      files.push(node.path);
      continue;
    }
    if (node.children && node.children.length > 0) {
      stack.push(...node.children);
    }
  }
  files.sort((left, right) => left.localeCompare(right));
  return files;
}

function scoreMention(label: string, query: string): number {
  if (!query) return 0;
  const lower = label.toLowerCase();
  const needle = query.toLowerCase();
  if (lower.startsWith(needle)) return 0;
  if (lower.includes(`/${needle}`)) return 1;
  if (lower.includes(needle)) return 2;
  return 9;
}

function normalizeMentionPath(path: string): string {
  return path.replace(/\\/g, '/').replace(/^\.?\//, '').toLowerCase();
}

function isDeprioritizedMentionPath(path: string): boolean {
  const normalized = normalizeMentionPath(path);
  const blockedRoots = ['parts/', '.ato/', 'node_modules/', '.git/', '.venv/'];
  for (const root of blockedRoots) {
    if (normalized.startsWith(root)) return true;
    if (normalized.includes(`/${root}`)) return true;
  }
  return false;
}

function fileMentionTypeRank(path: string): number {
  const normalized = normalizeMentionPath(path);
  if (normalized.endsWith('.ato')) return 0;
  if (
    normalized.endsWith('.py')
    || normalized.endsWith('.ts')
    || normalized.endsWith('.tsx')
    || normalized.endsWith('.js')
    || normalized.endsWith('.json')
    || normalized.endsWith('.yaml')
    || normalized.endsWith('.yml')
    || normalized.endsWith('.toml')
  ) {
    return 1;
  }
  return 2;
}

function mentionPathDepth(path: string): number {
  return normalizeMentionPath(path).split('/').filter(Boolean).length;
}

function formatCount(value: number, singular: string, plural: string): string {
  return `${value} ${value === 1 ? singular : plural}`;
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return value;
}

function normalizeProgressPhase(value: unknown): AgentProgressPhase | null {
  if (
    value === 'thinking'
    || value === 'tool_start'
    || value === 'tool_end'
    || value === 'done'
    || value === 'stopped'
    || value === 'error'
    || value === 'compacting'
  ) {
    return value;
  }
  return null;
}

function formatCompactTokenValue(value: number): string {
  if (value >= 10_000) return `${Math.round(value / 1_000)}k`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(Math.round(value));
}

function summarizePendingTraceActivity(trace: AgentTraceView): string {
  if (trace.running) {
    return inferToolActivityDetail(trace.name, trace.args);
  }
  if (!trace.ok) {
    const errorText = asNonEmptyString(trace.result.error);
    if (errorText) return `Failed: ${trimSingleLine(errorText, 46)}`;
    return `Failed ${trace.name}`;
  }
  if (trace.name === 'project_edit_file') {
    const path = asNonEmptyString(trace.result.path) ?? asNonEmptyString(trace.args.path);
    if (path) return `Edited ${compactPath(path)}`;
  }
  const message = asNonEmptyString(trace.result.message);
  if (message) return trimSingleLine(message, 46);
  return inferToolActivityDetail(trace.name, trace.args);
}

function buildThinkingThoughts(
  {
    isSessionLoading,
    isWorking,
    activityLabel,
    activityElapsedSeconds,
    progress,
    pendingTraces,
  }: {
    isSessionLoading: boolean;
    isWorking: boolean;
    activityLabel: string;
    activityElapsedSeconds: number;
    progress: AgentLiveProgressState;
    pendingTraces: AgentTraceView[];
  },
): string[] {
  if (!isSessionLoading && !isWorking) return [];
  const thoughts: string[] = [];

  if (isSessionLoading) {
    thoughts.push('Starting agent session');
  }

  if (progress.statusText || progress.detailText) {
    const status = progress.statusText
      ?? (progress.phase === 'compacting' ? 'Compacting context' : null)
      ?? 'Thinking';
    if (progress.detailText) {
      thoughts.push(`${status}: ${trimSingleLine(progress.detailText, 56)}`);
    } else {
      thoughts.push(status);
    }
  } else if (isWorking) {
    thoughts.push(activityLabel || 'Thinking');
  }

  if (progress.loop !== null) {
    const stepSummary = progress.toolCount !== null
      ? `Loop ${progress.loop} • tool ${Math.max(1, progress.toolIndex ?? 1)}/${Math.max(1, progress.toolCount)}`
      : `Loop ${progress.loop}`;
    thoughts.push(stepSummary);
  }

  pendingTraces
    .slice()
    .reverse()
    .slice(0, 3)
    .forEach((trace) => thoughts.push(summarizePendingTraceActivity(trace)));

  if (isWorking && activityElapsedSeconds > 0) {
    thoughts.push(`Working ${activityElapsedSeconds}s`);
  }

  const deduped = new Set<string>();
  const ordered: string[] = [];
  for (const thought of thoughts) {
    const compact = trimSingleLine(thought, 72);
    if (!compact || deduped.has(compact)) continue;
    deduped.add(compact);
    ordered.push(compact);
    if (ordered.length >= THINKING_STREAM_MAX_ITEMS) break;
  }
  return ordered.length > 0 ? ordered : ['Thinking...'];
}

function estimateThinkingMeterSignal(
  {
    isWorking,
    progress,
    pendingMessage,
    pendingTraces,
    activityElapsedSeconds,
  }: {
    isWorking: boolean;
    progress: AgentLiveProgressState;
    pendingMessage: AgentMessage | null;
    pendingTraces: AgentTraceView[];
    activityElapsedSeconds: number;
  },
): ThinkingMeterSignal {
  if (!isWorking) {
    return {
      percent: 0,
      tokenText: '0',
      description: 'Idle',
      isApproximate: true,
    };
  }

  if (progress.totalTokens !== null && progress.totalTokens > 0) {
    const budget = Math.max(THINKING_PROXY_TOKEN_BUDGET, Math.ceil(progress.totalTokens * 1.2));
    const percent = Math.max(6, Math.min(98, Math.round((progress.totalTokens / budget) * 100)));
    return {
      percent,
      tokenText: formatCompactTokenValue(progress.totalTokens),
      description: `${formatCompactTokenValue(progress.totalTokens)} tokens`,
      isApproximate: false,
    };
  }

  const messageChars = pendingMessage?.content.length ?? 0;
  const running = pendingTraces.filter((trace) => trace.running).length;
  const completed = pendingTraces.filter((trace) => !trace.running && trace.ok).length;
  const failed = pendingTraces.filter((trace) => !trace.running && !trace.ok).length;
  const loopBoost = progress.loop !== null ? Math.max(0, progress.loop - 1) * 190 : 0;
  const toolBoost =
    progress.toolCount !== null && progress.toolIndex !== null
      ? Math.max(0, Math.min(progress.toolCount, progress.toolIndex)) * 52
      : 0;

  const approximateTokens = Math.round(
    180
    + (messageChars * 0.38)
    + (activityElapsedSeconds * 6.5)
    + (running * 210)
    + (completed * 130)
    + (failed * 95)
    + loopBoost
    + toolBoost
  );
  const clamped = Math.max(72, Math.min(THINKING_PROXY_TOKEN_BUDGET, approximateTokens));
  const percent = Math.max(6, Math.min(98, Math.round((clamped / THINKING_PROXY_TOKEN_BUDGET) * 100)));
  return {
    percent,
    tokenText: `~${formatCompactTokenValue(clamped)}`,
    description: `~${formatCompactTokenValue(clamped)} token effort`,
    isApproximate: true,
  };
}

function renderLineDelta(added: number, removed: number, className?: string): JSX.Element {
  const classes = ['agent-line-delta'];
  if (className) classes.push(className);
  return (
    <span className={classes.join(' ')}>
      <span className="agent-line-added">+{added}</span>
      <span className="agent-line-removed">-{removed}</span>
    </span>
  );
}

function summarizeToolTraceGroup(traces: AgentTraceView[]): string {
  if (traces.length === 0) return 'No tool calls';
  const running = traces.filter((trace) => trace.running).length;
  const failed = traces.filter((trace) => !trace.running && !trace.ok).length;
  const completed = traces.filter((trace) => !trace.running && trace.ok).length;

  if (running > 0) {
    return `${formatCount(running, 'running', 'running')} • ${formatCount(completed, 'done', 'done')} • ${formatCount(failed, 'failed', 'failed')}`;
  }
  if (failed > 0) {
    return `${formatCount(completed, 'done', 'done')} • ${formatCount(failed, 'failed', 'failed')}`;
  }
  return `${formatCount(completed, 'completed', 'completed')}`;
}

function asNonEmptyString(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function compactPath(path: string): string {
  const normalized = path.replace(/\\/g, '/').replace(/^\.?\//, '');
  if (normalized.length <= 44) return normalized;
  const segments = normalized.split('/').filter(Boolean);
  if (segments.length <= 2) {
    return `...${normalized.slice(-41)}`;
  }
  return `.../${segments.slice(-2).join('/')}`;
}

function describeArgsTarget(args: Record<string, unknown>): string | null {
  const target = asNonEmptyString(args.target);
  if (target) return target;
  const targets = asStringList(args.targets);
  if (targets.length === 0) return null;
  if (targets.length === 1) return targets[0];
  return `${targets[0]} +${targets.length - 1}`;
}

function inferToolActivityDetail(toolName: string | null, args: Record<string, unknown>): string {
  if (!toolName) return 'Working';
  const path = asNonEmptyString(args.path);

  if (toolName === 'project_read_file') {
    return path ? `Reading ${compactPath(path)}` : 'Reading file';
  }
  if (toolName === 'project_edit_file') {
    return path ? `Editing ${compactPath(path)}` : 'Editing file';
  }
  if (toolName === 'project_search') {
    const query = asNonEmptyString(args.query);
    return query ? `Searching "${trimSingleLine(query, 30)}"` : 'Searching project';
  }
  if (toolName === 'web_search') {
    const query = asNonEmptyString(args.query);
    return query ? `Searching web for "${trimSingleLine(query, 26)}"` : 'Searching web';
  }
  if (toolName === 'project_list_modules') {
    return 'Scanning modules';
  }
  if (toolName === 'project_module_children') {
    const entry = asNonEmptyString(args.entry);
    return entry ? `Inspecting ${trimSingleLine(entry, 36)}` : 'Inspecting module';
  }
  if (toolName === 'project_rename_path') {
    const oldPath = asNonEmptyString(args.old_path);
    const newPath = asNonEmptyString(args.new_path);
    if (oldPath && newPath) {
      return `Renaming ${compactPath(oldPath)} -> ${compactPath(newPath)}`;
    }
    return 'Renaming path';
  }
  if (toolName === 'project_delete_path') {
    return path ? `Deleting ${compactPath(path)}` : 'Deleting path';
  }
  if (toolName === 'build_run') {
    const target = describeArgsTarget(args);
    return target ? `Running build ${trimSingleLine(target, 28)}` : 'Running build';
  }
  if (toolName === 'build_logs_search') {
    const buildId = asNonEmptyString(args.queued_build_id) ?? asNonEmptyString(args.build_id);
    return buildId ? `Checking logs ${trimSingleLine(buildId, 22)}` : 'Checking build logs';
  }
  if (toolName === 'report_bom') {
    const target = describeArgsTarget(args);
    return target ? `Loading BOM ${trimSingleLine(target, 28)}` : 'Loading BOM';
  }
  if (toolName === 'report_variables') {
    const target = describeArgsTarget(args);
    return target ? `Loading variables ${trimSingleLine(target, 28)}` : 'Loading variables';
  }
  if (toolName === 'design_diagnostics') {
    return 'Running diagnostics';
  }
  if (toolName === 'parts_search' || toolName === 'packages_search') {
    const query = asNonEmptyString(args.query);
    return query ? `Searching "${trimSingleLine(query, 30)}"` : inferActivityFromTool(toolName);
  }
  if (toolName === 'parts_install' || toolName === 'packages_install') {
    const name = asNonEmptyString(args.name) ?? asNonEmptyString(args.identifier);
    return name ? `Installing ${trimSingleLine(name, 30)}` : inferActivityFromTool(toolName);
  }
  if (toolName === 'datasheet_read') {
    const lcscId = asNonEmptyString(args.lcsc_id);
    if (lcscId) return `Reading datasheet ${lcscId}`;
    const query = asNonEmptyString(args.query);
    return query ? `Reading datasheet "${trimSingleLine(query, 26)}"` : 'Reading datasheet';
  }
  if (toolName === 'layout_get_component_position') {
    const address = asNonEmptyString(args.address);
    return address ? `Locating ${trimSingleLine(address, 30)}` : 'Locating component';
  }
  if (toolName === 'layout_set_component_position') {
    const address = asNonEmptyString(args.address);
    const mode = asNonEmptyString(args.mode);
    if (address && mode === 'relative') {
      return `Nudging ${trimSingleLine(address, 30)}`;
    }
    if (address) {
      return `Placing ${trimSingleLine(address, 30)}`;
    }
    return 'Updating placement';
  }

  return inferActivityFromTool(toolName);
}

function inferActivityFromTool(toolName: string | null): string {
  if (!toolName) return 'Working';
  if (toolName.startsWith('project_') || toolName.startsWith('stdlib_')) {
    if (toolName === 'project_edit_file' || toolName === 'project_rename_path' || toolName === 'project_delete_path') {
      return 'Editing';
    }
    return 'Exploring';
  }
  if (toolName.startsWith('build_')) {
    return toolName === 'build_logs_search' ? 'Reviewing' : 'Building';
  }
  if (toolName === 'parts_search' || toolName === 'packages_search') {
    return 'Researching';
  }
  if (toolName === 'web_search') {
    return 'Researching';
  }
  if (toolName === 'parts_install' || toolName === 'packages_install') {
    return 'Installing';
  }
  if (toolName === 'report_bom' || toolName === 'report_variables' || toolName === 'manufacturing_summary' || toolName === 'design_diagnostics') {
    return 'Reviewing';
  }
  if (toolName.startsWith('layout_')) {
    return toolName === 'layout_set_component_position' ? 'Placing' : 'Inspecting';
  }
  return 'Working';
}

function inferActivityFromProgress(
  payload: {
    phase: AgentProgressPhase | null;
    name: string | null;
    args: Record<string, unknown>;
    trace: AgentToolTrace | null;
    statusText: string | null;
    detailText: string | null;
  },
): string | null {
  if (payload.phase === 'thinking') {
    const status = payload.statusText || 'Thinking';
    if (payload.detailText) {
      return `${status}: ${trimSingleLine(payload.detailText, 36)}`;
    }
    return status;
  }
  if (payload.phase === 'compacting') {
    const status = payload.statusText || 'Compacting context';
    if (payload.detailText) {
      return `${status}: ${trimSingleLine(payload.detailText, 36)}`;
    }
    return status;
  }
  if (payload.phase === 'tool_start') {
    return inferToolActivityDetail(payload.name, payload.args);
  }
  if (payload.phase === 'tool_end' && payload.trace) {
    if (!payload.trace.ok) {
      const error = asNonEmptyString(payload.trace.result.error);
      if (error) {
        return `Failed: ${trimSingleLine(error, 42)}`;
      }
      return `Failed ${payload.trace.name}`;
    }
    if (payload.trace.name === 'project_edit_file') {
      const pathFromArgs = asNonEmptyString(payload.trace.args.path);
      const pathFromResult = asNonEmptyString(payload.trace.result.path);
      const path = pathFromArgs || pathFromResult;
      const diff = payload.trace.result.diff;
      if (path) {
        if (diff && typeof diff === 'object') {
          const added = typeof (diff as Record<string, unknown>).added_lines === 'number'
            ? (diff as Record<string, unknown>).added_lines as number
            : null;
          const removed = typeof (diff as Record<string, unknown>).removed_lines === 'number'
            ? (diff as Record<string, unknown>).removed_lines as number
            : null;
          if (added !== null && removed !== null) {
            return `Edited ${compactPath(path)} (+${added}/-${removed})`;
          }
        }
        return `Edited ${compactPath(path)}`;
      }
    }
    const resultMessage = asNonEmptyString(payload.trace.result.message);
    if (resultMessage) {
      return trimSingleLine(resultMessage, 46);
    }
    return inferToolActivityDetail(payload.trace.name, payload.trace.args);
  }
  if (payload.phase === 'error') return 'Errored';
  if (payload.phase === 'done') return 'Complete';
  if (payload.phase === 'stopped') return 'Stopped';
  return null;
}

function applyProgressToMessages(
  previous: AgentMessage[],
  pendingId: string,
  parsed: ReturnType<typeof readProgressPayload>,
  nextActivity: string | null,
): AgentMessage[] {
  return previous.map((message) => {
    if (message.id !== pendingId) return message;

    const traces = [...(message.toolTraces ?? [])];

    if (parsed.phase === 'tool_start') {
      if (!parsed.callId || !parsed.name) {
        return message;
      }
      const index = traces.findIndex((trace) => trace.callId === parsed.callId);
      const runningTrace: AgentTraceView = {
        callId: parsed.callId,
        name: parsed.name,
        args: parsed.args,
        ok: true,
        result: { message: 'running' },
        running: true,
      };
      if (index >= 0) {
        traces[index] = runningTrace;
      } else {
        traces.push(runningTrace);
      }
      const nextContent = nextActivity ? `${nextActivity}...` : message.content;
      return {
        ...message,
        content: nextContent,
        activity: nextActivity ?? message.activity,
        toolTraces: traces,
      };
    }

    if (parsed.phase === 'tool_end') {
      if (!parsed.trace) {
        return message;
      }
      const finishedTrace: AgentTraceView = {
        ...parsed.trace,
        callId: parsed.callId ?? undefined,
        running: false,
      };
      const index = parsed.callId
        ? traces.findIndex((trace) => trace.callId === parsed.callId)
        : -1;
      if (index >= 0) {
        traces[index] = finishedTrace;
      } else {
        traces.push(finishedTrace);
      }
      const nextContent = nextActivity ? `${nextActivity}...` : message.content;
      return {
        ...message,
        content: nextContent,
        activity: nextActivity ?? message.activity,
        toolTraces: traces,
      };
    }

    if (parsed.phase === 'error') {
      return {
        ...message,
        pending: false,
      };
    }

    if (parsed.phase === 'thinking') {
      const nextContent = nextActivity ? `${nextActivity}...` : message.content;
      return {
        ...message,
        content: nextContent,
        activity: nextActivity ?? message.activity,
      };
    }

    if (parsed.phase === 'done' || parsed.phase === 'stopped') {
      return {
        ...message,
        pending: false,
      };
    }

    return message;
  });
}

function suggestNextAction(traces: AgentTraceView[]): string | null {
  const hasEdits = traces.some((trace) => trace.ok && trace.name === 'project_edit_file');
  const hasBuildRun = traces.some((trace) => trace.ok && trace.name === 'build_run');
  const hasInstall = traces.some((trace) => trace.ok && (trace.name === 'parts_install' || trace.name === 'packages_install'));
  const hasBuildLogs = traces.some((trace) => trace.ok && trace.name === 'build_logs_search');

  if (hasEdits && !hasBuildRun) return 'run a build to validate those changes';
  if (hasBuildRun && !hasBuildLogs) return 'review the latest build logs and summarize any issues';
  if (hasInstall) return 'wire that dependency into the target module and run a verification build';
  return null;
}

function withCompletionNudge(text: string, traces: AgentTraceView[]): string {
  const base = text.trim();
  const nextStep = suggestNextAction(traces);
  const hasPrompt = /\bwould you like me to\b/i.test(base) || /\?\s*$/.test(base);

  const additions: string[] = [];
  if (nextStep && !hasPrompt) additions.push(`Would you like me to ${nextStep}?`);

  if (additions.length === 0) return text;
  if (!base) return additions.join('\n');
  return `${base}\n\n${additions.join('\n')}`;
}

function collectChangedFilesSummary(messages: AgentMessage[]): AgentChangedFilesSummary | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role !== 'assistant' || !message.toolTraces || message.toolTraces.length === 0) continue;

    const byPath = new Map<string, AgentChangedFile>();
    for (const trace of message.toolTraces) {
      if (trace.name !== 'project_edit_file' || !trace.ok) continue;
      const payload = readTraceEditDiffPayload(trace);
      if (!payload) continue;
      const diff = readTraceDiff(trace) ?? { added: 0, removed: 0 };
      const existing = byPath.get(payload.path);
      if (existing) {
        existing.added += diff.added;
        existing.removed += diff.removed;
        continue;
      }
      byPath.set(payload.path, {
        path: payload.path,
        added: diff.added,
        removed: diff.removed,
        payload,
      });
    }

    if (byPath.size === 0) continue;
    const files = [...byPath.values()].sort((left, right) => left.path.localeCompare(right.path));
    const totalAdded = files.reduce((sum, file) => sum + file.added, 0);
    const totalRemoved = files.reduce((sum, file) => sum + file.removed, 0);
    return {
      messageId: message.id,
      files,
      totalAdded,
      totalRemoved,
    };
  }

  return null;
}

function compactBuildId(buildId: string): string {
  const numbered = buildId.match(/^build-(\d+)-/);
  if (numbered) return `#${numbered[1]}`;
  if (buildId.length <= 12) return buildId;
  return `${buildId.slice(0, 8)}...`;
}

function extractBuildRunReferences(traces: AgentTraceView[]): BuildRunReferences {
  const buildIds: string[] = [];
  const targets: string[] = [];
  const seenBuildIds = new Set<string>();
  const seenTargets = new Set<string>();
  let hasBuildRun = false;
  let hasRunningBuildRun = false;

  const addBuildId = (value: unknown) => {
    if (typeof value !== 'string') return;
    const trimmed = value.trim();
    if (!trimmed || seenBuildIds.has(trimmed)) return;
    seenBuildIds.add(trimmed);
    buildIds.push(trimmed);
  };

  const addTarget = (value: unknown) => {
    if (typeof value !== 'string') return;
    const trimmed = value.trim();
    if (!trimmed || seenTargets.has(trimmed)) return;
    seenTargets.add(trimmed);
    targets.push(trimmed);
  };

  for (const trace of traces) {
    if (trace.name !== 'build_run') continue;
    hasBuildRun = true;
    if (trace.running) hasRunningBuildRun = true;

    addBuildId(trace.result.build_id);
    addBuildId(trace.result.buildId);
    addTarget(trace.result.target);
    addTarget(trace.result.build_target);

    const candidateGroups = [trace.result.build_targets, trace.result.buildTargets];
    for (const group of candidateGroups) {
      if (!Array.isArray(group)) continue;
      for (const row of group) {
        if (!row || typeof row !== 'object') continue;
        const candidate = row as Record<string, unknown>;
        addBuildId(candidate.build_id);
        addBuildId(candidate.buildId);
        addTarget(candidate.target);
      }
    }

    if (Array.isArray(trace.args.targets)) {
      for (const target of trace.args.targets) {
        addTarget(target);
      }
    }
  }

  return {
    hasBuildRun,
    hasRunningBuildRun,
    buildIds,
    targets,
  };
}

function buildStatusRank(status: string): number {
  if (status === 'building') return 0;
  if (status === 'queued') return 1;
  if (status === 'failed') return 2;
  if (status === 'warning') return 3;
  if (status === 'success') return 4;
  if (status === 'cancelled') return 5;
  return 6;
}

function sortBuildsForChat(left: Build, right: Build): number {
  const statusDiff = buildStatusRank(left.status) - buildStatusRank(right.status);
  if (statusDiff !== 0) return statusDiff;

  const leftStarted = typeof left.startedAt === 'number' ? left.startedAt : 0;
  const rightStarted = typeof right.startedAt === 'number' ? right.startedAt : 0;
  if (leftStarted !== rightStarted) return rightStarted - leftStarted;

  return (left.target || left.name || '').localeCompare(right.target || right.name || '');
}

function normalizeQueuedBuild(build: Build, projectRoot: string): QueuedBuild | null {
  if (typeof build.buildId !== 'string' || !build.buildId) return null;
  const status = build.status as QueuedBuild['status'];
  const validStatuses: QueuedBuild['status'][] = [
    'queued',
    'building',
    'success',
    'failed',
    'warning',
    'cancelled',
  ];
  if (!validStatuses.includes(status)) return null;

  return {
    buildId: build.buildId,
    status,
    projectRoot: build.projectRoot || projectRoot,
    target: build.target || build.name || 'default',
    entry: build.entry,
    startedAt: typeof build.startedAt === 'number' ? build.startedAt : 0,
    elapsedSeconds: build.elapsedSeconds,
    stages: Array.isArray(build.stages)
      ? build.stages.map((stage) => ({
          name: stage.name,
          stageId: stage.stageId,
          displayName: stage.displayName,
          status: stage.status,
          elapsedSeconds: stage.elapsedSeconds,
        }))
      : undefined,
    totalStages: build.totalStages,
    error: build.error,
  };
}

function resolveBuildStatusForTraces(
  traces: AgentTraceView[],
  projectBuilds: Build[],
  projectRoot: string,
): {
  hasBuildRun: boolean;
  builds: QueuedBuild[];
  pendingBuildIds: string[];
} {
  const references = extractBuildRunReferences(traces);
  if (!references.hasBuildRun) {
    return { hasBuildRun: false, builds: [], pendingBuildIds: [] };
  }

  const buildsById = new Map<string, Build>();
  for (const build of projectBuilds) {
    if (typeof build.buildId !== 'string' || !build.buildId) continue;
    buildsById.set(build.buildId, build);
  }

  const targetSet = new Set(references.targets);
  const selected: Build[] = [];
  const selectedIds = new Set<string>();
  const addBuild = (build: Build) => {
    const buildId = typeof build.buildId === 'string' ? build.buildId : null;
    if (!buildId || selectedIds.has(buildId)) return;
    selectedIds.add(buildId);
    selected.push(build);
  };

  for (const buildId of references.buildIds) {
    const matched = buildsById.get(buildId);
    if (matched) addBuild(matched);
  }

  if (targetSet.size > 0) {
    for (const build of projectBuilds) {
      if (!targetSet.has(build.target || '')) continue;
      addBuild(build);
    }
  }

  if (selected.length === 0 && references.hasRunningBuildRun) {
    for (const build of projectBuilds) {
      if (build.status === 'queued' || build.status === 'building') {
        addBuild(build);
      }
    }
  }

  selected.sort(sortBuildsForChat);
  const builds = selected
    .map((build) => normalizeQueuedBuild(build, projectRoot))
    .filter((build): build is QueuedBuild => Boolean(build));

  const matchedBuildIds = new Set(builds.map((build) => build.buildId));
  const pendingBuildIds = references.buildIds.filter((buildId) => !matchedBuildIds.has(buildId));

  return {
    hasBuildRun: true,
    builds,
    pendingBuildIds,
  };
}

export function AgentChatPanel({ projectRoot, selectedTargets }: AgentChatPanelProps) {
  const minimizedDockHeight = 54;
  const defaultDockHeight = useMemo(() => {
    if (typeof window === 'undefined') return 460;
    const maxHeight = Math.floor(window.innerHeight * 0.78);
    return Math.max(320, Math.min(520, maxHeight));
  }, []);
  const [chatSnapshots, setChatSnapshots] = useState<AgentChatSnapshot[]>([]);
  const [isSnapshotsHydrated, setIsSnapshotsHydrated] = useState(false);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [isChatsPanelOpen, setIsChatsPanelOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activityLabel, setActivityLabel] = useState<string>('Idle');
  const [activityElapsedSeconds, setActivityElapsedSeconds] = useState(0);
  const [liveProgress, setLiveProgress] = useState<AgentLiveProgressState>(DEFAULT_LIVE_PROGRESS_STATE);
  const [lastProgressAt, setLastProgressAt] = useState<number | null>(null);
  const [dockHeight, setDockHeight] = useState<number>(defaultDockHeight);
  const [isMinimized, setIsMinimized] = useState(false);
  const [changesExpanded, setChangesExpanded] = useState(false);
  const [expandedTraceGroups, setExpandedTraceGroups] = useState<Set<string>>(new Set());
  const [expandedTraceKeys, setExpandedTraceKeys] = useState<Set<string>>(new Set());
  const [resizingDock, setResizingDock] = useState(false);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const composerInputRef = useRef<HTMLTextAreaElement | null>(null);
  const chatsPanelRef = useRef<HTMLDivElement | null>(null);
  const chatsPanelToggleRef = useRef<HTMLButtonElement | null>(null);
  const chatSnapshotsRef = useRef<AgentChatSnapshot[]>([]);
  const activeChatIdRef = useRef<string | null>(null);
  const activeChatByProjectRef = useRef<Record<string, string>>({});
  const activityStartedAtRef = useRef<number | null>(null);
  const resizeStartRef = useRef<{ y: number; height: number } | null>(null);
  const [mentionToken, setMentionToken] = useState<MentionToken | null>(null);
  const [mentionIndex, setMentionIndex] = useState(0);

  const projectModules = useStore((state) =>
    projectRoot ? state.projectModules[projectRoot] ?? [] : []
  );
  const projectFileNodes = useStore((state) =>
    projectRoot ? state.projectFiles[projectRoot] ?? [] : []
  );
  const queuedBuilds = useStore((state) => state.queuedBuilds);
  const setProjectModules = useStore((state) => state.setProjectModules);
  const setProjectFiles = useStore((state) => state.setProjectFiles);

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
  const isWorking = isSending || isStopping;
  const pendingAssistantMessage = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role === 'assistant' && message.pending) {
        return message;
      }
    }
    return null;
  }, [messages]);
  const pendingTraces = pendingAssistantMessage?.toolTraces ?? [];
  const thinkingThoughts = useMemo(
    () => buildThinkingThoughts({
      isSessionLoading,
      isWorking,
      activityLabel,
      activityElapsedSeconds,
      progress: liveProgress,
      pendingTraces,
    }),
    [
      activityElapsedSeconds,
      activityLabel,
      isSessionLoading,
      isWorking,
      liveProgress,
      pendingTraces,
    ],
  );
  const thinkingMeterSignal = useMemo(
    () => estimateThinkingMeterSignal({
      isWorking: isSessionLoading || isWorking,
      progress: liveProgress,
      pendingMessage: pendingAssistantMessage,
      pendingTraces,
      activityElapsedSeconds,
    }),
    [
      activityElapsedSeconds,
      isSessionLoading,
      isWorking,
      liveProgress,
      pendingAssistantMessage,
      pendingTraces,
    ],
  );
  const progressSilenceSeconds = (isSessionLoading || isWorking) && lastProgressAt
    ? Math.max(0, Math.floor((Date.now() - lastProgressAt) / 1000))
    : 0;
  const isProgressQuiet = progressSilenceSeconds >= PROGRESS_QUIET_THRESHOLD_SECONDS;
  const headerTitle = useMemo(() => shortProjectName(projectRoot), [projectRoot]);
  const activeChatTitle = activeChatSnapshot?.title ?? DEFAULT_CHAT_TITLE;
  const projectFiles = useMemo(() => flattenFileNodes(projectFileNodes), [projectFileNodes]);
  const changedFilesSummary = useMemo(() => collectChangedFilesSummary(messages), [messages]);
  const projectQueuedBuilds = useMemo(() => {
    if (!projectRoot) return [];
    return queuedBuilds.filter((build) => build.projectRoot === projectRoot);
  }, [queuedBuilds, projectRoot]);
  const latestBuildStatus = useMemo((): MessageBuildStatusState | null => {
    if (!projectRoot) return null;

    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role !== 'assistant' || !message.toolTraces || message.toolTraces.length === 0) {
        continue;
      }

      const resolved = resolveBuildStatusForTraces(
        message.toolTraces,
        projectQueuedBuilds,
        projectRoot,
      );
      if (!resolved.hasBuildRun) continue;
      return {
        messageId: message.id,
        builds: resolved.builds,
        pendingBuildIds: resolved.pendingBuildIds,
      };
    }

    return null;
  }, [messages, projectQueuedBuilds, projectRoot]);

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
    activeChatByProjectRef.current = {
      ...activeChatByProjectRef.current,
      [projectRoot]: activeChatId,
    };
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(
        ACTIVE_CHAT_STORAGE_KEY,
        JSON.stringify(activeChatByProjectRef.current),
      );
    } catch {
      // Ignore storage failures; active chat defaults to most recent.
    }
  }, [activeChatId, isSnapshotsHydrated, projectRoot]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsSnapshotsHydrated(true);
      return;
    }
    const restoredChats = parseStoredSnapshots(
      window.localStorage.getItem(CHAT_SNAPSHOTS_STORAGE_KEY),
    );
    const restoredActiveByProject = parseStoredActiveChats(
      window.localStorage.getItem(ACTIVE_CHAT_STORAGE_KEY),
    );
    setChatSnapshots(restoredChats);
    activeChatByProjectRef.current = restoredActiveByProject;
    setIsSnapshotsHydrated(true);
  }, []);

  useEffect(() => {
    if (!isSnapshotsHydrated || typeof window === 'undefined') return;

    const persistedChats = chatSnapshots
      .map((chat) => normalizeSnapshotForPersistence(chat))
      .filter((chat): chat is AgentChatSnapshot => Boolean(chat))
      .sort((left, right) => right.updatedAt - left.updatedAt)
      .slice(0, MAX_PERSISTED_CHATS);
    const payload = {
      version: 1,
      chats: persistedChats,
    };

    try {
      window.localStorage.setItem(
        CHAT_SNAPSHOTS_STORAGE_KEY,
        JSON.stringify(payload),
      );
    } catch {
      const trimmedPayload = {
        version: 1,
        chats: persistedChats.slice(0, 16).map((chat) => ({
          ...chat,
          messages: chat.messages.slice(-40),
        })),
      };
      try {
        window.localStorage.setItem(
          CHAT_SNAPSHOTS_STORAGE_KEY,
          JSON.stringify(trimmedPayload),
        );
      } catch {
        // Ignore storage failures; chat remains fully functional in-memory.
      }
    }

    const activeMap = { ...activeChatByProjectRef.current };
    const validProjectRoots = new Set(persistedChats.map((chat) => chat.projectRoot));
    Object.keys(activeMap).forEach((root) => {
      if (!validProjectRoots.has(root)) {
        delete activeMap[root];
      }
    });
    activeChatByProjectRef.current = activeMap;
    try {
      window.localStorage.setItem(
        ACTIVE_CHAT_STORAGE_KEY,
        JSON.stringify(activeMap),
      );
    } catch {
      // Ignore storage failures; active chat defaults to most recent.
    }
  }, [chatSnapshots, isSnapshotsHydrated]);

  const resetChatUiState = useCallback(() => {
    setMentionToken(null);
    setMentionIndex(0);
    setChangesExpanded(false);
    setExpandedTraceGroups(new Set());
    setExpandedTraceKeys(new Set());
    setLiveProgress(DEFAULT_LIVE_PROGRESS_STATE);
    setLastProgressAt(null);
    activityStartedAtRef.current = null;
  }, []);

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
      setLastProgressAt(Date.now());
      setLiveProgress({
        ...DEFAULT_LIVE_PROGRESS_STATE,
        phase: 'thinking',
        statusText: snapshot.activityLabel || 'Thinking',
      });
    }
  }, [resetChatUiState]);

  const upsertSnapshot = useCallback((snapshot: AgentChatSnapshot) => {
    setChatSnapshots((previous) => {
      const index = previous.findIndex((chat) => chat.id === snapshot.id);
      if (index < 0) {
        return [snapshot, ...previous];
      }
      const next = [...previous];
      next[index] = {
        ...previous[index],
        ...snapshot,
        createdAt: previous[index].createdAt,
      };
      return next;
    });
  }, []);

  const updateChatSnapshot = useCallback(
    (chatId: string, updater: (chat: AgentChatSnapshot) => AgentChatSnapshot) => {
      setChatSnapshots((previous) => {
        const index = previous.findIndex((chat) => chat.id === chatId);
        if (index < 0) return previous;
        const current = previous[index];
        const updated = updater(current);
        const next = [...previous];
        next[index] = {
          ...updated,
          createdAt: current.createdAt,
          updatedAt: Date.now(),
        };
        return next;
      });
    },
    [],
  );

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
        input: '',
        error: message,
        activityLabel: 'Idle',
        createdAt: Date.now(),
        updatedAt: Date.now(),
      });
    }
  }, [upsertSnapshot]);

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
      input: '',
      error: null,
      activityLabel: 'Starting',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    void startChatSession(chatId, root);
  }, [resetChatUiState, startChatSession, upsertSnapshot]);

  const activateChat = useCallback((chatId: string) => {
    const snapshot = chatSnapshotsRef.current.find((chat) => chat.id === chatId);
    if (!snapshot) return;
    setActiveChatId(chatId);
    loadSnapshotIntoView(snapshot);
    setIsChatsPanelOpen(false);
  }, [loadSnapshotIntoView]);

  useEffect(() => {
    if (!activeChatId || !projectRoot) return;
    const liveSnapshot = chatSnapshotsRef.current.find((chat) => chat.id === activeChatId);
    if (liveSnapshot && liveSnapshot.projectRoot !== projectRoot) return;
    const nextTitle = deriveChatTitle(messages);
    setChatSnapshots((previous) => {
      const index = previous.findIndex((chat) => chat.id === activeChatId);
      const now = Date.now();
      if (index < 0) {
        return [
          {
            id: activeChatId,
            projectRoot,
            title: nextTitle,
            sessionId,
            isSessionLoading,
            isSending,
            isStopping,
            activeRunId,
            pendingRunId: null,
            pendingAssistantId: null,
            cancelRequested: false,
            activityElapsedSeconds,
            messages,
            input,
            error,
            activityLabel,
            createdAt: now,
            updatedAt: now,
          },
          ...previous,
        ];
      }

      const current = previous[index];
      const updated: AgentChatSnapshot = {
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
        updatedAt: now,
      };

      const next = [...previous];
      next[index] = updated;
      return next;
    });
  }, [
    activeChatId,
    activeRunId,
    activityElapsedSeconds,
    activityLabel,
    error,
    input,
    isSending,
    isSessionLoading,
    isStopping,
    messages,
    projectRoot,
    sessionId,
  ]);

  useEffect(() => {
    setIsChatsPanelOpen(false);
  }, [activeChatId, projectRoot]);

  useEffect(() => {
    if (!changedFilesSummary) {
      setChangesExpanded(false);
    }
  }, [changedFilesSummary]);

  const mentionItems = useMemo((): MentionItem[] => {
    if (!mentionToken) return [];
    const query = mentionToken.query.trim().toLowerCase();

    const moduleItems = projectModules
      .map((moduleEntry: ModuleDefinition): MentionItem => ({
        kind: 'module',
        label: moduleEntry.entry,
        token: moduleEntry.entry,
        subtitle: moduleEntry.type,
      }))
      .filter((item) =>
        !query || item.label.toLowerCase().includes(query)
      );

    const fileItems = projectFiles
      .map((path): MentionItem => ({
        kind: 'file',
        label: path,
        token: path,
      }))
      .filter((item) => {
        const normalized = normalizeMentionPath(item.label);
        const deprioritized = isDeprioritizedMentionPath(item.label);
        if (!query) {
          // Default suggestions should favor user source files.
          return !deprioritized;
        }
        if (!normalized.includes(query)) return false;
        // Keep deprioritized paths available only when explicitly matched.
        return !deprioritized || normalized.includes(query);
      });

    const combined: MentionItem[] = [...moduleItems, ...fileItems];
    const deduped = new Map<string, MentionItem>();
    for (const item of combined) {
      const key = `${item.kind}:${item.token}`;
      if (!deduped.has(key)) {
        deduped.set(key, item);
      }
    }

    return [...deduped.values()]
      .sort((left, right) => {
        const kindDiff = (left.kind === 'module' ? 0 : 1) - (right.kind === 'module' ? 0 : 1);
        if (kindDiff !== 0) return kindDiff;

        if (left.kind === 'file' && right.kind === 'file') {
          const deprioritizedDiff = Number(isDeprioritizedMentionPath(left.label)) - Number(isDeprioritizedMentionPath(right.label));
          if (deprioritizedDiff !== 0) return deprioritizedDiff;

          const fileTypeDiff = fileMentionTypeRank(left.label) - fileMentionTypeRank(right.label);
          if (fileTypeDiff !== 0) return fileTypeDiff;
        }

        const scoreDiff = scoreMention(left.label, query) - scoreMention(right.label, query);
        if (scoreDiff !== 0) return scoreDiff;

        const depthDiff = mentionPathDepth(left.label) - mentionPathDepth(right.label);
        if (depthDiff !== 0) return depthDiff;

        return left.label.localeCompare(right.label);
      })
      .slice(0, 12);
  }, [mentionToken, projectModules, projectFiles]);

  useEffect(() => {
    if (mentionItems.length === 0) {
      setMentionIndex(0);
      return;
    }
    setMentionIndex((current) => Math.min(current, mentionItems.length - 1));
  }, [mentionItems.length]);

  useEffect(() => {
    const element = messagesRef.current;
    if (!element) return;
    element.scrollTop = element.scrollHeight;
  }, [messages, isSending]);

  useEffect(() => {
    setMentionToken(null);
    setMentionIndex(0);
    setExpandedTraceGroups(new Set());
    setExpandedTraceKeys(new Set());
  }, [activeChatId, projectRoot]);

  useEffect(() => {
    const activeTraceGroupKeys = new Set<string>();
    const activeTraceKeys = new Set<string>();
    for (const message of messages) {
      if (!message.toolTraces || message.toolTraces.length === 0) continue;
      activeTraceGroupKeys.add(message.id);
      message.toolTraces.forEach((trace, index) => {
        activeTraceKeys.add(traceExpansionKey(message.id, trace, index));
      });
    }

    setExpandedTraceGroups((previous) => {
      if (previous.size === 0) return previous;
      const next = new Set<string>();
      previous.forEach((groupKey) => {
        if (activeTraceGroupKeys.has(groupKey)) {
          next.add(groupKey);
        }
      });

      if (next.size !== previous.size) return next;
      for (const groupKey of previous) {
        if (!next.has(groupKey)) return next;
      }
      return previous;
    });

    setExpandedTraceKeys((previous) => {
      if (previous.size === 0) return previous;
      const next = new Set<string>();
      previous.forEach((traceKey) => {
        if (activeTraceKeys.has(traceKey)) {
          next.add(traceKey);
        }
      });

      if (next.size !== previous.size) return next;
      for (const traceKey of previous) {
        if (!next.has(traceKey)) return next;
      }
      return previous;
    });
  }, [messages]);

  useEffect(() => {
    if (!projectRoot) return;
    if (projectModules.length > 0) return;
    let cancelled = false;

    void api.modules.list(projectRoot)
      .then((result) => {
        if (cancelled) return;
        setProjectModules(projectRoot, result.modules || []);
      })
      .catch(() => {
        // Silent fallback: module mentions will still work if modules load elsewhere.
      });

    return () => {
      cancelled = true;
    };
  }, [projectRoot, projectModules.length, setProjectModules]);

  useEffect(() => {
    if (!projectRoot) return;
    const handleMessage = (event: MessageEvent) => {
      const message = event.data as {
        type?: string;
        projectRoot?: string;
        files?: FileTreeNode[];
      };
      if (message?.type !== 'filesListed') return;
      if (message.projectRoot !== projectRoot) return;
      setProjectFiles(projectRoot, message.files || []);
    };

    window.addEventListener('message', handleMessage);
    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, [projectRoot, setProjectFiles]);

  useEffect(() => {
    if (!projectRoot) return;
    if (projectFileNodes.length > 0) return;
    postMessage({
      type: 'listFiles',
      projectRoot,
      includeAll: true,
    });
  }, [projectRoot, projectFileNodes.length]);

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
  }, [isSessionLoading, isSending, isStopping, projectRoot, sessionId]);

  useEffect(() => {
    if (!isWorking) {
      activityStartedAtRef.current = null;
      setActivityElapsedSeconds(0);
      setLiveProgress(DEFAULT_LIVE_PROGRESS_STATE);
      setLastProgressAt(null);
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
      const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
      setActivityElapsedSeconds(elapsed);
    };

    updateElapsed();
    const timerId = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(timerId);
  }, [isWorking]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const key = 'atopile.agentChatDockHeight';
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return;
    const maxHeight = Math.max(260, Math.floor(window.innerHeight * 0.88));
    setDockHeight(Math.max(280, Math.min(parsed, maxHeight)));
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const raw = window.sessionStorage.getItem('atopile.agentChatMinimized');
    setIsMinimized(raw === '1');
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
    return () => {
      window.removeEventListener('mousedown', onPointerDown);
    };
  }, [isChatsPanelOpen]);

  useEffect(() => {
    if (!resizingDock) return;

    const onMouseMove = (event: MouseEvent) => {
      const start = resizeStartRef.current;
      if (!start) return;
      const delta = start.y - event.clientY;
      const maxHeight = Math.max(300, Math.floor(window.innerHeight * 0.88));
      const next = Math.max(280, Math.min(start.height + delta, maxHeight));
      setDockHeight(next);
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
        if (nextActivity) {
          next.activityLabel = nextActivity;
        }
        if (parsed.phase === 'done' || parsed.phase === 'stopped' || parsed.phase === 'error') {
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
        setLastProgressAt(Date.now());
        setLiveProgress((previous) => ({
          phase: parsed.phase ?? previous.phase,
          statusText: parsed.statusText ?? previous.statusText,
          detailText: parsed.detailText ?? previous.detailText,
          loop: parsed.loop ?? previous.loop,
          toolIndex: parsed.toolIndex ?? previous.toolIndex,
          toolCount: parsed.toolCount ?? previous.toolCount,
          totalTokens: parsed.totalTokens ?? previous.totalTokens,
        }));
        if (nextActivity) {
          setActivityLabel(nextActivity);
        }
        setMessages((previous) => applyProgressToMessages(previous, pendingId, parsed, nextActivity));
        if (parsed.phase === 'done' || parsed.phase === 'stopped' || parsed.phase === 'error') {
          setIsSending(false);
          setIsStopping(false);
          setActiveRunId(null);
        }
      }
    };

    window.addEventListener('atopile:agent_progress', onProgress as EventListener);
    return () => {
      window.removeEventListener('atopile:agent_progress', onProgress as EventListener);
    };
  }, [updateChatSnapshot]);

  useEffect(() => {
    if (!projectRoot) {
      setActiveChatId(null);
      setSessionId(null);
      setMessages([
        {
          id: 'agent-empty',
          role: 'system',
          content: 'Select a project to start an agent session.',
        },
      ]);
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
    if (!isSnapshotsHydrated) {
      return;
    }

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
    const preferredChatId = activeChatByProjectRef.current[projectRoot];
    const preferredChat = preferredChatId
      ? chatsForProject.find((chat) => chat.id === preferredChatId) ?? null
      : null;
    const target = currentChat ?? preferredChat ?? chatsForProject[0];
    if (activeChatId !== target.id) {
      setActiveChatId(target.id);
    }
    loadSnapshotIntoView(target);
  }, [
    activeChatId,
    createAndActivateChat,
    isSnapshotsHydrated,
    loadSnapshotIntoView,
    projectRoot,
    resetChatUiState,
  ]);

  const waitForRunCompletion = useCallback(async (currentSessionId: string, runId: string) => {
    const startedAt = Date.now();
    const hardTimeoutMs = 2 * 60 * 60 * 1000;
    let pollErrorCount = 0;

    while ((Date.now() - startedAt) < hardTimeoutMs) {
      try {
        const runStatus = await agentApi.getRunStatus(currentSessionId, runId);
        pollErrorCount = 0;
        if (runStatus.status === 'completed' && runStatus.response) {
          return runStatus.response;
        }
        if (runStatus.status === 'cancelled') {
          throw new Error(`${RUN_CANCELLED_MARKER}:${runStatus.error ?? 'Cancelled'}`);
        }
        if (runStatus.status === 'failed') {
          throw new Error(runStatus.error ?? 'Agent run failed.');
        }
      } catch (pollError: unknown) {
        pollErrorCount += 1;
        if (pollError instanceof Error && pollError.message.startsWith(RUN_CANCELLED_MARKER)) {
          throw pollError;
        }
        if (isRunNotFoundError(pollError)) {
          throw new Error(
            `${RUN_LOST_MARKER}:Active run was lost (the backend likely restarted). Please resend your message.`,
          );
        }
        if (pollErrorCount >= 20) {
          const message = pollError instanceof Error
            ? pollError.message
            : 'Unable to poll agent run status.';
          throw new Error(
            `Lost contact while waiting for the active run. ${message}`,
          );
        }
      }

      const delayMs = pollErrorCount > 0
        ? Math.min(2500, 350 * (2 ** Math.min(5, pollErrorCount - 1)))
        : 350;
      await new Promise<void>((resolve) => {
        window.setTimeout(() => resolve(), delayMs);
      });
    }

    throw new Error(
      'Agent run is still in progress after a long wait. Stop it or keep waiting.',
    );
  }, []);

  const openFileDiff = useCallback((file: AgentChangedFile) => {
    postMessage({
      type: 'openDiff',
      path: file.payload.path,
      beforeContent: file.payload.before_content,
      afterContent: file.payload.after_content,
      title: `Agent edit diff: ${file.payload.path}`,
    });
  }, []);

  const toggleTraceGroupExpanded = useCallback((messageId: string) => {
    setExpandedTraceGroups((previous) => {
      const next = new Set(previous);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }, []);

  const toggleTraceExpanded = useCallback((traceKey: string) => {
    setExpandedTraceKeys((previous) => {
      const next = new Set(previous);
      if (next.has(traceKey)) {
        next.delete(traceKey);
      } else {
        next.add(traceKey);
      }
      return next;
    });
  }, []);

  const startNewChat = useCallback(() => {
    if (!projectRoot) return;
    createAndActivateChat(projectRoot);
    setIsChatsPanelOpen(false);
  }, [createAndActivateChat, projectRoot]);

  const toggleMinimized = useCallback(() => {
    setIsMinimized((current) => !current);
  }, []);

  const startResize = useCallback((event: ReactMouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    resizeStartRef.current = {
      y: event.clientY,
      height: dockHeight,
    };
    setResizingDock(true);
  }, [dockHeight]);

  const refreshMentionFromInput = useCallback((nextInput: string, caret: number) => {
    const token = findMentionToken(nextInput, caret);
    setMentionToken(token);
    setMentionIndex(0);
  }, []);

  const insertMention = useCallback((item: MentionItem) => {
    if (!mentionToken) return;

    const before = input.slice(0, mentionToken.start);
    const after = input.slice(mentionToken.end);
    const mentionText = `@${item.token}`;
    const needsSpace = after.length > 0 && !/^\s/.test(after);
    const nextInput = `${before}${mentionText}${needsSpace ? ' ' : ''}${after}`;
    const cursor = (before + mentionText + (needsSpace ? ' ' : '')).length;

    setInput(nextInput);
    setMentionToken(null);
    setMentionIndex(0);
    requestAnimationFrame(() => {
      const element = composerInputRef.current;
      if (!element) return;
      element.focus();
      element.setSelectionRange(cursor, cursor);
    });
  }, [input, mentionToken]);

  const stopRun = useCallback(async () => {
    if (!activeChatId || !sessionId || !isSending) return;
    setIsStopping(true);
    setActivityLabel('Stopping');
    setLastProgressAt(Date.now());
    setLiveProgress({
      ...DEFAULT_LIVE_PROGRESS_STATE,
      phase: 'thinking',
      statusText: 'Stopping',
      detailText: 'Cancelling active run',
    });
    const pendingId = activeChatSnapshot?.pendingAssistantId ?? null;
    updateChatSnapshot(activeChatId, (chat) => ({
      ...chat,
      isStopping: true,
      cancelRequested: true,
      activityLabel: 'Stopping',
      messages: pendingId
        ? chat.messages.map((message) =>
          message.id === pendingId
            ? { ...message, content: 'Stopping...', activity: 'Stopping' }
            : message
        )
        : chat.messages,
    }));
    if (pendingId) {
      setMessages((previous) =>
        previous.map((message) =>
          message.id === pendingId
            ? { ...message, content: 'Stopping...', activity: 'Stopping' }
            : message
        )
      );
    }

    const runId = activeRunId ?? activeChatSnapshot?.pendingRunId ?? null;
    if (!runId) {
      return;
    }

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
      updateChatSnapshot(activeChatId, (chat) => ({
        ...chat,
        error: message,
      }));
    }
  }, [activeChatId, activeChatSnapshot, activeRunId, isSending, sessionId, updateChatSnapshot]);

  const sendSteeringMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || !projectRoot || !sessionId || !activeChatId || !isSending) return;
    const chatId = activeChatId;
    const chatPrefix = chatId;
    const pendingAssistantId = activeChatSnapshot?.pendingAssistantId ?? null;
    const userMessage: AgentMessage = {
      id: `${chatPrefix}-user-steer-${Date.now()}`,
      role: 'user',
      content: trimmed,
    };

    const applySteerPendingState = (messages: AgentMessage[]): AgentMessage[] => {
      const withUser = [...messages, userMessage];
      if (!pendingAssistantId) {
        return withUser;
      }
      return withUser.map((message) => (
        message.id === pendingAssistantId
          ? {
            ...message,
            content: 'Incorporating latest guidance...',
            activity: 'Steering',
          }
          : message
      ));
    };

    updateChatSnapshot(chatId, (chat) => ({
      ...chat,
      messages: applySteerPendingState(chat.messages),
      input: '',
      error: null,
      activityLabel: 'Steering',
    }));

    if (activeChatIdRef.current === chatId) {
      setMessages((previous) => applySteerPendingState(previous));
      setActivityLabel('Steering');
      setLastProgressAt(Date.now());
      setLiveProgress({
        ...DEFAULT_LIVE_PROGRESS_STATE,
        phase: 'thinking',
        statusText: 'Steering',
        detailText: 'Applying latest user guidance',
      });
      setError(null);
    }
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);

    const runId = activeRunId ?? activeChatSnapshot?.pendingRunId ?? null;
    if (!runId) {
      const message = 'No active run found to steer. Please send your request again.';
      const steerErrorMessage: AgentMessage = {
        id: `${chatPrefix}-steer-error-${Date.now()}`,
        role: 'system',
        content: message,
      };
      updateChatSnapshot(chatId, (chat) => ({
        ...chat,
        messages: [...chat.messages, steerErrorMessage],
        error: message,
      }));
      if (activeChatIdRef.current === chatId) {
        setMessages((previous) => [...previous, steerErrorMessage]);
        setError(message);
      }
      return;
    }

    try {
      const steerResult = await agentApi.steerRun(sessionId, runId, {
        message: trimmed,
      });
      if (steerResult.status !== 'running') {
        throw new Error('Active run is no longer running. Please resend your request.');
      }
    } catch (steerError: unknown) {
      const message = steerError instanceof Error ? steerError.message : 'Unable to send steering guidance.';
      const steerErrorMessage: AgentMessage = {
        id: `${chatPrefix}-steer-error-${Date.now()}`,
        role: 'system',
        content: `Steering failed: ${message}`,
      };
      updateChatSnapshot(chatId, (chat) => ({
        ...chat,
        messages: [...chat.messages, steerErrorMessage],
        error: message,
      }));
      if (activeChatIdRef.current === chatId) {
        setMessages((previous) => [...previous, steerErrorMessage]);
        setError(message);
      }
    }
  }, [
    activeChatId,
    activeChatSnapshot,
    activeRunId,
    input,
    isSending,
    projectRoot,
    sessionId,
    updateChatSnapshot,
  ]);

  const sendMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || !projectRoot || !sessionId || !activeChatId || isSending) return;
    const chatId = activeChatId;
    const chatPrefix = chatId;

    const userMessage: AgentMessage = {
      id: `${chatPrefix}-user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    };
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
      messages: [...chat.messages, userMessage, pendingAssistantMessage],
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

    setMessages((previous) => [...previous, userMessage, pendingAssistantMessage]);
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);
    setActiveRunId(null);
    setIsStopping(false);
    setIsSending(true);
    setError(null);
    setActivityLabel('Planning');
    setLastProgressAt(Date.now());
    setLiveProgress({
      ...DEFAULT_LIVE_PROGRESS_STATE,
      phase: 'thinking',
      statusText: 'Planning',
      detailText: 'Reviewing request and project context',
    });

    try {
      let currentSessionId = sessionId;
      let run: { runId: string; status: string };
      try {
        run = await agentApi.createRun(currentSessionId, {
          message: trimmed,
          projectRoot,
          selectedTargets,
        });
      } catch (runStartError: unknown) {
        if (!isSessionNotFoundError(runStartError)) {
          throw runStartError;
        }
        const recoveredSession = await agentApi.createSession(projectRoot);
        currentSessionId = recoveredSession.sessionId;
        const recoveredNotice: AgentMessage = {
          id: `${chatPrefix}-session-recovered-${Date.now()}`,
          role: 'system',
          content: 'Previous agent session expired. Reconnected with a new session and retrying.',
        };
        updateChatSnapshot(chatId, (chat) => ({
          ...chat,
          sessionId: currentSessionId,
          messages: [...chat.messages, recoveredNotice],
        }));
        if (activeChatIdRef.current === chatId) {
          setSessionId(currentSessionId);
          setMessages((previous) => [...previous, recoveredNotice]);
        }
        run = await agentApi.createRun(currentSessionId, {
          message: trimmed,
          projectRoot,
          selectedTargets,
        });
      }
      updateChatSnapshot(chatId, (chat) => ({
        ...chat,
        pendingRunId: run.runId,
        activeRunId: run.runId,
      }));
      setActiveRunId(run.runId);
      const cancelledEarly = chatSnapshotsRef.current.find((chat) => chat.id === chatId)?.cancelRequested;
      if (cancelledEarly) {
        if (activeChatIdRef.current === chatId) {
          setIsStopping(true);
        }
        await agentApi.cancelRun(currentSessionId, run.runId);
      }
      const response = await waitForRunCompletion(currentSessionId, run.runId);
      const finalizedTraces = response.toolTraces.map((trace) => ({ ...trace, running: false }));

      const assistantMessage: AgentMessage = {
        id: `${chatPrefix}-assistant-${Date.now()}`,
        role: 'assistant',
        content: withCompletionNudge(
          normalizeAssistantText(response.assistantMessage),
          finalizedTraces,
        ),
        toolTraces: finalizedTraces,
      };

      updateChatSnapshot(chatId, (chat) => ({
        ...chat,
        messages: chat.messages.map((message) =>
          message.id === pendingAssistantId ? assistantMessage : message
        ),
        isSending: false,
        isStopping: false,
        activeRunId: null,
        pendingRunId: null,
        pendingAssistantId: null,
        cancelRequested: false,
        activityLabel: 'Ready',
        error: null,
      }));
      if (activeChatIdRef.current === chatId) {
        setMessages((previous) =>
          previous.map((message) =>
            message.id === pendingAssistantId ? assistantMessage : message
          )
        );
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
              id: cancelled
                ? `${chatPrefix}-assistant-stopped-${Date.now()}`
                : `${chatPrefix}-assistant-error-${Date.now()}`,
              role: 'assistant',
              content: cancelled
                ? `Stopped: ${message}`
                : runLost
                  ? `Request interrupted: ${message}`
                  : `Request failed: ${message}`,
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
        if (!cancelled) {
          setError(message);
        }
        setMessages((previous) =>
          previous.map((entry) =>
            entry.id === pendingAssistantId
              ? {
                id: cancelled
                  ? `${chatPrefix}-assistant-stopped-${Date.now()}`
                  : `${chatPrefix}-assistant-error-${Date.now()}`,
                role: 'assistant',
                content: cancelled
                  ? `Stopped: ${message}`
                  : runLost
                    ? `Request interrupted: ${message}`
                    : `Request failed: ${message}`,
                activity: cancelled ? 'Stopped' : runLost ? 'Interrupted' : 'Errored',
              }
              : entry
          )
        );
        setActivityLabel(cancelled ? 'Stopped' : runLost ? 'Interrupted' : 'Errored');
      }
    } finally {
      if (activeChatIdRef.current === chatId) {
        setActiveRunId(null);
        setIsStopping(false);
        setIsSending(false);
      }
    }
  }, [
    activeChatId,
    input,
    isSending,
    projectRoot,
    selectedTargets,
    sessionId,
    updateChatSnapshot,
    waitForRunCompletion,
  ]);

  const statusClass = isSessionLoading || isWorking ? 'working' : isReady ? 'ready' : 'idle';
  const statusText = isSessionLoading
    ? 'Starting'
    : isWorking
      ? `${activityLabel}${activityElapsedSeconds >= 8 ? ` ${activityElapsedSeconds}s` : ''}`
      : isReady
        ? 'Ready'
        : 'Idle';
  const showStatusText = isSessionLoading || isWorking;

  return (
    <div className={`agent-chat-dock ${isMinimized ? 'minimized' : ''}`} style={{ height: `${isMinimized ? minimizedDockHeight : dockHeight}px`, maxHeight: '88vh' }}>
      {!isMinimized && (
        <button
          type="button"
          className={`agent-chat-resize-handle ${resizingDock ? 'active' : ''}`}
          onMouseDown={startResize}
          aria-label="Resize agent panel"
          title="Drag to resize"
        />
      )}
      <div className="agent-chat-header">
        <div className="agent-chat-header-main">
          <button
            ref={chatsPanelToggleRef}
            type="button"
            className={`agent-chat-nav-toggle ${isChatsPanelOpen ? 'active' : ''}`}
            onClick={() => setIsChatsPanelOpen((current) => !current)}
            disabled={!projectRoot}
            title="Show chat history for this project"
            aria-label="Toggle chat history panel"
          >
            <MessageSquareText size={13} />
          </button>
          <div className="agent-chat-title">
            <div className="agent-chat-title-row">
              <span className="agent-title-project">{headerTitle}</span>
            </div>
            <div className="agent-chat-thread-row">
              <span className="agent-chat-thread-title" title={activeChatTitle}>
                {activeChatTitle}
              </span>
              <span
                className={`agent-chat-thread-status ${statusClass}`}
                aria-label={`Status: ${statusText}`}
                title={`Status: ${statusText}`}
              >
                {(isSessionLoading || isWorking) && <Loader2 size={10} className="agent-tool-spin" />}
                <span className="agent-chat-thread-dot" />
                {showStatusText && <span className="agent-chat-thread-status-text">{statusText}</span>}
              </span>
            </div>
          </div>
        </div>
        <div className="agent-chat-actions">
          <button
            type="button"
            className="agent-chat-action icon-only"
            onClick={startNewChat}
            disabled={!projectRoot}
            title="Start a new chat session"
            aria-label="Start a new chat session"
          >
            <Plus size={12} />
          </button>
          <button
            type="button"
            className="agent-chat-action icon-only"
            onClick={toggleMinimized}
            title={isMinimized ? 'Expand agent panel' : 'Minimize agent panel'}
            aria-label={isMinimized ? 'Expand agent panel' : 'Minimize agent panel'}
          >
            {isMinimized ? <Maximize2 size={12} /> : <Minimize2 size={12} />}
          </button>
        </div>
      </div>

      {!isMinimized && (isSessionLoading || isWorking) && (
        <div className="agent-chat-working-strip" role="status" aria-live="polite">
          <div
            className="agent-chat-thoughts"
            title={thinkingThoughts.join(' • ')}
          >
            <div className="agent-chat-thoughts-track">
              {[...thinkingThoughts, ...thinkingThoughts].map((thought, index) => (
                <span key={`thought-${index}`} className="agent-chat-thought-chip">
                  {thought}
                </span>
              ))}
            </div>
          </div>
          <div className="agent-chat-thinking-proxy">
            <span className="agent-chat-thinking-label">{thinkingMeterSignal.tokenText}</span>
            <div
              className="agent-chat-thinking-meter"
              title={thinkingMeterSignal.isApproximate ? 'Estimated from live activity and elapsed time.' : 'Reported token usage.'}
            >
              <div
                className={`agent-chat-thinking-meter-fill ${isProgressQuiet ? 'quiet' : 'live'}`}
                style={{ width: `${thinkingMeterSignal.percent}%` }}
              />
            </div>
            <span
              className={`agent-chat-thinking-heartbeat ${isProgressQuiet ? 'quiet' : 'live'}`}
              title={thinkingMeterSignal.description}
            >
              {isProgressQuiet ? `waiting ${progressSilenceSeconds}s` : 'live'}
            </span>
          </div>
        </div>
      )}

      {!isMinimized && (
        <div className={`agent-chat-shell ${isChatsPanelOpen ? 'chats-open' : ''}`}>
          <aside className={`agent-chat-history-drawer ${isChatsPanelOpen ? 'open' : ''}`} ref={chatsPanelRef}>
            <div className="agent-chat-history-head">
              <span className="agent-chat-history-title">
                {shortProjectName(projectRoot)} chats
              </span>
              <button
                type="button"
                className="agent-chat-history-close"
                onClick={() => setIsChatsPanelOpen(false)}
                aria-label="Close chat history"
              >
                <X size={12} />
              </button>
            </div>
            <button
              type="button"
              className="agent-chat-history-new"
              onClick={startNewChat}
              disabled={!projectRoot}
            >
              <Plus size={12} />
              <span>New chat</span>
            </button>
            <div className="agent-chat-history-list">
              {projectChats.map((chat) => (
                <button
                  key={`history-${chat.id}`}
                  type="button"
                  className={`agent-chat-history-item ${chat.id === activeChatId ? 'active' : ''}`}
                  onClick={() => activateChat(chat.id)}
                >
                  <span className="agent-chat-history-item-title">{chat.title}</span>
                  <span className="agent-chat-history-item-preview">{summarizeChatPreview(chat.messages)}</span>
                  <span className="agent-chat-history-item-time">{formatChatTimestamp(chat.updatedAt)}</span>
                </button>
              ))}
            </div>
          </aside>
          <button
            type="button"
            className={`agent-chat-history-scrim ${isChatsPanelOpen ? 'open' : ''}`}
            onClick={() => setIsChatsPanelOpen(false)}
            aria-label="Close chat history panel"
            tabIndex={isChatsPanelOpen ? 0 : -1}
          />
          <div className="agent-chat-main">
            <div className="agent-chat-messages" ref={messagesRef}>
              {messages.map((message) => {
                const allTraceEntries = (message.toolTraces ?? []).map((trace, index) => ({ trace, index }));
                const hasToolTraces = allTraceEntries.length > 0;
                const canCollapseToolGroup = allTraceEntries.length > TOOL_TRACE_PREVIEW_COUNT;
                const isToolGroupExpanded = !canCollapseToolGroup || expandedTraceGroups.has(message.id);
                const visibleTraceEntries = isToolGroupExpanded
                  ? allTraceEntries
                  : allTraceEntries.slice(-TOOL_TRACE_PREVIEW_COUNT);
                const hiddenTraceCount = Math.max(0, allTraceEntries.length - visibleTraceEntries.length);

                const toolTraceSection = hasToolTraces ? (
                  <div className={`agent-tool-group ${isToolGroupExpanded ? 'expanded' : 'collapsed'}`}>
                    <button
                      type="button"
                      className={`agent-tool-group-toggle ${canCollapseToolGroup ? 'collapsible' : 'static'}`}
                      onClick={() => {
                        if (canCollapseToolGroup) {
                          toggleTraceGroupExpanded(message.id);
                        }
                      }}
                      disabled={!canCollapseToolGroup}
                      aria-expanded={isToolGroupExpanded}
                    >
                      <ChevronDown
                        size={11}
                        className={`agent-tool-group-chevron ${isToolGroupExpanded ? 'open' : ''} ${!canCollapseToolGroup ? 'hidden' : ''}`}
                      />
                      <span className="agent-tool-group-title">Tool use</span>
                      <span className="agent-tool-group-summary">{summarizeToolTraceGroup(allTraceEntries.map((entry) => entry.trace))}</span>
                      {canCollapseToolGroup && (
                        <span className="agent-tool-group-count">
                          {isToolGroupExpanded
                            ? `show latest ${TOOL_TRACE_PREVIEW_COUNT}`
                            : `show all ${allTraceEntries.length}`}
                        </span>
                      )}
                    </button>
                    <div className="agent-tool-traces">
                      {visibleTraceEntries.map(({ trace, index }) => {
                        const currentTraceKey = traceExpansionKey(message.id, trace, index);
                        const expanded = expandedTraceKeys.has(currentTraceKey);
                        const details = summarizeTraceDetails(trace);
                        const traceDiff = readTraceDiff(trace);

                        return (
                          <div
                            key={`${message.id}-trace-${trace.callId ?? index}`}
                            className={`agent-tool-trace ${trace.running ? 'running' : trace.ok ? 'ok' : 'error'} ${expanded ? 'expanded' : ''}`}
                          >
                            <div className="agent-tool-trace-head">
                              <button
                                type="button"
                                className="agent-tool-trace-toggle"
                                onClick={() => toggleTraceExpanded(currentTraceKey)}
                                aria-expanded={expanded}
                              >
                                {trace.running
                                  ? <Loader2 size={11} className="agent-tool-spin" />
                                  : trace.ok
                                    ? <CheckCircle2 size={11} />
                                    : <AlertCircle size={11} />}
                                <span className="agent-tool-name">{trace.name}</span>
                                <span className="agent-tool-summary">{summarizeToolTrace(trace)}</span>
                                {traceDiff && renderLineDelta(traceDiff.added, traceDiff.removed, 'agent-line-delta-compact')}
                                <ChevronDown size={11} className={`agent-tool-chevron ${expanded ? 'open' : ''}`} />
                              </button>
                            </div>
                            {expanded && (
                              <div className="agent-tool-details">
                                <div className="agent-tool-detail-row">
                                  <span className="agent-tool-detail-label">status</span>
                                  <span className={`agent-tool-detail-value ${!trace.ok && !trace.running ? 'error' : ''}`}>
                                    {details.statusText}
                                  </span>
                                </div>
                                {trace.callId && (
                                  <div className="agent-tool-detail-row">
                                    <span className="agent-tool-detail-label">call</span>
                                    <span className="agent-tool-detail-value agent-tool-detail-mono">
                                      {trace.callId}
                                    </span>
                                  </div>
                                )}
                                {details.input.text && (
                                  <div className="agent-tool-detail-row">
                                    <span className="agent-tool-detail-label">input</span>
                                    <span className="agent-tool-detail-value">
                                      {details.input.text}
                                    </span>
                                  </div>
                                )}
                                {details.input.hiddenCount > 0 && (
                                  <div className="agent-tool-detail-row">
                                    <span className="agent-tool-detail-label">input+</span>
                                    <span className="agent-tool-detail-value agent-tool-detail-muted">
                                      +{details.input.hiddenCount} more fields
                                    </span>
                                  </div>
                                )}
                                {traceDiff && (
                                  <div className="agent-tool-detail-row">
                                    <span className="agent-tool-detail-label">lines</span>
                                    {renderLineDelta(traceDiff.added, traceDiff.removed)}
                                  </div>
                                )}
                                {details.output.text && (
                                  <div className="agent-tool-detail-row">
                                    <span className="agent-tool-detail-label">
                                      {trace.ok || trace.running ? 'output' : 'error'}
                                    </span>
                                    <span className={`agent-tool-detail-value ${!trace.ok && !trace.running ? 'error' : ''}`}>
                                      {details.output.text}
                                    </span>
                                  </div>
                                )}
                                {details.output.hiddenCount > 0 && (
                                  <div className="agent-tool-detail-row">
                                    <span className="agent-tool-detail-label">
                                      {trace.ok || trace.running ? 'output+' : 'error+'}
                                    </span>
                                    <span className="agent-tool-detail-value agent-tool-detail-muted">
                                      +{details.output.hiddenCount} more fields
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    {!isToolGroupExpanded && hiddenTraceCount > 0 && (
                      <button
                        type="button"
                        className="agent-tool-group-more"
                        onClick={() => toggleTraceGroupExpanded(message.id)}
                      >
                        showing latest {visibleTraceEntries.length} of {allTraceEntries.length}
                      </button>
                    )}
                  </div>
                ) : null;

                return (
                  <div key={message.id} className={`agent-message-row ${message.role} ${message.pending ? 'pending' : ''}`}>
                    {message.pending && (
                      <div className="agent-message-meta">
                        <Loader2 size={11} className="agent-tool-spin" />
                        {message.activity && (
                          <span className="agent-message-activity">{message.activity}</span>
                        )}
                      </div>
                    )}
                    {message.role === 'assistant' && toolTraceSection}
                    <div className="agent-message-bubble">
                      <div className="agent-message-content agent-markdown">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                    {message.role !== 'assistant' && toolTraceSection}
                    {latestBuildStatus && latestBuildStatus.messageId === message.id && (
                      <div className="agent-build-status-panel">
                        <div className="agent-build-status-head">
                          <span className="agent-build-status-title">Build status</span>
                          <span className="agent-build-status-meta">
                            {latestBuildStatus.builds.length > 0
                              ? formatCount(latestBuildStatus.builds.length, 'build', 'builds')
                              : 'waiting'}
                          </span>
                        </div>

                        {latestBuildStatus.builds.length > 0 ? (
                          <div className="agent-build-status-list">
                            {latestBuildStatus.builds.map((build) => (
                              <BuildQueueItem key={`agent-build-${build.buildId}`} build={build} />
                            ))}
                          </div>
                        ) : (
                          <div className="agent-build-status-empty">
                            Waiting for build status updates...
                          </div>
                        )}

                        {latestBuildStatus.pendingBuildIds.length > 0 && (
                          <div className="agent-build-status-pending">
                            Tracking {latestBuildStatus.pendingBuildIds.map(compactBuildId).join(', ')}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {changedFilesSummary && (
              <div className={`agent-changes-summary ${changesExpanded ? 'expanded' : ''}`}>
                <button
                  type="button"
                  className="agent-changes-toggle"
                  onClick={() => setChangesExpanded((value) => !value)}
                  title="Toggle changed files"
                >
                  <ChevronDown size={12} className={`agent-changes-chevron ${changesExpanded ? 'open' : ''}`} />
                  <span className="agent-changes-title">
                    {formatCount(changedFilesSummary.files.length, 'file', 'files')} changed
                  </span>
                  <span className="agent-changes-stats">
                    {renderLineDelta(changedFilesSummary.totalAdded, changedFilesSummary.totalRemoved)}
                  </span>
                </button>
                {changesExpanded && (
                  <div className="agent-changes-list">
                    {changedFilesSummary.files.map((file) => (
                      <button
                        key={`${changedFilesSummary.messageId}:${file.path}`}
                        type="button"
                        className="agent-changes-file"
                        onClick={() => openFileDiff(file)}
                        title={`Open diff for ${file.path}`}
                      >
                        <span className="agent-changes-file-path">{file.path}</span>
                        <span className="agent-changes-file-stats">
                          {renderLineDelta(file.added, file.removed)}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="agent-chat-composer-wrap">
              {mentionToken && mentionItems.length > 0 && (
                <div className="agent-mention-menu" role="listbox" aria-label="Mention suggestions">
                  {mentionItems.map((item, index) => (
                    <button
                      key={`${item.kind}:${item.token}`}
                      type="button"
                      className={`agent-mention-item ${index === mentionIndex ? 'active' : ''}`}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => insertMention(item)}
                    >
                      <span className={`agent-mention-kind ${item.kind}`}>{item.kind}</span>
                      <span className="agent-mention-label">{item.label}</span>
                      {item.subtitle && (
                        <span className="agent-mention-subtitle">{item.subtitle}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              <div className="agent-chat-input-shell">
                <textarea
                  ref={composerInputRef}
                  className="agent-chat-input"
                  value={input}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setInput(nextValue);
                    refreshMentionFromInput(
                      nextValue,
                      event.target.selectionStart ?? nextValue.length,
                    );
                  }}
                  onClick={(event) => {
                    refreshMentionFromInput(
                      event.currentTarget.value,
                      event.currentTarget.selectionStart ?? event.currentTarget.value.length,
                    );
                  }}
                  onKeyUp={(event) => {
                    if (
                      mentionToken
                      && mentionItems.length > 0
                      && (
                        event.key === 'ArrowDown'
                        || event.key === 'ArrowUp'
                        || event.key === 'Enter'
                        || event.key === 'Tab'
                        || event.key === 'Escape'
                      )
                    ) {
                      return;
                    }
                    refreshMentionFromInput(
                      event.currentTarget.value,
                      event.currentTarget.selectionStart ?? event.currentTarget.value.length,
                    );
                  }}
                  placeholder={
                    projectRoot
                      ? 'Ask to inspect files, edit code, install packages/parts, or run builds...'
                      : 'Select a project to chat with the agent...'
                  }
                  disabled={!isReady}
                  rows={4}
                  onKeyDown={(event) => {
                    if (mentionToken && mentionItems.length > 0) {
                      if (event.key === 'ArrowDown') {
                        event.preventDefault();
                        setMentionIndex((current) => (current + 1) % mentionItems.length);
                        return;
                      }
                      if (event.key === 'ArrowUp') {
                        event.preventDefault();
                        setMentionIndex((current) => (
                          (current - 1 + mentionItems.length) % mentionItems.length
                        ));
                        return;
                      }
                      if (event.key === 'Enter' || event.key === 'Tab') {
                        event.preventDefault();
                        insertMention(mentionItems[mentionIndex]);
                        return;
                      }
                      if (event.key === 'Escape') {
                        event.preventDefault();
                        setMentionToken(null);
                        setMentionIndex(0);
                        return;
                      }
                    }
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      if (isSending) {
                        void sendSteeringMessage();
                      } else {
                        void sendMessage();
                      }
                    }
                  }}
                />
                <button
                  className="agent-chat-send"
                  onClick={() => {
                    if (isSending) {
                      void sendSteeringMessage();
                    } else {
                      void sendMessage();
                    }
                  }}
                  disabled={!isReady || input.trim().length === 0 || isStopping}
                  aria-label={isSending ? 'Send steering guidance' : 'Send message'}
                  title={isSending ? 'Send steering guidance' : 'Send'}
                >
                  <ArrowUp size={14} />
                </button>
                {isSending && (
                  <button
                    className="agent-chat-stop"
                    onClick={() => {
                      void stopRun();
                    }}
                    disabled={isStopping}
                    aria-label="Stop agent run"
                    title="Stop"
                  >
                    {isStopping ? <Loader2 size={14} className="agent-tool-spin" /> : <Square size={13} />}
                  </button>
                )}
              </div>
            </div>

            {error && <div className="agent-chat-error">{error}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
