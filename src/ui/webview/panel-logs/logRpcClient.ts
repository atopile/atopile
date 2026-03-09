import { useEffect, useState } from "react";
import type { WebviewRpcClient } from "../shared/rpcClient";
import { rpcClient } from "../shared/rpcClient";
import type { LogConnectionState } from "../../shared/types";
import type {
  UiBuildLogRequest,
  UiLogEntry,
  UiLogsErrorMessage,
  UiLogsStreamMessage,
} from "../../shared/generated-types";

type LogMessage = UiLogsStreamMessage | UiLogsErrorMessage;

export class LogRpcClient {
  private readonly _rpcClient: WebviewRpcClient;
  private _logs: UiLogEntry[] = [];
  private _streaming = false;
  private _error: string | null = null;
  private _connectionState: LogConnectionState = "disconnected";
  private _activeRequest: UiBuildLogRequest | null = null;
  private _listeners = new Set<() => void>();

  constructor(client: WebviewRpcClient) {
    this._rpcClient = client;
    this._connectionState = client.isConnected() ? "connected" : "disconnected";
    client.addRawListener(this._handleRawMessage);
    client.addConnectionListener(this._handleConnectionChange);
  }

  get connectionState(): LogConnectionState {
    return this._connectionState;
  }

  get error(): string | null {
    return this._error;
  }

  get logs(): UiLogEntry[] {
    return this._logs;
  }

  get streaming(): boolean {
    return this._streaming;
  }

  addListener(listener: () => void): void {
    this._listeners.add(listener);
  }

  removeListener(listener: () => void): void {
    this._listeners.delete(listener);
  }

  dispose(): void {
    this._rpcClient.removeRawListener(this._handleRawMessage);
    this._rpcClient.removeConnectionListener(this._handleConnectionChange);
  }

  clearLogs(): void {
    this._logs = [];
    this._notify();
  }

  startBuildStream(request: UiBuildLogRequest): void {
    if (!request.buildId.trim()) {
      this._error = "Build ID is required";
      this._notify();
      return;
    }

    this._activeRequest = {
      ...request,
      buildId: request.buildId.trim(),
    };
    this._logs = [];
    this._streaming = true;
    this._error = null;
    this._notify();

    if (!this._rpcClient.isConnected()) {
      this._connectionState = "connecting";
      this._notify();
      return;
    }

    this._sendSubscription();
  }

  stopStream(): void {
    this._activeRequest = null;
    this._rpcClient.sendAction("unsubscribeLogs");
    this._streaming = false;
    this._notify();
  }

  static useLogState(): {
    connectionState: LogConnectionState;
    error: string | null;
    logs: UiLogEntry[];
    streaming: boolean;
  } {
    const [, bump] = useState(0);
    useEffect(() => {
      const callback = () => bump((n) => n + 1);
      hookListeners.add(callback);
      logClient?.addListener(callback);
      return () => {
        hookListeners.delete(callback);
        logClient?.removeListener(callback);
      };
    }, []);

    return {
      connectionState: logClient?.connectionState ?? "disconnected",
      error: logClient?.error ?? null,
      logs: logClient?.logs ?? [],
      streaming: logClient?.streaming ?? false,
    };
  }

  private readonly _handleConnectionChange = (connected: boolean) => {
    this._connectionState = connected ? "connected" : "disconnected";
    if (!connected) {
      this._streaming = false;
      this._notify();
      return;
    }

    if (this._activeRequest) {
      this._sendSubscription();
      return;
    }

    this._notify();
  };

  private readonly _handleRawMessage = (data: string) => {
    try {
      const message = JSON.parse(data) as LogMessage;
      if (message.type === "logs_stream") {
        if (message.logs.length > 0) {
          this._logs = [...this._logs, ...message.logs];
        }
        this._error = null;
        this._notify();
        return;
      }

      if (message.type === "logs_error") {
        this._error = message.error;
        this._streaming = false;
        this._notify();
      }
    } catch {
      // Ignore non-log RPC messages.
    }
  };

  private _sendSubscription(): void {
    this._rpcClient.sendAction("unsubscribeLogs");
    const ok = this._rpcClient.sendAction(
      "subscribeLogs",
      this._activeRequest as unknown as Record<string, unknown>,
    );
    if (!ok) {
      this._streaming = false;
      this._error = "Not connected";
    } else {
      this._streaming = true;
      this._error = null;
    }
    this._notify();
  }

  private _notify(): void {
    for (const listener of this._listeners) {
      listener();
    }
  }
}

export let logClient: LogRpcClient | null = null;
const hookListeners = new Set<() => void>();

export function connectLogClient(): void {
  if (!rpcClient) {
    return;
  }

  logClient?.dispose();
  logClient = new LogRpcClient(rpcClient);
  for (const listener of hookListeners) {
    logClient.addListener(listener);
  }
}
