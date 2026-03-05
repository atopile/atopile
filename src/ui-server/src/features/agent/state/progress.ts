import type { AgentToolTrace } from '../../../api/agent';
import { trimSingleLine } from '../../../components/AgentChatPanel.helpers';
import type {
  AgentChecklist,
  AgentChecklistItem,
  AgentEditDiffUiPayload,
  AgentMessage,
  AgentProgressPayload,
  AgentProgressPhase,
  AgentTraceView,
  DesignQuestion,
  DesignQuestionsData,
} from './types';

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
    || value === 'design_questions'
  ) {
    return value;
  }
  return null;
}

function parseChecklist(raw: unknown): AgentChecklist | null {
  if (!raw || typeof raw !== 'object') return null;
  const obj = raw as Record<string, unknown>;
  const items = Array.isArray(obj.items) ? obj.items : [];
  const parsed: AgentChecklistItem[] = [];
  for (const item of items) {
    if (!item || typeof item !== 'object') continue;
    const it = item as Record<string, unknown>;
    if (typeof it.id !== 'string' || typeof it.description !== 'string') continue;
    parsed.push({
      id: it.id,
      description: it.description as string,
      criteria: (typeof it.criteria === 'string' ? it.criteria : '') as string,
      status: (['not_started', 'doing', 'done', 'blocked'].includes(it.status as string)
        ? it.status
        : 'not_started') as AgentChecklistItem['status'],
      requirement_id: typeof it.requirement_id === 'string' ? it.requirement_id : null,
    });
  }
  if (parsed.length === 0) return null;
  return {
    items: parsed,
    created_at: typeof obj.created_at === 'number' ? obj.created_at : 0,
  };
}

function parseDesignQuestions(payload: AgentProgressPayload): DesignQuestionsData | null {
  if (!Array.isArray(payload.questions)) return null;
  const questions: DesignQuestion[] = [];
  for (const raw of payload.questions) {
    if (!raw || typeof raw !== 'object') continue;
    const q = raw as Record<string, unknown>;
    const id = typeof q.id === 'string' ? q.id : null;
    const question = typeof q.question === 'string' ? q.question : null;
    if (!id || !question) continue;
    const options = Array.isArray(q.options)
      ? (q.options as unknown[]).filter((o): o is string => typeof o === 'string')
      : undefined;
    const defaultOpt = typeof q.default === 'string' ? q.default : undefined;
    questions.push({ id, question, options: options?.length ? options : undefined, default: defaultOpt });
  }
  if (questions.length === 0) return null;
  const context = typeof payload.context === 'string' ? payload.context : '';
  return { context, questions };
}

export function readProgressPayload(detail: unknown): {
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
  inputTokens: number | null;
  totalTokens: number | null;
  contextLimitTokens: number | null;
  checklist: AgentChecklist | null;
  designQuestions: DesignQuestionsData | null;
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
      inputTokens: null,
      totalTokens: null,
      contextLimitTokens: null,
      checklist: null,
      designQuestions: null,
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
  const inputTokens = toFiniteNumber(payload.input_tokens)
    ?? (usage ? toFiniteNumber(usage.input_tokens) : null)
    ?? (usage ? toFiniteNumber(usage.inputTokens) : null);
  const totalTokens = toFiniteNumber(payload.total_tokens)
    ?? (usage ? toFiniteNumber(usage.total_tokens) : null)
    ?? (usage ? toFiniteNumber(usage.totalTokens) : null)
    ?? ((() => {
      const input = inputTokens;
      const output = toFiniteNumber(payload.output_tokens)
        ?? (usage ? toFiniteNumber(usage.output_tokens) : null)
        ?? (usage ? toFiniteNumber(usage.outputTokens) : null);
      if (input === null && output === null) return null;
      return (input ?? 0) + (output ?? 0);
    })());
  const contextLimitTokens = toFiniteNumber(payload.context_limit_tokens)
    ?? toFiniteNumber(payload.contextLimitTokens);

  const trace = payload.trace && typeof payload.trace === 'object'
    ? payload.trace as AgentToolTrace
    : null;

  const checklist = parseChecklist(payload.checklist);
  const designQuestions = phase === 'design_questions' ? parseDesignQuestions(payload) : null;

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
    inputTokens,
    totalTokens,
    contextLimitTokens,
    checklist,
    designQuestions,
  };
}

export function readTraceDiff(trace: AgentTraceView): { added: number; removed: number } | null {
  const raw = trace.result.diff;
  if (!raw || typeof raw !== 'object') return null;
  const diff = raw as Record<string, unknown>;
  const added = typeof diff.added_lines === 'number' ? diff.added_lines : null;
  const removed = typeof diff.removed_lines === 'number' ? diff.removed_lines : null;
  if (added == null || removed == null) return null;
  return { added, removed };
}

export function readTraceEditDiffPayload(trace: AgentTraceView): AgentEditDiffUiPayload | null {
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

function inferActivityFromTool(toolName: string | null): string {
  if (!toolName) return 'Working';
  if (toolName.startsWith('project_') || toolName.startsWith('stdlib_')) {
    if (
      toolName === 'project_edit_file' ||
      toolName === 'project_create_path' ||
      toolName === 'project_create_file' ||
      toolName === 'project_create_folder' ||
      toolName === 'project_move_path' ||
      toolName === 'project_rename_path' ||
      toolName === 'project_delete_path'
    ) {
      return 'Editing';
    }
    return 'Exploring';
  }
  if (toolName.startsWith('build_')) {
    return toolName === 'build_logs_search' ? 'Reviewing' : 'Building';
  }
  if (toolName === 'parts_search' || toolName === 'packages_search' || toolName === 'web_search') {
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

function inferToolActivityDetail(toolName: string | null, args: Record<string, unknown>): string {
  if (!toolName) return 'Working';
  const path = asNonEmptyString(args.path);

  if (toolName === 'project_read_file') return path ? `Reading ${compactPath(path)}` : 'Reading file';
  if (toolName === 'project_edit_file') return path ? `Editing ${compactPath(path)}` : 'Editing file';
  if (toolName === 'project_create_path' || toolName === 'project_create_file') return path ? `Creating ${compactPath(path)}` : 'Creating file';
  if (toolName === 'project_create_folder') return path ? `Creating folder ${compactPath(path)}` : 'Creating folder';
  if (toolName === 'project_search') {
    const query = asNonEmptyString(args.query);
    return query ? `Searching "${trimSingleLine(query, 30)}"` : 'Searching project';
  }
  if (toolName === 'web_search') {
    const query = asNonEmptyString(args.query);
    return query ? `Searching web for "${trimSingleLine(query, 26)}"` : 'Searching web';
  }
  if (toolName === 'project_list_modules') return 'Scanning modules';
  if (toolName === 'project_module_children') {
    const entry = asNonEmptyString(args.entry);
    return entry ? `Inspecting ${trimSingleLine(entry, 36)}` : 'Inspecting module';
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
  if (toolName === 'design_diagnostics') return 'Running diagnostics';
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
  return inferActivityFromTool(toolName);
}

export function inferActivityFromProgress(
  payload: {
    phase: AgentProgressPhase | null;
    name: string | null;
    args: Record<string, unknown>;
    trace: AgentToolTrace | null;
    statusText: string | null;
    detailText: string | null;
  },
): string | null {
  if (payload.phase === 'thinking' || payload.phase === 'compacting') {
    const status = payload.statusText || (payload.phase === 'compacting' ? 'Compacting context' : 'Thinking');
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
      if (error) return `Failed: ${trimSingleLine(error, 42)}`;
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
    if (resultMessage) return trimSingleLine(resultMessage, 46);
    return inferToolActivityDetail(payload.trace.name, payload.trace.args);
  }
  if (payload.phase === 'design_questions') return 'Questions for you';
  if (payload.phase === 'error') return 'Errored';
  if (payload.phase === 'done') return 'Complete';
  if (payload.phase === 'stopped') return 'Stopped';
  return null;
}

export function applyProgressToMessages(
  previous: AgentMessage[],
  pendingId: string,
  parsed: ReturnType<typeof readProgressPayload>,
  nextActivity: string | null,
): AgentMessage[] {
  return previous.map((message) => {
    if (message.id !== pendingId) return message;

    const traces = [...(message.toolTraces ?? [])];
    const latestChecklist = parsed.checklist ?? message.checklist;

    if (parsed.phase === 'tool_start') {
      if (!parsed.callId || !parsed.name) return message;
      const index = traces.findIndex((trace) => trace.callId === parsed.callId);
      const runningTrace: AgentTraceView = {
        callId: parsed.callId,
        name: parsed.name,
        args: parsed.args,
        ok: true,
        result: { message: 'running' },
        running: true,
      };
      if (index >= 0) traces[index] = runningTrace;
      else traces.push(runningTrace);
      return {
        ...message,
        content: nextActivity ? `${nextActivity}...` : message.content,
        activity: nextActivity ?? message.activity,
        toolTraces: traces,
        checklist: latestChecklist,
      };
    }

    if (parsed.phase === 'tool_end') {
      if (!parsed.trace) return message;
      const finishedTrace: AgentTraceView = {
        ...parsed.trace,
        callId: parsed.callId ?? undefined,
        running: false,
      };
      const index = parsed.callId
        ? traces.findIndex((trace) => trace.callId === parsed.callId)
        : -1;
      if (index >= 0) traces[index] = finishedTrace;
      else traces.push(finishedTrace);
      return {
        ...message,
        content: nextActivity ? `${nextActivity}...` : message.content,
        activity: nextActivity ?? message.activity,
        toolTraces: traces,
        checklist: latestChecklist,
      };
    }

    if (parsed.phase === 'error') {
      return {
        ...message,
        pending: false,
        checklist: latestChecklist,
      };
    }

    if (parsed.phase === 'thinking') {
      return {
        ...message,
        activity: nextActivity ?? message.activity,
        checklist: latestChecklist,
      };
    }

    if (parsed.phase === 'design_questions' && parsed.designQuestions) {
      return {
        ...message,
        content: parsed.designQuestions.context || 'Design questions',
        pending: false,
        designQuestions: parsed.designQuestions,
        checklist: latestChecklist,
      };
    }

    if (parsed.phase === 'done' || parsed.phase === 'stopped') {
      return {
        ...message,
        pending: false,
        checklist: latestChecklist,
      };
    }

    return message;
  });
}
