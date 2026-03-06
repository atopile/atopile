import { Plus, Minimize2, Maximize2, MessageSquareText } from 'lucide-react';
import { AgentComposer } from '../features/agent/components/AgentComposer';
import { AgentHistoryDrawer } from '../features/agent/components/AgentHistoryDrawer';
import { AgentMessagesView } from '../features/agent/components/AgentMessagesView';
import { useAgentChatRuntime } from '../features/agent/useAgentChatRuntime';
import './AgentChatPanel.css';

interface AgentChatPanelProps {
  projectRoot: string | null;
  selectedTargets: string[];
}

export function AgentChatPanel({ projectRoot, selectedTargets }: AgentChatPanelProps) {
  const runtime = useAgentChatRuntime(projectRoot, selectedTargets);

  return (
    <div
      className={`agent-chat-dock ${runtime.isMinimized ? 'minimized' : ''}`}
      style={{
        height: `${runtime.isMinimized ? runtime.minimizedDockHeight : runtime.dockHeight}px`,
        maxHeight: '88vh',
      }}
    >
      {!runtime.isMinimized && (
        <button
          type="button"
          className={`agent-chat-resize-handle ${runtime.resizingDock ? 'active' : ''}`}
          onMouseDown={runtime.startResize}
          aria-label="Resize agent panel"
          title="Drag to resize"
        />
      )}
      <div className="agent-chat-header">
        <div className="agent-chat-header-main">
          <button
            ref={runtime.chatsPanelToggleRef}
            type="button"
            className={`agent-chat-nav-toggle ${runtime.isChatsPanelOpen ? 'active' : ''}`}
            onClick={() => runtime.setIsChatsPanelOpen((current) => !current)}
            disabled={!projectRoot}
            title="Show chat history for this project"
            aria-label="Toggle chat history panel"
          >
            <MessageSquareText size={13} />
          </button>
          <div className="agent-chat-title">
            <div className="agent-chat-title-row">
              <span className="agent-title-project">{runtime.headerTitle}</span>
            </div>
            <div className="agent-chat-thread-row">
              <span className="agent-chat-thread-title" title={runtime.activeChatTitle}>
                {runtime.activeChatTitle}
              </span>
              <span
                className={`agent-chat-thread-status ${runtime.statusClass}`}
                aria-label={`Status: ${runtime.statusText}`}
                title={`Status: ${runtime.statusText}`}
              >
                <span className="agent-chat-thread-dot" />
              </span>
            </div>
          </div>
        </div>
        <div className="agent-chat-actions">
          <button
            type="button"
            className="agent-chat-action icon-only"
            onClick={runtime.startNewChat}
            disabled={!projectRoot}
            title="Start a new chat session"
            aria-label="Start a new chat session"
          >
            <Plus size={12} />
          </button>
          <button
            type="button"
            className="agent-chat-action icon-only"
            onClick={runtime.toggleMinimized}
            title={runtime.isMinimized ? 'Expand agent panel' : 'Minimize agent panel'}
            aria-label={runtime.isMinimized ? 'Expand agent panel' : 'Minimize agent panel'}
          >
            {runtime.isMinimized ? <Maximize2 size={12} /> : <Minimize2 size={12} />}
          </button>
        </div>
      </div>

      {!runtime.isMinimized && (
        <div className={`agent-chat-shell ${runtime.isChatsPanelOpen ? 'chats-open' : ''}`}>
          <AgentHistoryDrawer
            projectRoot={projectRoot}
            projectChats={runtime.projectChats}
            activeChatId={runtime.activeChatId}
            isChatsPanelOpen={runtime.isChatsPanelOpen}
            chatsPanelRef={runtime.chatsPanelRef}
            onClose={() => runtime.setIsChatsPanelOpen(false)}
            onStartNewChat={runtime.startNewChat}
            onActivateChat={runtime.activateChat}
          />
          <div className="agent-chat-main">
            <AgentMessagesView
              messagesRef={runtime.messagesRef}
              messages={runtime.messages}
              expandedTraceGroups={runtime.expandedTraceGroups}
              expandedTraceKeys={runtime.expandedTraceKeys}
              latestBuildStatus={runtime.latestBuildStatus}
              changedFilesSummary={runtime.changedFilesSummary}
              changesExpanded={runtime.changesExpanded}
              onToggleTraceGroupExpanded={runtime.toggleTraceGroupExpanded}
              onToggleTraceExpanded={runtime.toggleTraceExpanded}
              onToggleChangesExpanded={() => runtime.setChangesExpanded((value) => !value)}
              onSubmitDesignQuestions={(answers) => void runtime.sendMessage({ directMessage: answers, hideUserMessage: true })}
              onOpenFileDiff={runtime.openFileDiff}
            />

            <AgentComposer
              composerInputRef={runtime.composerInputRef}
              input={runtime.input}
              mentionToken={runtime.mentionToken}
              mentionItems={runtime.mentionItems}
              isLoadingMentions={runtime.isLoadingMentions}
              mentionIndex={runtime.mentionIndex}
              projectRoot={projectRoot}
              isReady={runtime.isReady}
              isSending={runtime.isSending}
              isStopping={runtime.isStopping}
              compactionNotice={runtime.compactionNotice}
              contextUsage={runtime.contextUsage}
              onInputChange={(nextValue, textarea) => {
                runtime.setInput(nextValue);
                runtime.refreshMentionFromInput(
                  nextValue,
                  textarea.selectionStart ?? nextValue.length,
                );
                textarea.style.height = 'auto';
                textarea.style.height = `${textarea.scrollHeight}px`;
              }}
              onInputClick={runtime.refreshMentionFromInput}
              onInputKeyUp={(key, value, caret) => {
                if (
                  runtime.mentionToken
                  && runtime.mentionItems.length > 0
                  && (
                    key === 'ArrowDown'
                    || key === 'ArrowUp'
                    || key === 'Enter'
                    || key === 'Tab'
                    || key === 'Escape'
                  )
                ) {
                  return;
                }
                runtime.refreshMentionFromInput(value, caret);
              }}
              onKeyDown={(event) => {
                if (runtime.mentionToken && runtime.mentionItems.length > 0) {
                  if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    runtime.setMentionIndex((current) => (current + 1) % runtime.mentionItems.length);
                    return;
                  }
                  if (event.key === 'ArrowUp') {
                    event.preventDefault();
                    runtime.setMentionIndex((current) => (
                      (current - 1 + runtime.mentionItems.length) % runtime.mentionItems.length
                    ));
                    return;
                  }
                  if (event.key === 'Enter' || event.key === 'Tab') {
                    event.preventDefault();
                    runtime.insertMention(runtime.mentionItems[runtime.mentionIndex]);
                    return;
                  }
                  if (event.key === 'Escape') {
                    event.preventDefault();
                    runtime.setMentionToken(null);
                    runtime.setMentionIndex(0);
                    return;
                  }
                }
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  if (runtime.isSending) {
                    void runtime.sendSteeringMessage();
                  } else {
                    void runtime.sendMessage();
                  }
                }
              }}
              onInsertMention={runtime.insertMention}
              onSend={() => {
                if (runtime.isSending) {
                  void runtime.sendSteeringMessage();
                } else {
                  void runtime.sendMessage();
                }
              }}
              onInterrupt={() => {
                void runtime.sendInterruptMessage();
              }}
              onStop={() => {
                void runtime.stopRun();
              }}
            />

            {runtime.error && <div className="agent-chat-error">{runtime.error}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
