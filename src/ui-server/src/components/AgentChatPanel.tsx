import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import { ArrowUp, CheckCircle2, AlertCircle, ChevronDown, Loader2, Square, Plus, Minimize2, Maximize2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  agentApi,
  type AgentToolTrace,
} from '../api/agent';
import { api } from '../api/client';
import { postMessage } from '../api/vscodeApi';
import { useStore } from '../store';
import { BuildQueueItem } from './BuildQueueItem';
import type { Build, FileTreeNode, ModuleDefinition, QueuedBuild } from '../types/build';
import './AgentChatPanel.css';

type MessageRole = 'user' | 'assistant' | 'system';

type AgentProgressPhase = 'tool_start' | 'tool_end' | 'done' | 'stopped' | 'error';

interface AgentProgressPayload {
  session_id?: unknown;
  run_id?: unknown;
  phase?: unknown;
  call_id?: unknown;
  name?: unknown;
  args?: unknown;
  trace?: unknown;
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

interface AgentChatPanelProps {
  projectRoot: string | null;
  selectedTargets: string[];
}

const RUN_CANCELLED_MARKER = '__ATOPILE_AGENT_RUN_CANCELLED__';
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

function shortProjectName(projectRoot: string | null): string {
  if (!projectRoot) return 'No project selected';
  const parts = projectRoot.split('/').filter(Boolean);
  return parts[parts.length - 1] || projectRoot;
}

function normalizeAssistantText(text: string): string {
  if (!text || text.includes('```')) return text;
  const lines = text.split('\n');
  const nonEmpty = lines.filter((line) => line.trim().length > 0);
  if (nonEmpty.length < 2) return text;

  const indents = nonEmpty
    .map((line) => line.match(/^\s*/)?.[0].length ?? 0)
    .filter((value) => value > 0);
  if (indents.length === 0) return text;

  const minIndent = Math.min(...indents);
  if (minIndent < 2) return text;

  return lines
    .map((line) => (line.startsWith(' '.repeat(minIndent)) ? line.slice(minIndent) : line))
    .join('\n');
}

function trimSingleLine(value: string, maxLength: number): string {
  const compact = value.replace(/\s+/g, ' ').trim();
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, Math.max(0, maxLength - 1))}...`;
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
    };
  }

  const payload = detail as AgentProgressPayload;
  const phase = typeof payload.phase === 'string' ? payload.phase as AgentProgressPhase : null;
  const sessionId = typeof payload.session_id === 'string' ? payload.session_id : null;
  const runId = typeof payload.run_id === 'string' ? payload.run_id : null;
  const callId = typeof payload.call_id === 'string' ? payload.call_id : null;
  const name = typeof payload.name === 'string' ? payload.name : null;
  const args = payload.args && typeof payload.args === 'object'
    ? payload.args as Record<string, unknown>
    : {};

  const trace = payload.trace && typeof payload.trace === 'object'
    ? payload.trace as AgentToolTrace
    : null;

  return { sessionId, runId, phase, callId, trace, name, args };
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
  if (toolName === 'parts_install' || toolName === 'packages_install') {
    return 'Installing';
  }
  if (toolName === 'report_bom' || toolName === 'report_variables' || toolName === 'manufacturing_summary' || toolName === 'design_diagnostics') {
    return 'Reviewing';
  }
  return 'Working';
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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activityLabel, setActivityLabel] = useState<string>('Idle');
  const [dockHeight, setDockHeight] = useState<number>(defaultDockHeight);
  const [sessionResetToken, setSessionResetToken] = useState(0);
  const [isMinimized, setIsMinimized] = useState(false);
  const [changesExpanded, setChangesExpanded] = useState(false);
  const [expandedTraceGroups, setExpandedTraceGroups] = useState<Set<string>>(new Set());
  const [expandedTraceKeys, setExpandedTraceKeys] = useState<Set<string>>(new Set());
  const [resizingDock, setResizingDock] = useState(false);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const composerInputRef = useRef<HTMLTextAreaElement | null>(null);
  const pendingAssistantIdRef = useRef<string | null>(null);
  const pendingRunIdRef = useRef<string | null>(null);
  const cancelRequestedRef = useRef(false);
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

  const isReady = Boolean(projectRoot && sessionId);
  const isWorking = isSending || isStopping;
  const headerTitle = useMemo(() => shortProjectName(projectRoot), [projectRoot]);
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
  }, [projectRoot, sessionResetToken]);

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
      if (!parsed.sessionId || parsed.sessionId !== sessionId) return;
      if (
        pendingRunIdRef.current
        && parsed.runId
        && parsed.runId !== pendingRunIdRef.current
      ) {
        return;
      }
      const pendingId = pendingAssistantIdRef.current;
      if (!pendingId) return;
      let nextActivity: string | null = null;
      if (parsed.phase === 'tool_start') {
        nextActivity = inferActivityFromTool(parsed.name);
      } else if (parsed.phase === 'tool_end' && parsed.trace) {
        nextActivity = inferActivityFromTool(parsed.trace.name);
      } else if (parsed.phase === 'error') {
        nextActivity = 'Errored';
      } else if (parsed.phase === 'done') {
        nextActivity = 'Complete';
      } else if (parsed.phase === 'stopped') {
        nextActivity = 'Stopped';
      }
      if (nextActivity) {
        setActivityLabel(nextActivity);
      }

      setMessages((previous) =>
        previous.map((message) => {
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
            return {
              ...message,
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
            return {
              ...message,
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

          if (parsed.phase === 'done' || parsed.phase === 'stopped') {
            return {
              ...message,
              pending: false,
            };
          }

          return message;
        })
      );
    };

    window.addEventListener('atopile:agent_progress', onProgress as EventListener);
    return () => {
      window.removeEventListener('atopile:agent_progress', onProgress as EventListener);
    };
  }, [sessionId]);

  useEffect(() => {
    let cancelled = false;

    pendingAssistantIdRef.current = null;
    pendingRunIdRef.current = null;
    cancelRequestedRef.current = false;
    setIsStopping(false);
    setActiveRunId(null);

    if (!projectRoot) {
      setSessionId(null);
      setMessages([
        {
          id: 'agent-empty',
          role: 'system',
          content: 'Select a project to start an agent session.',
        },
      ]);
      return;
    }

    setIsSessionLoading(true);
    setError(null);

    agentApi
      .createSession(projectRoot)
      .then((response) => {
        if (cancelled) return;
        setSessionId(response.sessionId);
        setMessages([
          {
            id: `agent-welcome-${response.sessionId}`,
            role: 'system',
            content: `Session ready for ${shortProjectName(projectRoot)}. Ask me to inspect, edit, build, or install.`,
          },
        ]);
      })
      .catch((sessionError: unknown) => {
        if (cancelled) return;
        const message = sessionError instanceof Error ? sessionError.message : 'Failed to start session.';
        setSessionId(null);
        setError(message);
        setMessages([
          {
            id: 'agent-session-error',
            role: 'system',
            content: `Unable to start agent: ${message}`,
          },
        ]);
      })
      .finally(() => {
        if (!cancelled) {
          setIsSessionLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projectRoot]);

  const waitForRunCompletion = useCallback(async (currentSessionId: string, runId: string) => {
    const timeoutAt = Date.now() + 10 * 60 * 1000;
    while (Date.now() < timeoutAt) {
      const runStatus = await agentApi.getRunStatus(currentSessionId, runId);
      if (runStatus.status === 'completed' && runStatus.response) {
        return runStatus.response;
      }
      if (runStatus.status === 'cancelled') {
        throw new Error(`${RUN_CANCELLED_MARKER}:${runStatus.error ?? 'Cancelled'}`);
      }
      if (runStatus.status === 'failed') {
        throw new Error(runStatus.error ?? 'Agent run failed.');
      }
      await new Promise<void>((resolve) => {
        window.setTimeout(() => resolve(), 350);
      });
    }
    throw new Error('Timed out waiting for agent run completion.');
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
    if (!projectRoot || isSending || isSessionLoading) return;
    setMentionToken(null);
    setMentionIndex(0);
    setExpandedTraceGroups(new Set());
    setExpandedTraceKeys(new Set());
    setChangesExpanded(false);
    setError(null);
    setSessionResetToken((current) => current + 1);
  }, [isSending, isSessionLoading, projectRoot]);

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
    if (!sessionId || !isSending) return;
    cancelRequestedRef.current = true;
    setIsStopping(true);
    setActivityLabel('Stopping');
    const pendingId = pendingAssistantIdRef.current;
    if (pendingId) {
      setMessages((previous) =>
        previous.map((message) =>
          message.id === pendingId
            ? { ...message, content: 'Stopping...', activity: 'Stopping' }
            : message
        )
      );
    }

    const runId = activeRunId ?? pendingRunIdRef.current;
    if (!runId) {
      return;
    }

    try {
      await agentApi.cancelRun(sessionId, runId);
    } catch (stopError: unknown) {
      const message = stopError instanceof Error ? stopError.message : 'Unable to stop the active run.';
      setError(message);
    }
  }, [activeRunId, isSending, sessionId]);

  const sendMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || !projectRoot || !sessionId || isSending) return;

    const userMessage: AgentMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    };
    const pendingAssistantId = `assistant-pending-${Date.now()}`;
    const pendingAssistantMessage: AgentMessage = {
      id: pendingAssistantId,
      role: 'assistant',
      content: 'Thinking...',
      activity: 'Thinking',
      pending: true,
      toolTraces: [],
    };

    pendingAssistantIdRef.current = pendingAssistantId;

    setMessages((previous) => [...previous, userMessage, pendingAssistantMessage]);
    setInput('');
    setMentionToken(null);
    setMentionIndex(0);
    cancelRequestedRef.current = false;
    setActiveRunId(null);
    setIsStopping(false);
    setIsSending(true);
    setError(null);
    setActivityLabel('Thinking');

    try {
      const run = await agentApi.createRun(sessionId, {
        message: trimmed,
        projectRoot,
        selectedTargets,
      });
      pendingRunIdRef.current = run.runId;
      setActiveRunId(run.runId);
      if (cancelRequestedRef.current) {
        setIsStopping(true);
        await agentApi.cancelRun(sessionId, run.runId);
      }
      const response = await waitForRunCompletion(sessionId, run.runId);
      const finalizedTraces = response.toolTraces.map((trace) => ({ ...trace, running: false }));

      const assistantMessage: AgentMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: withCompletionNudge(
          normalizeAssistantText(response.assistantMessage),
          finalizedTraces,
        ),
        toolTraces: finalizedTraces,
      };

      setMessages((previous) =>
        previous.map((message) =>
          message.id === pendingAssistantId ? assistantMessage : message
        )
      );
    } catch (sendError: unknown) {
      const rawMessage = sendError instanceof Error ? sendError.message : 'Agent request failed.';
      const cancelled = rawMessage.startsWith(RUN_CANCELLED_MARKER);
      const message = cancelled
        ? rawMessage.split(':').slice(1).join(':').trim() || 'Cancelled by user'
        : rawMessage;
      if (!cancelled) {
        setError(message);
      }
      setMessages((previous) =>
        previous.map((entry) =>
          entry.id === pendingAssistantId
            ? {
                id: cancelled ? `assistant-stopped-${Date.now()}` : `assistant-error-${Date.now()}`,
                role: 'assistant',
                content: cancelled ? `Stopped: ${message}` : `Request failed: ${message}`,
                activity: cancelled ? 'Stopped' : 'Errored',
              }
            : entry
        )
      );
      setActivityLabel(cancelled ? 'Stopped' : 'Errored');
    } finally {
      pendingAssistantIdRef.current = null;
      pendingRunIdRef.current = null;
      cancelRequestedRef.current = false;
      setActiveRunId(null);
      setIsStopping(false);
      setIsSending(false);
    }
  }, [input, isSending, projectRoot, selectedTargets, sessionId, waitForRunCompletion]);

  const statusClass = isSessionLoading || isWorking ? 'working' : isReady ? 'ready' : 'idle';
  const statusText = isSessionLoading ? 'Starting' : isWorking ? activityLabel : isReady ? 'Ready' : 'Idle';

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
        <div className="agent-chat-title">
          <span className="agent-title-label">Agent</span>
          <span className="agent-title-project">{headerTitle}</span>
        </div>
        <div className="agent-chat-header-right">
          <span className={`agent-status-pill ${statusClass}`}>
            {(isSessionLoading || isWorking) && <Loader2 size={10} className="agent-tool-spin" />}
            {statusText}
          </span>
          <div className="agent-chat-actions">
            <button
              type="button"
              className="agent-chat-action"
              onClick={startNewChat}
              disabled={!projectRoot || isSessionLoading || isSending}
              title="Start a new chat session"
            >
              <Plus size={12} />
              <span>New chat</span>
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
      </div>

      {!isMinimized && (
        <>
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
                  void stopRun();
                } else {
                  void sendMessage();
                }
              }
            }}
          />
          <button
            className={`agent-chat-send ${isSending ? 'stop' : ''}`}
            onClick={() => {
              if (isSending) {
                void stopRun();
              } else {
                void sendMessage();
              }
            }}
            disabled={!isReady || (!isSending && input.trim().length === 0) || (isSending && isStopping)}
            aria-label={isSending ? 'Stop agent run' : 'Send message'}
            title={isSending ? 'Stop' : 'Send'}
          >
            {isSending
              ? (isStopping ? <Loader2 size={14} className="agent-tool-spin" /> : <Square size={13} />)
              : <ArrowUp size={14} />}
          </button>
        </div>
      </div>

      {error && <div className="agent-chat-error">{error}</div>}
        </>
      )}
    </div>
  );
}
