/**
 * Log WebSocket client for streaming build logs.
 * Extends WebviewWebSocketClient to connect to the core server's
 * /atopile-core endpoint and handle log-specific messages.
 */

import { useState, useEffect } from 'react';
import { WebviewWebSocketClient } from '../shared/webviewWebSocketClient';
import {
  LogConnectionState,
  LogEntry,
  LogMessage,
  BuildLogRequest,
} from '../../shared/types';

declare global {
  interface Window {
    __ATOPILE_CORE_SERVER_PORT__: number;
  }
}

export class LogWebSocketClient extends WebviewWebSocketClient {
  private _logs: LogEntry[] = [];
  private _streaming = false;
  private _error: string | null = null;
  private _logConnectionState: LogConnectionState = 'disconnected';
  private _activeRequest: BuildLogRequest | null = null;

  constructor(url: string) {
    super(url);

    this._client.onConnected = () => {
      this._logConnectionState = 'connected';
      this._error = null;
      if (this._activeRequest) {
        const sent = this.sendAction(
          'subscribeLogs',
          { ...this._activeRequest } as Record<string, unknown>,
        );
        if (!sent) {
          this._streaming = false;
          this._error = 'Not connected';
        }
      }
      this._notify();
    };

    this._client.onDisconnected = () => {
      this._logConnectionState = 'disconnected';
      this._streaming = false;
      this._notify();
    };

    this._client.onRawMessage = (data) => {
      try {
        const str = typeof data === 'string' ? data : String(data);
        const msg = JSON.parse(str) as LogMessage;
        if (msg.type === 'logs_stream') {
          if (msg.logs.length > 0) {
            this._logs = [...this._logs, ...msg.logs];
          }
          this._error = null;
          this._notify();
        } else if (msg.type === 'logs_error') {
          this._error = msg.error;
          this._streaming = false;
          this._notify();
        }
      } catch {
        // Not a log message
      }
    };
  }

  get connectionState(): LogConnectionState { return this._logConnectionState; }
  get error(): string | null { return this._error; }
  get logs(): LogEntry[] { return this._logs; }
  get streaming(): boolean { return this._streaming; }
  addListener(cb: () => void): void { this._listeners.add(cb); }
  removeListener(cb: () => void): void { this._listeners.delete(cb); }

  connect(): void {
    this._logConnectionState = 'connecting';
    this._notify();
    super.connect();
  }

  clearLogs(): void {
    this._logs = [];
    this._notify();
  }

  startBuildStream(request: BuildLogRequest): void {
    if (!request.build_id.trim()) {
      this._error = 'Build ID is required';
      this._notify();
      return;
    }
    this._activeRequest = {
      ...request,
      build_id: request.build_id.trim(),
    };
    this._logs = [];
    this._streaming = true;
    this._error = null;
    this._notify();

    if (this._logConnectionState !== 'connected') {
      this.connect();
      return;
    }

    this.sendAction('unsubscribeLogs');
    if (!this.sendAction(
      'subscribeLogs',
      { ...this._activeRequest } as Record<string, unknown>,
    )) {
      this._streaming = false;
      this._error = 'Not connected';
      this._notify();
    }
  }

  stopStream(): void {
    this._activeRequest = null;
    this.sendAction('unsubscribeLogs');
    this._streaming = false;
    this._notify();
  }

  // -- React hooks --------------------------------------------------------------

  static useLogState(): {
    connectionState: LogConnectionState;
    error: string | null;
    logs: LogEntry[];
    streaming: boolean;
  } {
    const [, bump] = useState(0);
    useEffect(() => {
      const cb = () => bump(n => n + 1);
      hookListeners.add(cb);
      logClient?.addListener(cb);
      return () => {
        hookListeners.delete(cb);
        logClient?.removeListener(cb);
      };
    }, []);
    return {
      connectionState: logClient?.connectionState ?? 'disconnected',
      error: logClient?.error ?? null,
      logs: logClient?.logs ?? [],
      streaming: logClient?.streaming ?? false,
    };
  }
}

// -- Module singleton ---------------------------------------------------------

export let logClient: LogWebSocketClient | null = null;
const hookListeners = new Set<() => void>();

export function connectLogClient(): void {
  const port = window.__ATOPILE_CORE_SERVER_PORT__;
  if (!port) return;
  logClient = new LogWebSocketClient(`ws://localhost:${port}/atopile-core`);
  for (const cb of hookListeners) {
    logClient.addListener(cb);
  }
  logClient.connect();
}
