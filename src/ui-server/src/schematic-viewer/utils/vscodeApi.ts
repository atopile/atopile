import {
  onExtensionMessage as onRootExtensionMessage,
  postToExtension as postToRootExtension,
  type ExtensionToWebviewMessage,
} from '../../api/vscodeApi';

export function postToExtension(message: unknown): void {
  postToRootExtension(message);
}

export function onExtensionMessage(
  handler: (message: ExtensionToWebviewMessage | Record<string, unknown>) => void,
): () => void {
  return onRootExtensionMessage((message) => handler(message));
}

export function requestOpenSource(payload: {
  address?: string;
  filePath?: string;
  line?: number;
  column?: number;
  symbol?: string;
}): void {
  postToRootExtension({ type: 'openSource', ...payload });
}

export function requestRevealInExplorer(payload: {
  path?: string;
  filePath?: string;
  address?: string;
}): void {
  const path = payload.path || payload.filePath || payload.address;
  if (!path) return;
  postToRootExtension({ type: 'revealInFinder', path });
}
