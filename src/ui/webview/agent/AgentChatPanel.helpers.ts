export const DEFAULT_CHAT_TITLE = 'New chat';

export interface ChatPreviewMessage {
  role: string;
  content: string;
}

export function shortProjectName(projectRoot: string | null): string {
  if (!projectRoot) return 'No project selected';
  const parts = projectRoot.split('/').filter(Boolean);
  return parts[parts.length - 1] || projectRoot;
}

export function createChatId(): string {
  return `chat-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

export function trimSingleLine(value: string, maxLength: number): string {
  const compact = value.replace(/\s+/g, ' ').trim();
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, Math.max(0, maxLength - 1))}...`;
}

export function deriveChatTitle(messages: ChatPreviewMessage[]): string {
  const firstUser = messages.find((message) => message.role === 'user' && message.content.trim().length > 0);
  if (!firstUser) return DEFAULT_CHAT_TITLE;
  const compact = firstUser.content
    .replace(/[#>*_`~[\]()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!compact) return DEFAULT_CHAT_TITLE;
  return trimSingleLine(compact, 44);
}

export function summarizeChatPreview(messages: ChatPreviewMessage[]): string {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    const compact = message.content.replace(/\s+/g, ' ').trim();
    if (!compact) continue;
    if (message.role === 'user') return `You: ${trimSingleLine(compact, 58)}`;
    if (message.role === 'assistant') return trimSingleLine(compact, 62);
  }
  return 'No messages yet';
}

export function formatChatTimestamp(timestamp: number): string {
  if (!Number.isFinite(timestamp) || timestamp <= 0) return '';
  try {
    return new Date(timestamp).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export function normalizeAssistantText(text: string): string {
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
