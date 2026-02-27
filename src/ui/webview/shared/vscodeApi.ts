/**
 * Shared VS Code API instance.
 *
 * acquireVsCodeApi() can only be called once per webview.
 * Import `vscode` from this module instead of calling it directly.
 */
export const vscode = acquireVsCodeApi();

/**
 * Forward console.log/warn/error to the extension host OutputChannel.
 */
const _origLog = console.log;
const _origWarn = console.warn;
const _origError = console.error;

function forward(level: "log" | "warn" | "error", args: unknown[]) {
  const message = args
    .map((a) => (typeof a === "string" ? a : JSON.stringify(a)))
    .join(" ");
  vscode.postMessage({ type: "log", level, message });
}

console.log = (...args: unknown[]) => {
  _origLog.apply(console, args);
  forward("log", args);
};
console.warn = (...args: unknown[]) => {
  _origWarn.apply(console, args);
  forward("warn", args);
};
console.error = (...args: unknown[]) => {
  _origError.apply(console, args);
  forward("error", args);
};
