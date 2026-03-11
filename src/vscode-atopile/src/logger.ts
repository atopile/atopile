import * as vscode from "vscode";

export class ExtensionLogger {
  private readonly _prefix: string;

  constructor(
    private readonly _output: vscode.LogOutputChannel,
    private readonly _scope?: string,
  ) {
    this._prefix = this._scope ? `[${this._scope}]` : "[Extension]";
  }

  scope(scope: string): ExtensionLogger {
    const nextScope = this._scope ? `${this._scope}:${scope}` : scope;
    return new ExtensionLogger(this._output, nextScope);
  }

  info(message: string): void {
    this._output.info(`${this._prefix} ${message}`);
  }

  warn(message: string): void {
    this._output.warn(`${this._prefix} ${message}`);
  }

  error(message: string): void {
    this._output.error(`${this._prefix} ${message}`);
  }

  debug(message: string): void {
    this._output.debug(`${this._prefix} ${message}`);
  }
}
