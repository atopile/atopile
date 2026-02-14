import * as vscode from 'vscode';
import * as path from 'path';

export function getNonce(): string {
  let text = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

export function getWsOrigin(wsUrl: string): string {
  try {
    return new URL(wsUrl).origin;
  } catch {
    return wsUrl;
  }
}

export function createWebviewOptions(params: {
  extensionPath: string;
  port: number;
  prodLocalResourceRoots: string[];
}): vscode.WebviewOptions & { retainContextWhenHidden?: boolean } {
  const { extensionPath, port, prodLocalResourceRoots } = params;
  return {
    enableScripts: true,
    retainContextWhenHidden: true,
    portMapping: port > 0
      ? [{ webviewPort: port, extensionHostPort: port }]
      : [],
    localResourceRoots: prodLocalResourceRoots.map((relativePath) =>
      vscode.Uri.file(path.join(extensionPath, relativePath))
    ),
  };
}
