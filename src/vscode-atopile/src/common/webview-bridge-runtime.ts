import * as path from 'path';

export type WebviewBridgeFetchMode = 'global' | 'override';

export interface WebviewBridgeRuntimeConfig {
  apiUrl: string;
  fetchMode?: WebviewBridgeFetchMode;
}

export const WEBVIEW_BRIDGE_CONFIG_ELEMENT_ID = 'atopile-webview-bridge-config';

export function getWebviewBridgeRuntimePath(extensionPath: string): string {
  return path.join(extensionPath, 'resources', 'webview-bridge-runtime.js');
}

export function serializeWebviewBridgeConfig(config: WebviewBridgeRuntimeConfig): string {
  return JSON.stringify({
    apiUrl: config.apiUrl,
    fetchMode: config.fetchMode ?? 'global',
  }).replace(/</g, '\\u003c');
}
