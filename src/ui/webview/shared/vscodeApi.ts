/**
 * Shared VS Code API instance.
 *
 * acquireVsCodeApi() can only be called once per webview.
 * Import `vscode` from this module instead of calling it directly.
 */
declare function acquireVsCodeApi(): {
  postMessage(message: unknown): void;
};

export const vscode = acquireVsCodeApi();
