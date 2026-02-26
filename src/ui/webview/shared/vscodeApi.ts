/**
 * Shared VS Code API instance.
 *
 * acquireVsCodeApi() can only be called once per webview.
 * Import `vscode` from this module instead of calling it directly.
 */
export const vscode = acquireVsCodeApi();
