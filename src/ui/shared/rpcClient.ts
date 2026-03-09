import type { StoreKey } from "./generated-types";
import { MSG_TYPE, type RpcMessage } from "./types";
import type { RpcTransport } from "./rpcTransport";

class ReconnectScheduler {
  private _delay: number;
  private readonly _initialDelay: number;
  private readonly _maxDelay: number;
  private _timer: ReturnType<typeof setTimeout> | null = null;
  private _stopped = true;

  constructor(initialDelay = 1000, maxDelay = 10000) {
    this._delay = initialDelay;
    this._initialDelay = initialDelay;
    this._maxDelay = maxDelay;
  }

  resetDelay(): void {
    this._delay = this._initialDelay;
  }

  schedule(fn: () => void): void {
    if (this._stopped) {
      return;
    }

    this._timer = setTimeout(() => {
      this._timer = null;
      fn();
    }, this._delay);
    this._delay = Math.min(this._delay * 2, this._maxDelay);
  }

  start(): void {
    this._stopped = false;
  }

  stop(): void {
    this._stopped = true;
    if (this._timer) {
      clearTimeout(this._timer);
      this._timer = null;
    }
  }
}

export function parseMessage(data: unknown): RpcMessage | null {
  try {
    const str = typeof data === "string" ? data : String(data);
    const msg = JSON.parse(str);
    if (
      msg?.type === MSG_TYPE.SUBSCRIBE ||
      msg?.type === MSG_TYPE.STATE ||
      msg?.type === MSG_TYPE.ACTION ||
      msg?.type === MSG_TYPE.ACTION_RESULT
    ) {
      return msg as RpcMessage;
    }
    return null;
  } catch {
    return null;
  }
}

export interface RpcClientOptions {
  reconnect?: boolean;
}

export class RpcClient {
  private readonly _createTransport: () => RpcTransport;
  private readonly _reconnect: ReconnectScheduler | null;
  private readonly _subscribedKeys = new Set<string>();
  private readonly _pendingRequests = new Map<
    string,
    {
      action: string;
      resolve: (value: any) => void;
      reject: (error: Error) => void;
    }
  >();
  private _transport: RpcTransport | null = null;
  private _connected = false;
  private _requestCounter = 0;

  onState: ((key: StoreKey, data: unknown) => void) | null = null;
  onConnected: (() => void) | null = null;
  onDisconnected: (() => void) | null = null;
  onRawMessage: ((data: string) => void) | null = null;

  constructor(createTransport: () => RpcTransport, opts?: RpcClientOptions) {
    this._createTransport = createTransport;
    this._reconnect = opts?.reconnect === false ? null : new ReconnectScheduler();
  }

  get isConnected(): boolean {
    return this._connected;
  }

  connect(): Promise<void> {
    this._reconnect?.start();
    return new Promise<void>((resolve, reject) => {
      let settled = false;
      const settle = (fn: () => void) => {
        if (!settled) {
          settled = true;
          fn();
        }
      };

      const open = () => {
        this._transport?.close();

        const transport = this._createTransport();
        this._transport = transport;

        transport.onOpen = () => {
          this._connected = true;
          this._reconnect?.resetDelay();
          if (this._subscribedKeys.size > 0) {
            this._sendSubscribe([...this._subscribedKeys]);
          }
          this.onConnected?.();
          settle(() => resolve());
        };

        transport.onMessage = (data) => {
          this.onRawMessage?.(data);
          const msg = parseMessage(data);
          if (msg?.type === MSG_TYPE.STATE) {
            this.onState?.(msg.key, msg.data);
            return;
          }
          if (msg?.type === MSG_TYPE.ACTION_RESULT) {
            this._handleActionResult(msg);
          }
        };

        transport.onClose = () => {
          this._connected = false;
          transport.close();
          if (this._transport === transport) {
            this._transport = null;
          }
          this.onDisconnected?.();
          this._reconnect?.schedule(open);
          if (!this._reconnect) {
            settle(() => reject(new Error("RPC transport closed before open")));
          }
        };

        transport.connect();
      };

      open();
    });
  }

  subscribe(keys: StoreKey[]): void {
    for (const key of keys) {
      this._subscribedKeys.add(key);
    }
    if (this._connected && this._subscribedKeys.size > 0) {
      this._sendSubscribe([...this._subscribedKeys]);
    }
  }

  sendRaw(data: string): boolean {
    if (!this._transport) {
      return false;
    }
    try {
      this._transport.send(data);
      return true;
    } catch {
      return false;
    }
  }

  sendAction(action: string, payload?: Record<string, unknown>): boolean {
    return this.sendRaw(JSON.stringify({ type: MSG_TYPE.ACTION, action, ...payload }));
  }

  requestAction<T>(action: string, payload?: Record<string, unknown>): Promise<T> {
    const requestId = `rpc-${this._requestCounter++}`;

    return new Promise<T>((resolve, reject) => {
      this._pendingRequests.set(requestId, {
        action,
        resolve: (value: unknown) => resolve(value as T),
        reject,
      });
      const ok = this.sendRaw(
        JSON.stringify({
          type: MSG_TYPE.ACTION,
          action,
          requestId,
          ...payload,
        }),
      );
      if (!ok) {
        this._pendingRequests.delete(requestId);
        reject(new Error("RPC transport is not available"));
      }
    });
  }

  close(): void {
    this._reconnect?.stop();
    this._connected = false;
    this._rejectPendingRequests(new Error("RPC transport closed"));
    this._transport?.close();
    this._transport = null;
  }

  private _sendSubscribe(keys: string[]): boolean {
    return this.sendRaw(JSON.stringify({ type: MSG_TYPE.SUBSCRIBE, keys }));
  }

  private _handleActionResult(msg: Extract<RpcMessage, { type: typeof MSG_TYPE.ACTION_RESULT }>): void {
    if (!msg.requestId) {
      return;
    }

    const pending = this._pendingRequests.get(msg.requestId);
    if (!pending) {
      return;
    }
    this._pendingRequests.delete(msg.requestId);

    if (msg.ok === false) {
      pending.reject(new Error(msg.error || `${pending.action} failed`));
      return;
    }

    pending.resolve(msg.result as unknown);
  }

  private _rejectPendingRequests(error: Error): void {
    for (const pending of this._pendingRequests.values()) {
      pending.reject(error);
    }
    this._pendingRequests.clear();
  }
}
