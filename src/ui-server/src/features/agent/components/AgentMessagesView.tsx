import type { RefObject } from 'react';
import { AlertCircle, Check, ChevronDown, Loader2, X } from 'lucide-react';
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
} from './viewHelpers';
import type { QueuedBuild } from '../../../types/build';

interface MessageBuildStatusState {
  messageId: string;
  builds: QueuedBuild[];
  pendingBuildIds: string[];
}

interface AgentMessagesViewProps {
  messagesRef: RefObject<HTMLDivElement>;
  messages: AgentMessage[];
  expandedTraceKeys: Set<string>;
  latestBuildStatus: MessageBuildStatusState | null;
  onToggleTraceExpanded: (traceKey: string) => void;
  onSubmitDesignQuestions: (answers: string) => void;
}

export function AgentMessagesView({
  messagesRef,
  messages,
  expandedTraceKeys,
  latestBuildStatus,
  onToggleTraceExpanded,
  onSubmitDesignQuestions,
}: AgentMessagesViewProps) {
  const latestChecklistMessageId = [...messages]
    .reverse()
    .find((message) => (message.checklist?.items.length ?? 0) > 0)?.id ?? null;

  return (
    <>
      <div className="agent-chat-messages" ref={messagesRef}>
        {messages.map((message) => {
          const allTraceEntries = (message.toolTraces ?? []).map((trace, index) => ({ trace, index }));
          const hasToolTraces = allTraceEntries.length > 0;

          const toolTraceSection = hasToolTraces ? (
            <div className="agent-tool-group scrollable">
              <div className="agent-tool-group-header">
                <span className="agent-tool-group-title">Tool use</span>
                <span className="agent-tool-group-summary">{summarizeToolTraceGroup(allTraceEntries.map((entry) => entry.trace))}</span>
              </div>
              <div className="agent-tool-traces">
                {allTraceEntries.map(({ trace, index }) => {
                  const currentTraceKey = traceExpansionKey(message.id, trace, index);
                  const expanded = expandedTraceKeys.has(currentTraceKey);
                  const details = summarizeTraceDetails(trace);
                  const traceDiff = readTraceDiff(trace);

                  return (
                    <div
                      key={currentTraceKey}
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
                            ? <Loader2 size={11} className="agent-tool-spin agent-tool-status-icon running" />
                            : trace.ok
                              ? <Check size={11} className="agent-tool-status-icon ok" />
                              : <X size={11} className="agent-tool-status-icon error" />}
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
            </div>
          ) : null;

          const completedCount = message.checklist?.items.filter((item) => item.status === 'done').length ?? 0;
          const checklistCount = message.checklist?.items.length ?? 0;
          const terminalItems = message.checklist?.items.filter((item) => item.status === 'done' || item.status === 'blocked') ?? [];
          const activeChecklistItems = message.checklist?.items.filter((item) => item.status !== 'done' && item.status !== 'blocked') ?? [];
          const visibleChecklistItems = [...activeChecklistItems, ...terminalItems];

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
              {message.checklist && checklistCount > 0 && latestChecklistMessageId === message.id && (
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
                          {item.status === 'done' && <Check size={13} className="agent-tool-status-icon ok" />}
                          {item.status === 'doing' && <Loader2 size={13} className="agent-tool-spin agent-tool-status-icon running" />}
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
    </>
  );
}
