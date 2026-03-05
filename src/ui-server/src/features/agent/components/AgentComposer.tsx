import { AlertCircle, ArrowUp, Loader2, Square } from 'lucide-react';
import type { KeyboardEvent, RefObject } from 'react';

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

interface AgentComposerProps {
  composerInputRef: RefObject<HTMLTextAreaElement>;
  input: string;
  mentionToken: MentionToken | null;
  mentionItems: MentionItem[];
  isLoadingMentions: boolean;
  mentionIndex: number;
  projectRoot: string | null;
  isReady: boolean;
  isSending: boolean;
  isStopping: boolean;
  compactionNotice: { nonce: number; status: string; detail: string | null } | null;
  contextUsage: {
    usedTokens: number;
    limitTokens: number;
    usedPercent: number;
    leftPercent: number;
  } | null;
  onInputChange: (nextValue: string, textarea: HTMLTextAreaElement) => void;
  onInputClick: (value: string, caret: number) => void;
  onInputKeyUp: (key: string, value: string, caret: number) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onInsertMention: (item: MentionItem) => void;
  onSend: () => void;
  onStop: () => void;
}

export function AgentComposer({
  composerInputRef,
  input,
  mentionToken,
  mentionItems,
  isLoadingMentions,
  mentionIndex,
  projectRoot,
  isReady,
  isSending,
  isStopping,
  compactionNotice,
  contextUsage,
  onInputChange,
  onInputClick,
  onInputKeyUp,
  onInsertMention,
  onKeyDown,
  onSend,
  onStop,
}: AgentComposerProps) {
  return (
    <div className="agent-chat-composer-wrap">
      {mentionToken && (
        <div className="agent-mention-menu" role="listbox" aria-label="Mention suggestions">
          {mentionItems.length > 0 ? (
            mentionItems.map((item, index) => (
              <button
                key={`${item.kind}:${item.token}`}
                type="button"
                className={`agent-mention-item ${index === mentionIndex ? 'active' : ''}`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => onInsertMention(item)}
              >
                <span className={`agent-mention-kind ${item.kind}`}>{item.kind}</span>
                <span className="agent-mention-label">{item.label}</span>
                {item.subtitle && (
                  <span className="agent-mention-subtitle">{item.subtitle}</span>
                )}
              </button>
            ))
          ) : (
            <div className="agent-mention-empty" role="status">
              {isLoadingMentions ? 'Loading mentions…' : 'No matches'}
            </div>
          )}
        </div>
      )}

      <div className="agent-chat-input-shell">
        <textarea
          ref={composerInputRef}
          className="agent-chat-input"
          value={input}
          onChange={(event) => onInputChange(event.target.value, event.target)}
          onClick={(event) => {
            onInputClick(
              event.currentTarget.value,
              event.currentTarget.selectionStart ?? event.currentTarget.value.length,
            );
          }}
          onKeyUp={(event) => {
            onInputKeyUp(
              event.key,
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
          rows={2}
          onKeyDown={onKeyDown}
        />
        <button
          className="agent-chat-send"
          onClick={onSend}
          disabled={!isReady || input.trim().length === 0 || isStopping}
          aria-label={isSending ? 'Send steering guidance' : 'Send message'}
          title={isSending ? 'Send steering guidance' : 'Send'}
        >
          <ArrowUp size={14} />
        </button>
        {isSending && (
          <button
            className="agent-chat-stop"
            onClick={onStop}
            disabled={isStopping}
            aria-label="Stop agent run"
            title="Stop"
          >
            {isStopping ? <Loader2 size={14} className="agent-tool-spin" /> : <Square size={13} />}
          </button>
        )}
      </div>
      <div className="agent-chat-composer-meta" aria-live="polite">
        {compactionNotice && (
          <div className="agent-context-notice" role="status">
            <AlertCircle size={11} />
            <span>{compactionNotice.status}</span>
            {compactionNotice.detail && (
              <span className="agent-context-notice-detail">{compactionNotice.detail}</span>
            )}
          </div>
        )}
        {contextUsage && (
          <div
            className="agent-context-meter"
            title={`Context: ${contextUsage.usedTokens.toLocaleString()} / ${contextUsage.limitTokens.toLocaleString()} tokens`}
          >
            <div className="agent-context-meter-row">
              <span className="agent-context-meter-label">Context</span>
              <span className="agent-context-meter-value">{contextUsage.leftPercent}% left</span>
            </div>
            <div className="agent-context-meter-bar" aria-hidden="true">
              <span className="agent-context-meter-fill" style={{ width: `${contextUsage.usedPercent}%` }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
