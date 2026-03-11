import { rpcClient } from "./rpcClient";

export class WebviewLogger {
  private readonly _prefix: string;

  constructor(scope: string) {
    this._prefix = `[${scope}]`;
  }

  info(message: string): void {
    const scopedMessage = `${this._prefix} ${message}`;
    console.log(scopedMessage);
    rpcClient?.sendAction("vscode.log", { level: "log", message: scopedMessage });
  }

  warn(message: string): void {
    const scopedMessage = `${this._prefix} ${message}`;
    console.warn(scopedMessage);
    rpcClient?.sendAction("vscode.log", { level: "warn", message: scopedMessage });
  }

  error(message: string): void {
    const scopedMessage = `${this._prefix} ${message}`;
    console.error(scopedMessage);
    rpcClient?.sendAction("vscode.log", { level: "error", message: scopedMessage });
  }
}

export function createWebviewLogger(scope: string): WebviewLogger {
  return new WebviewLogger(scope);
}
