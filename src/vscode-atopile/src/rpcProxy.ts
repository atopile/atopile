import * as vscode from "vscode";
import WebSocket from "ws";
import type { RpcTransport } from "../../ui/shared/rpcTransport";
import type {
  ExtensionRequestMessage,
  ExtensionRequestResult,
} from "./extensionRequestHandler";
import { ExtensionLogger } from "./logger";

type BootstrapState = {
  key: string;
  data: unknown;
};

type SessionCallbacks = {
  onOpen?: () => void;
  onClose?: () => void;
  onMessage?: (data: string) => void;
  onExtensionRequest?: (message: ExtensionRequestMessage) => Promise<ExtensionRequestResult>;
};

export const EXTENSION_SESSION_ID = "extension";

export class RpcProxy implements vscode.Disposable {
  private readonly _corePort: number;
  private readonly _logger: ExtensionLogger;
  private readonly _handleExtensionRequest: (
    webview: vscode.Webview,
    message: ExtensionRequestMessage,
  ) => Promise<ExtensionRequestResult>;
  private readonly _registrations = new Set<vscode.Disposable>();
  private readonly _sessions = new Map<string, SessionCallbacks>();
  private readonly _bootstrapState = new Map<string, unknown>();
  private readonly _pendingMessages: string[] = [];
  private _disposed = false;
  private _socket: WebSocket | null = null;
  private _reconnectTimer: NodeJS.Timeout | null = null;

  constructor(
    corePort: number,
    logger: ExtensionLogger,
    handleExtensionRequest: (
      webview: vscode.Webview,
      message: ExtensionRequestMessage,
    ) => Promise<ExtensionRequestResult>,
  ) {
    this._corePort = corePort;
    this._logger = logger.scope("RpcProxy");
    this._handleExtensionRequest = handleExtensionRequest;
  }

  setBootstrapState(key: string, data: unknown): void {
    this._bootstrapState.set(key, data);
    this._broadcastBootstrapState();
  }

  clearBootstrapState(key: string): void {
    this._bootstrapState.delete(key);
  }

  connectWebviewSession(sessionId: string, webview: vscode.Webview): vscode.Disposable {
    const sessionDisposable = this._attachSession(sessionId, {
      onOpen: () => {
        this._postWebviewMessage(webview, { type: "rpc:open" }, `${sessionId}:open`);
        this._sendBootstrapState(webview);
      },
      onClose: () => {
        this._postWebviewMessage(webview, { type: "rpc:close" }, `${sessionId}:close`);
      },
      onMessage: (data) => {
        this._postWebviewMessage(webview, { type: "rpc:recv", data }, `${sessionId}:recv`);
      },
      onExtensionRequest: (message) => this._handleExtensionRequest(webview, message),
    });

    const messageDisposable = webview.onDidReceiveMessage((message) => {
      if (message?.type !== "rpc:send" || typeof message.data !== "string") {
        return;
      }
      this._sendSessionRaw(sessionId, message.data);
    });

    this._connect();
    this._sendBootstrapState(webview);

    const disposable = new vscode.Disposable(() => {
      messageDisposable.dispose();
      sessionDisposable.dispose();
      this._registrations.delete(disposable);
    });

    this._registrations.add(disposable);
    return disposable;
  }

  createTransport(sessionId: string): RpcTransport {
    return new ProxySessionTransport(this, sessionId);
  }

  dispose(): void {
    this._disposed = true;
    for (const disposable of [...this._registrations]) {
      disposable.dispose();
    }
    this._registrations.clear();
    this._sessions.clear();
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this._socket) {
      this._socket.removeAllListeners();
      this._socket.close();
      this._socket = null;
    }
  }

  attachSession(sessionId: string, callbacks: SessionCallbacks): vscode.Disposable {
    return this._attachSession(sessionId, callbacks);
  }

  sendSessionPayload(sessionId: string, payload: Record<string, unknown>): boolean {
    return this._sendSerialized({
      ...payload,
      sessionId,
    });
  }

  private _attachSession(sessionId: string, callbacks: SessionCallbacks): vscode.Disposable {
    const existing = this._sessions.get(sessionId);
    if (existing && existing !== callbacks) {
      try {
        existing.onClose?.();
      } catch (error) {
        this._logger.warn(
          `Ignoring stale session close failure for ${sessionId}: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }
    this._sessions.set(sessionId, callbacks);
    this._connect();
    if (this._isSocketOpen()) {
      callbacks.onOpen?.();
    }

    return new vscode.Disposable(() => {
      const current = this._sessions.get(sessionId);
      if (current !== callbacks) {
        return;
      }
      callbacks.onClose?.();
      this._sessions.delete(sessionId);
    });
  }

  private _sendBootstrapState(webview: vscode.Webview): void {
    for (const [key, data] of this._bootstrapState.entries()) {
      const entry: BootstrapState = { key, data };
      this._postWebviewMessage(
        webview,
        {
          type: "rpc:recv",
          data: JSON.stringify({
            type: "state",
            key: entry.key,
            data: entry.data,
          }),
        },
        `bootstrap:${entry.key}`,
      );
    }
  }

  private _broadcastBootstrapState(): void {
    for (const [sessionId] of this._sessions.entries()) {
      if (sessionId === EXTENSION_SESSION_ID) {
        continue;
      }
      const callbacks = this._sessions.get(sessionId);
      if (!callbacks?.onMessage) {
        continue;
      }
      for (const [key, data] of this._bootstrapState.entries()) {
        callbacks.onMessage(
          JSON.stringify({
            type: "state",
            key,
            data,
          }),
        );
      }
    }
  }

  private _sendSessionRaw(sessionId: string, raw: string): void {
    try {
      const payload = JSON.parse(raw) as Record<string, unknown>;
      this._sendSerialized({
        ...payload,
        sessionId,
      });
    } catch {
      this._logger.warn(`Dropping invalid JSON from session ${sessionId}`);
    }
  }

  private _sendSerialized(payload: Record<string, unknown>): boolean {
    const raw = JSON.stringify(payload);
    if (!this._isSocketOpen()) {
      this._pendingMessages.push(raw);
      this._connect();
      return false;
    }

    this._socket!.send(raw);
    return true;
  }

  private _connect(): void {
    if (this._disposed) {
      return;
    }
    if (this._socket && this._socket.readyState !== WebSocket.CLOSED) {
      return;
    }
    if (this._reconnectTimer) {
      return;
    }

    const socket = new WebSocket(`ws://localhost:${this._corePort}/atopile-ui`);
    this._socket = socket;

    socket.on("open", () => {
      for (const callbacks of this._sessions.values()) {
        callbacks.onOpen?.();
      }
      this._flushPending();
    });

    socket.on("message", (data) => {
      void this._handleSocketMessage(data.toString());
    });

    socket.on("close", () => {
      if (this._socket === socket) {
        this._socket = null;
      }
      for (const callbacks of this._sessions.values()) {
        callbacks.onClose?.();
      }
      this._scheduleReconnect();
    });

    socket.on("error", (error) => {
      this._logger.error(error.message);
    });
  }

  private _flushPending(): void {
    if (!this._isSocketOpen()) {
      return;
    }
    while (this._pendingMessages.length > 0) {
      this._socket!.send(this._pendingMessages.shift()!);
    }
  }

  private _scheduleReconnect(): void {
    if (this._disposed || this._reconnectTimer) {
      return;
    }
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this._connect();
    }, 1000);
  }

  private async _handleSocketMessage(raw: string): Promise<void> {
    let message: Record<string, unknown>;
    try {
      message = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      this._logger.warn("Dropping invalid backend JSON");
      return;
    }

    const sessionId =
      typeof message.sessionId === "string" && message.sessionId
        ? message.sessionId
        : EXTENSION_SESSION_ID;
    const callbacks = this._sessions.get(sessionId);
    if (!callbacks) {
      this._logger.warn(`No registered session for ${sessionId}`);
      return;
    }

    if (message.type === "extension_request") {
      await this._handleBackendExtensionRequest(sessionId, callbacks, message);
      return;
    }

    delete message.sessionId;
    callbacks.onMessage?.(JSON.stringify(message));
  }

  private async _handleBackendExtensionRequest(
    sessionId: string,
    callbacks: SessionCallbacks,
    message: Record<string, unknown>,
  ): Promise<void> {
    if (!callbacks.onExtensionRequest) {
      this._logger.warn(`Session ${sessionId} cannot handle extension_request`);
      return;
    }

    const request = message as ExtensionRequestMessage;
    if (typeof request.requestId !== "string" || !request.requestId) {
      this._logger.warn("Dropping extension_request without requestId");
      return;
    }

    this._logger.info(
      `extension_request session=${sessionId} action=${request.action} requestId=${request.requestId}`,
    );

    let response: ExtensionRequestResult;
    try {
      response = await callbacks.onExtensionRequest(request);
    } catch (error) {
      response = {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }

    this._logger.info(
      `extension_response session=${sessionId} action=${request.action} requestId=${request.requestId} ok=${response.ok}`,
    );

    this.sendSessionPayload(sessionId, {
      type: "extension_response",
      requestId: request.requestId,
      action: request.action,
      ...response,
    });
  }

  private _isSocketOpen(): boolean {
    return this._socket?.readyState === WebSocket.OPEN;
  }

  private _postWebviewMessage(
    webview: vscode.Webview,
    message: unknown,
    context: string,
  ): void {
    try {
      const result = webview.postMessage(message);
      void result.then(
        undefined,
        (error) => {
          this._logger.warn(
            `Ignoring webview postMessage failure for ${context}: ${error instanceof Error ? error.message : String(error)}`,
          );
        },
      );
    } catch (error) {
      this._logger.warn(
        `Ignoring webview postMessage failure for ${context}: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }
}

class ProxySessionTransport implements RpcTransport {
  onMessage: ((data: string) => void) | null = null;
  onOpen: (() => void) | null = null;
  onClose: (() => void) | null = null;

  private readonly _proxy: RpcProxy;
  private readonly _sessionId: string;
  private _disposable: vscode.Disposable | null = null;

  constructor(proxy: RpcProxy, sessionId: string) {
    this._proxy = proxy;
    this._sessionId = sessionId;
  }

  connect(): void {
    if (this._disposable) {
      return;
    }
    this._disposable = this._proxy.attachSession(this._sessionId, {
      onOpen: () => this.onOpen?.(),
      onClose: () => this.onClose?.(),
      onMessage: (data) => this.onMessage?.(data),
    });
  }

  send(data: string): void {
    const ok = this._proxy.sendSessionPayload(this._sessionId, JSON.parse(data) as Record<string, unknown>);
    if (!ok) {
      throw new Error("Transport is not connected");
    }
  }

  close(): void {
    this._disposable?.dispose();
    this._disposable = null;
  }
}
