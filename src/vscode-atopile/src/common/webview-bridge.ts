/**
 * Shared extension-side proxy bridge for webview providers.
 *
 * Handles fetch and WebSocket proxy messages from webviews running in
 * sandboxed HTTPS iframes (e.g. OpenVSCode Server) where direct
 * localhost access is blocked by Mixed Content / CORS.
 */

import { WebSocket as NodeWebSocket } from 'ws';
import { backendServer } from './backendServer';
import { traceInfo, traceError } from './log/logging';

// ── Shared message interfaces ────────────────────────────────────────

export interface FetchProxyRequest {
  type: 'fetchProxy';
  id: number;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string | null;
}

export interface WsProxyConnect {
  type: 'wsProxyConnect';
  id: number;
  url: string;
}

export interface WsProxySend {
  type: 'wsProxySend';
  id: number;
  data: string;
}

export interface WsProxyClose {
  type: 'wsProxyClose';
  id: number;
  code?: number;
  reason?: string;
}

// ── Bridge options ───────────────────────────────────────────────────

export interface WebviewProxyBridgeOptions {
  /** Post a message back to the webview. */
  postToWebview: (msg: Record<string, unknown>) => void;
  /** Enable WebSocket retry on transient errors (default true). */
  wsRetry?: boolean;
  /** Maximum number of retry attempts (default 8). */
  wsMaxRetries?: number;
  /** Delay between retries in milliseconds (default 500). */
  wsRetryDelayMs?: number;
  /** Prefix for log messages (default 'WebviewBridge'). */
  logTag?: string;
}

// ── Bridge class ─────────────────────────────────────────────────────

export class WebviewProxyBridge {
  private readonly _post: (msg: Record<string, unknown>) => void;
  private readonly _wsRetry: boolean;
  private readonly _wsMaxRetries: number;
  private readonly _wsRetryDelayMs: number;
  private readonly _tag: string;

  private readonly _wsProxies: Map<number, NodeWebSocket> = new Map();
  private readonly _wsProxyRetryTimers: Map<number, NodeJS.Timeout> = new Map();

  constructor(opts: WebviewProxyBridgeOptions) {
    this._post = opts.postToWebview;
    this._wsRetry = opts.wsRetry ?? true;
    this._wsMaxRetries = opts.wsMaxRetries ?? 8;
    this._wsRetryDelayMs = opts.wsRetryDelayMs ?? 500;
    this._tag = opts.logTag ?? 'WebviewBridge';
  }

  /**
   * Try to handle a message from the webview.
   * Returns `true` if the message was a proxy message and was handled.
   */
  handleMessage(msg: { type?: string }): boolean {
    switch (msg.type) {
      case 'fetchProxy':
        this._handleFetchProxy(msg as unknown as FetchProxyRequest);
        return true;
      case 'wsProxyConnect':
        this._handleWsProxyConnect(msg as unknown as WsProxyConnect);
        return true;
      case 'wsProxySend':
        this._handleWsProxySend(msg as unknown as WsProxySend);
        return true;
      case 'wsProxyClose':
        this._handleWsProxyClose(msg as unknown as WsProxyClose);
        return true;
      default:
        return false;
    }
  }

  /** Clean up all WebSocket connections and retry timers. */
  dispose(): void {
    for (const ws of this._wsProxies.values()) {
      ws.removeAllListeners();
      ws.close();
    }
    this._wsProxies.clear();
    for (const timer of this._wsProxyRetryTimers.values()) {
      clearTimeout(timer);
    }
    this._wsProxyRetryTimers.clear();
  }

  // ── Fetch proxy ──────────────────────────────────────────────────

  private _handleFetchProxy(req: FetchProxyRequest): void {
    // Rewrite the URL to use the internal backend address.
    // The webview sends the browser-visible URL (e.g. https://host/proxy/8501/...),
    // but the extension host should always connect directly to the local backend.
    let url = req.url;
    try {
      const externalBase = backendServer.apiUrl;
      const internalBase = backendServer.internalApiUrl || externalBase;
      if (externalBase && internalBase && url.startsWith(externalBase)) {
        url = internalBase + url.slice(externalBase.length);
      }
    } catch {
      // Use URL as-is if rewriting fails
    }

    const init: Record<string, unknown> = {
      method: req.method,
      headers: req.headers,
    };
    if (req.body && req.method !== 'GET' && req.method !== 'HEAD') {
      init.body = req.body;
    }

    // Use Node.js native fetch (available since Node 18)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).fetch(url, init)
      .then(async (response: { text: () => Promise<string>; status: number; statusText: string; headers: { forEach: (cb: (v: string, k: string) => void) => void } }) => {
        const body = await response.text();
        const headers: Record<string, string> = {};
        response.headers.forEach((value: string, key: string) => {
          headers[key] = value;
        });
        this._post({
          type: 'fetchProxyResult',
          id: req.id,
          status: response.status,
          statusText: response.statusText,
          headers,
          body,
        });
      })
      .catch((err: Error) => {
        this._post({
          type: 'fetchProxyResult',
          id: req.id,
          error: String(err),
        });
      });
  }

  // ── WebSocket proxy ──────────────────────────────────────────────

  private _handleWsProxyConnect(msg: WsProxyConnect): void {
    this._clearWsProxyRetry(msg.id);

    // Close any existing proxy with the same id
    const existing = this._wsProxies.get(msg.id);
    if (existing) {
      existing.removeAllListeners();
      existing.close();
      this._wsProxies.delete(msg.id);
    }

    // Rewrite the URL to use the internal backend address.
    let targetUrl = msg.url;
    try {
      const parsed = new URL(msg.url);
      const internalBase = backendServer.internalApiUrl || backendServer.apiUrl;
      if (internalBase) {
        const internal = new URL(internalBase);
        const wsProtocol = internal.protocol === 'https:' ? 'wss:' : 'ws:';
        const port = internal.port ? `:${internal.port}` : '';
        targetUrl = `${wsProtocol}//${internal.hostname}${port}${parsed.pathname}${parsed.search}`;
      }
    } catch {
      // Use the URL as-is if parsing fails
    }

    this._connectWsProxy(msg.id, targetUrl, 0);
  }

  private _connectWsProxy(id: number, targetUrl: string, attempt: number): void {
    traceInfo(`[${this._tag}][WsProxy] Connecting id=${id} to ${targetUrl}${attempt > 0 ? ` (attempt ${attempt})` : ''}`);
    const ws = new NodeWebSocket(targetUrl);
    this._wsProxies.set(id, ws);

    let suppressClose = false;

    ws.on('open', () => {
      this._clearWsProxyRetry(id);
      traceInfo(`[${this._tag}][WsProxy] Connected id=${id}`);
      this._post({ type: 'wsProxyOpen', id });
    });

    ws.on('message', (data: Buffer | string) => {
      const payload = typeof data === 'string' ? data : data.toString('utf-8');
      this._post({ type: 'wsProxyMessage', id, data: payload });
    });

    ws.on('close', (code: number, reason: Buffer) => {
      this._wsProxies.delete(id);
      if (suppressClose) {
        return;
      }

      traceInfo(`[${this._tag}][WsProxy] Closed id=${id} code=${code}`);
      this._post({
        type: 'wsProxyClose',
        id,
        code,
        reason: reason.toString('utf-8'),
      });
    });

    ws.on('error', (err: Error) => {
      if (this._wsRetry) {
        const backendNotReady = backendServer.serverState !== 'running' || !backendServer.isConnected;
        const shouldRetry =
          this._isTransientWsProxyError(err) &&
          backendNotReady &&
          attempt < this._wsMaxRetries;

        if (shouldRetry) {
          suppressClose = true;
          this._wsProxies.delete(id);
          traceInfo(`[${this._tag}][WsProxy] Backend starting, delaying id=${id}: ${err.message}`);
          this._scheduleWsProxyRetry(id, targetUrl, attempt + 1);
          try {
            ws.removeAllListeners();
            ws.close();
          } catch {
            // Ignore close failures during transient reconnect handling.
          }
          return;
        }
      }

      traceError(`[${this._tag}][WsProxy] Error id=${id}: ${err.message}`);
      this._post({ type: 'wsProxyError', id, error: err.message });
    });
  }

  private _handleWsProxySend(msg: WsProxySend): void {
    const ws = this._wsProxies.get(msg.id);
    if (ws?.readyState === NodeWebSocket.OPEN) {
      ws.send(msg.data);
    }
  }

  private _handleWsProxyClose(msg: WsProxyClose): void {
    this._clearWsProxyRetry(msg.id);
    const ws = this._wsProxies.get(msg.id);
    if (ws) {
      ws.close(msg.code ?? 1000, msg.reason ?? '');
      this._wsProxies.delete(msg.id);
    }
  }

  // ── Retry helpers ────────────────────────────────────────────────

  private _clearWsProxyRetry(id: number): void {
    const timer = this._wsProxyRetryTimers.get(id);
    if (timer) {
      clearTimeout(timer);
      this._wsProxyRetryTimers.delete(id);
    }
  }

  private _scheduleWsProxyRetry(id: number, targetUrl: string, attempt: number): void {
    this._clearWsProxyRetry(id);

    traceInfo(`[${this._tag}][WsProxy] Retrying id=${id} in ${this._wsRetryDelayMs}ms (attempt ${attempt})`);

    const timer = setTimeout(() => {
      this._wsProxyRetryTimers.delete(id);
      // Do not reconnect if this socket id has been replaced or explicitly closed.
      if (this._wsProxies.has(id)) {
        return;
      }
      this._connectWsProxy(id, targetUrl, attempt);
    }, this._wsRetryDelayMs);

    this._wsProxyRetryTimers.set(id, timer);
  }

  private _isTransientWsProxyError(err: Error): boolean {
    const message = (err.message || '').toUpperCase();
    return (
      message.includes('ECONNREFUSED') ||
      message.includes('ECONNRESET') ||
      message.includes('EHOSTUNREACH') ||
      message.includes('ETIMEDOUT')
    );
  }
}
