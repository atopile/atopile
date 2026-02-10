import * as vscode from 'vscode';
import * as path from 'path';

export function createWebviewOptions(params: {
  isDev: boolean;
  extensionPath: string;
  port: number;
  prodLocalResourceRoots: string[];
}): vscode.WebviewOptions & { retainContextWhenHidden?: boolean } {
  const { isDev, extensionPath, port, prodLocalResourceRoots } = params;
  return {
    enableScripts: true,
    retainContextWhenHidden: true,
    portMapping: port
      ? [{ webviewPort: port, extensionHostPort: port }]
      : [],
    localResourceRoots: isDev
      ? []
      : prodLocalResourceRoots.map((relativePath) =>
          vscode.Uri.file(path.join(extensionPath, relativePath))
        ),
  };
}
