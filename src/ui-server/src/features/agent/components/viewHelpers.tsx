import { trimSingleLine } from '../../../components/AgentChatPanel.helpers';
import { readTraceDiff, readTraceEditDiffPayload } from '../state/progress';
import type {
  AgentEditDiffUiPayload,
  AgentMessage,
  AgentTraceView,
} from '../state/types';

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

export interface AgentChangedFile {
  path: string;
  added: number;
  removed: number;
  payload: AgentEditDiffUiPayload;
}

export interface AgentChangedFilesSummary {
  messageId: string;
  files: AgentChangedFile[];
  totalAdded: number;
  totalRemoved: number;
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

function stableStringify(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(',')}]`;
  }
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${key}:${stableStringify(record[key])}`).join(',')}}`;
  }
  return '';
}

function formatTracePreviewValue(value: unknown, maxLength = 88): string {
  if (value === null) return 'null';
  if (typeof value === 'undefined') return 'undefined';
  if (typeof value === 'string') {
    const compact = trimSingleLine(value, maxLength);
    return compact.length > 0 ? compact : '""';
  }
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
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

export function summarizeTraceDetails(trace: AgentTraceView): TraceDetailsSummary {
  const inputSelection = collectTraceEntries(trace.args, TRACE_INPUT_PREFERRED_KEYS, TRACE_DETAIL_LIMIT);
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

export function traceExpansionKey(messageId: string, trace: AgentTraceView, index: number): string {
  if (trace.callId) return `${messageId}:${trace.callId}`;
  return `${messageId}:${trace.name}:${stableStringify(trace.args)}:${index}`;
}

export function summarizeToolTrace(trace: AgentTraceView): string {
  if (trace.running) return 'running...';
  if (trace.ok) {
    if (trace.name === 'project_edit_file') {
      const diff = readTraceDiff(trace);
      const operationsApplied =
        typeof trace.result.operations_applied === 'number' ? trace.result.operations_applied : null;
      const firstChangedLine =
        typeof trace.result.first_changed_line === 'number' ? trace.result.first_changed_line : null;
      if (operationsApplied !== null && firstChangedLine !== null) {
        return `${operationsApplied} edits at line ${firstChangedLine}`;
      }
      if (operationsApplied !== null) return `${operationsApplied} edits applied`;
      if (diff) return 'line changes';
    }
    if (typeof trace.result.message === 'string') return trace.result.message;
    if (typeof trace.result.total === 'number') return `${trace.result.total} items`;
    return 'ok';
  }
  if (typeof trace.result.error === 'string') return trace.result.error;
  return 'failed';
}

export function formatCount(value: number, singular: string, plural: string): string {
  return `${value} ${value === 1 ? singular : plural}`;
}

export function renderLineDelta(added: number, removed: number, className?: string): JSX.Element {
  const classes = ['agent-line-delta'];
  if (className) classes.push(className);
  return (
    <span className={classes.join(' ')}>
      <span className="agent-line-added">+{added}</span>
      <span className="agent-line-removed">-{removed}</span>
    </span>
  );
}

export function summarizeToolTraceGroup(traces: AgentTraceView[]): string {
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

export function collectChangedFilesSummary(messages: AgentMessage[]): AgentChangedFilesSummary | null {
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

export function compactBuildId(buildId: string): string {
  const numbered = buildId.match(/^build-(\d+)-/);
  if (numbered) return `#${numbered[1]}`;
  if (buildId.length <= 12) return buildId;
  return `${buildId.slice(0, 8)}...`;
}
