import { useState, type RefObject } from 'react';
import { AlertCircle, CheckCircle2, ChevronDown, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { BuildQueueItem } from '../../../components/BuildQueueItem';
import { readTraceDiff } from '../state/progress';
import type { AgentMessage } from '../state/types';
import { DesignQuestionsCard } from './DesignQuestionsCard';
import {
  compactBuildId,
  formatCount,
  renderLineDelta,
  summarizeToolTrace,
  summarizeToolTraceGroup,
  summarizeTraceDetails,
  traceExpansionKey,
  type AgentChangedFilesSummary,
} from './viewHelpers';
import type { QueuedBuild } from '../../../types/build';

const TOOL_TRACE_PREVIEW_COUNT = 5;
const CHECKLIST_TERMINAL_PREVIEW_COUNT = 10;

interface MessageBuildStatusState {
  messageId: string;
  builds: QueuedBuild[];
  pendingBuildIds: string[];
}

interface AgentMessagesViewProps {
  messagesRef: RefObject<HTMLDivElement>;
  messages: AgentMessage[];
  expandedTraceGroups: Set<string>;
  expandedTraceKeys: Set<string>;
  latestBuildStatus: MessageBuildStatusState | null;
  changedFilesSummary: AgentChangedFilesSummary | null;
  changesExpanded: boolean;
  onToggleTraceGroupExpanded: (messageId: string) => void;
  onToggleTraceExpanded: (traceKey: string) => void;
  onToggleChangesExpanded: () => void;
  onSubmitDesignQuestions: (answers: string) => void;
  onOpenFileDiff: (file: NonNullable<AgentChangedFilesSummary>['files'][number]) => void;
}

export function AgentMessagesView({
  messagesRef,
  messages,
  expandedTraceGroups,
  expandedTraceKeys,
  latestBuildStatus,
  changedFilesSummary,
  changesExpanded,
  onToggleTraceGroupExpanded,
  onToggleTraceExpanded,
  onToggleChangesExpanded,
  onSubmitDesignQuestions,
  onOpenFileDiff,
}: AgentMessagesViewProps) {
  const [expandedChecklistMessages, setExpandedChecklistMessages] = useState<Set<string>>(new Set());

  return (
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
                    onToggleTraceGroupExpanded(message.id);
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
                          onClick={() => onToggleTraceExpanded(currentTraceKey)}
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
                  onClick={() => onToggleTraceGroupExpanded(message.id)}
                >
                  showing latest {visibleTraceEntries.length} of {allTraceEntries.length}
                </button>
              )}
            </div>
          ) : null;

          const completedCount = message.checklist?.items.filter((item) => item.status === 'done').length ?? 0;
          const checklistCount = message.checklist?.items.length ?? 0;
          const terminalItems = message.checklist?.items.filter((item) => item.status === 'done' || item.status === 'blocked') ?? [];
          const activeChecklistItems = message.checklist?.items.filter((item) => item.status !== 'done' && item.status !== 'blocked') ?? [];
          const hiddenTerminalCount = Math.max(0, terminalItems.length - CHECKLIST_TERMINAL_PREVIEW_COUNT);
          const isChecklistExpanded = expandedChecklistMessages.has(message.id);
          const visibleTerminalItems = isChecklistExpanded
            ? terminalItems
            : terminalItems.slice(-CHECKLIST_TERMINAL_PREVIEW_COUNT);
          const visibleChecklistItems = [...activeChecklistItems, ...visibleTerminalItems];

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
              {message.content.trim().length > 0 && (
                <div className="agent-message-bubble">
                  <div className="agent-message-content agent-markdown">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
              {message.designQuestions && !message.pending && (
                <DesignQuestionsCard
                  data={message.designQuestions}
                  onSubmit={onSubmitDesignQuestions}
                />
              )}
              {message.role !== 'assistant' && toolTraceSection}
              {message.checklist && checklistCount > 0 && (
                <div className="agent-checklist-panel">
                  <div className="agent-checklist-head">
                    <span className="agent-checklist-title">Checklist</span>
                    <span className="agent-checklist-meta">{completedCount}/{checklistCount} done</span>
                  </div>
                  <div className="agent-checklist-progress">
                    <div
                      className="agent-checklist-progress-bar"
                      style={{ width: `${Math.round((completedCount / checklistCount) * 100)}%` }}
                    />
                  </div>
                  <div className="agent-checklist-items">
                    {visibleChecklistItems.map((item) => (
                      <div
                        key={item.id}
                        className={`agent-checklist-item agent-checklist-item--${item.status}`}
                      >
                        <span className="agent-checklist-item-icon">
                          {item.status === 'done' && <CheckCircle2 size={13} />}
                          {item.status === 'doing' && <Loader2 size={13} className="agent-tool-spin" />}
                          {item.status === 'blocked' && <AlertCircle size={13} />}
                          {item.status === 'not_started' && <span className="agent-checklist-item-circle" />}
                        </span>
                        <span className="agent-checklist-item-id">{item.id}</span>
                        <span className="agent-checklist-item-desc">{item.description}</span>
                        {item.requirement_id && (
                          <span className="agent-checklist-item-req" title={`Spec requirement ${item.requirement_id}`}>
                            {item.requirement_id}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                  {hiddenTerminalCount > 0 && (
                    <button
                      type="button"
                      className="agent-checklist-more"
                      onClick={() => {
                        setExpandedChecklistMessages((current) => {
                          const next = new Set(current);
                          if (next.has(message.id)) {
                            next.delete(message.id);
                          } else {
                            next.add(message.id);
                          }
                          return next;
                        });
                      }}
                    >
                      {isChecklistExpanded
                        ? `show recent ${CHECKLIST_TERMINAL_PREVIEW_COUNT}`
                        : `show all ${checklistCount} items`}
                    </button>
                  )}
                </div>
              )}
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
            onClick={onToggleChangesExpanded}
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
                  onClick={() => onOpenFileDiff(file)}
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
    </>
  );
}
