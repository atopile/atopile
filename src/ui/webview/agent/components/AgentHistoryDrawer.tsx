import type { RefObject } from 'react';
import { Plus, X } from 'lucide-react';
import {
  formatChatTimestamp,
  shortProjectName,
  summarizeChatPreview,
} from '../AgentChatPanel.helpers';
import type { AgentChatSnapshot } from '../state/types';

interface AgentHistoryDrawerProps {
  projectRoot: string | null;
  projectChats: AgentChatSnapshot[];
  activeChatId: string | null;
  isChatsPanelOpen: boolean;
  chatsPanelRef: RefObject<HTMLDivElement | null>;
  onClose: () => void;
  onStartNewChat: () => void;
  onActivateChat: (chatId: string) => void;
}

export function AgentHistoryDrawer({
  projectRoot,
  projectChats,
  activeChatId,
  isChatsPanelOpen,
  chatsPanelRef,
  onClose,
  onStartNewChat,
  onActivateChat,
}: AgentHistoryDrawerProps) {
  return (
    <>
      <aside className={`agent-chat-history-drawer ${isChatsPanelOpen ? 'open' : ''}`} ref={chatsPanelRef}>
        <div className="agent-chat-history-head">
          <span className="agent-chat-history-title">
            {shortProjectName(projectRoot)} chats
          </span>
          <button
            type="button"
            className="agent-chat-history-close"
            onClick={onClose}
            aria-label="Close chat history"
          >
            <X size={12} />
          </button>
        </div>
        <button
          type="button"
          className="agent-chat-history-new"
          onClick={onStartNewChat}
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
              onClick={() => onActivateChat(chat.id)}
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
        onClick={onClose}
        aria-label="Close chat history panel"
        tabIndex={isChatsPanelOpen ? 0 : -1}
      />
    </>
  );
}
