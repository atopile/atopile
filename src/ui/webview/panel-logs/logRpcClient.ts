import { useEffect, useState } from "react";
import { WebSocketTransport } from "../../shared/webSocketTransport";
import type { SocketLike } from "../../shared/rpcTransport";
import type {
  UiBuildLogRequest,
  UiLogEntry,
  UiLogsErrorMessage,
  UiTestLogRequest,
} from "../../shared/generated-types";

type VscodeRpcClient = {
  addRawListener(listener: (data: string) => void): void;
  removeRawListener(listener: (data: string) => void): void;
  addConnectionListener(listener: (connected: boolean) => void): void;
  removeConnectionListener(listener: (connected: boolean) => void): void;
  sendAction(action: string, payload?: Record<string, unknown>): boolean;
  isConnected(): boolean;
};

export type LogConnectionState = "disconnected" | "connecting" | "connected";
export type LogRequest =
  | ({ kind: "build" } & UiBuildLogRequest)
  | ({ kind: "test" } & UiTestLogRequest);
export type LogTarget =
  | {
      mode: "build";
      buildId: string;
      stage: string | null;
    }
  | {
      mode: "test";
      testRunId: string;
      testName: string | null;
    };

type RawLogMessage =
  | UiLogsErrorMessage
  | {
      type: "logs_stream" | "logs_result" | "test_logs_stream" | "test_logs_result";
      buildId?: string;
      build_id?: string;
      testRunId?: string;
      test_run_id?: string;
      stage?: string | null;
      testName?: string | null;
      test_name?: string | null;
      logs: unknown[];
      last_id?: number;
      lastId?: number;
    };

function getRequestIdentity(message: RawLogMessage): {
  kind: "build" | "test" | null;
  buildId: string | null;
  testRunId: string | null;
  stage: string | null;
  testName: string | null;
} {
  switch (message.type) {
    case "logs_stream":
    case "logs_result":
      return {
        kind: "build",
        buildId:
          (typeof message.buildId === "string" ? message.buildId : message.build_id) ??
          null,
        testRunId: null,
        stage: (typeof message.stage === "string" ? message.stage : null) ?? null,
        testName: null,
      };
    case "test_logs_stream":
    case "test_logs_result":
      return {
        kind: "test",
        buildId: null,
        testRunId:
          (typeof message.testRunId === "string"
            ? message.testRunId
            : message.test_run_id) ?? null,
        stage: null,
        testName:
          (typeof message.testName === "string" ? message.testName : message.test_name) ??
          null,
      };
    default:
      return {
        kind: null,
        buildId: null,
        testRunId: null,
        stage: null,
        testName: null,
      };
  }
}

function matchesActiveRequest(
  request: LogRequest | null,
  message: RawLogMessage,
): boolean {
  if (!request) {
    return false;
  }
  const identity = getRequestIdentity(message);
  if (identity.kind !== request.kind) {
    return false;
  }
  if (request.kind === "build") {
    return (
      identity.buildId === request.buildId &&
      identity.stage === (request.stage ?? null)
    );
  }
  return (
    identity.testRunId === request.testRunId &&
    identity.testName === (request.testName ?? null)
  );
}

interface LogTransport {
  connect(): void;
  disconnect(): void;
  isConnected(): boolean;
  addRawListener(listener: (data: string) => void): void;
  removeRawListener(listener: (data: string) => void): void;
  addConnectionListener(listener: (connected: boolean) => void): void;
  removeConnectionListener(listener: (connected: boolean) => void): void;
  startStream(request: LogRequest): void;
  stopStream(): void;
}

function normalizeLogEntry(entry: unknown, mode: "build" | "test"): UiLogEntry {
  const record = entry as Record<string, unknown>;
  return {
    id: (record.id as number | null | undefined) ?? null,
    timestamp: String(record.timestamp ?? ""),
    level: String(record.level ?? "INFO") as UiLogEntry["level"],
    audience: String(record.audience ?? "developer") as UiLogEntry["audience"],
    loggerName: String(record.loggerName ?? record.logger_name ?? ""),
    message: String(record.message ?? ""),
    testName:
      (record.testName as string | null | undefined) ??
      (record.test_name as string | null | undefined) ??
      (mode === "test" ? "" : null),
    stage:
      (record.stage as string | null | undefined) ?? null,
    sourceFile:
      (record.sourceFile as string | null | undefined) ??
      (record.source_file as string | null | undefined) ??
      null,
    sourceLine:
      (record.sourceLine as number | null | undefined) ??
      (record.source_line as number | null | undefined) ??
      null,
    atoTraceback:
      (record.atoTraceback as string | null | undefined) ??
      (record.ato_traceback as string | null | undefined) ??
      null,
    pythonTraceback:
      (record.pythonTraceback as string | null | undefined) ??
      (record.python_traceback as string | null | undefined) ??
      null,
    objects: record.objects ?? null,
  };
}

function serializeVscodeRequest(request: LogRequest): Record<string, unknown> {
  if (request.kind === "build") {
    return {
      buildId: request.buildId,
      stage: request.stage,
      logLevels: request.logLevels,
      audience: request.audience,
      count: request.count,
    };
  }
  return {
    testRunId: request.testRunId,
    testName: request.testName,
    logLevels: request.logLevels,
    audience: request.audience,
    count: request.count,
  };
}

function serializeWebSocketRequest(
  request: LogRequest,
  subscribe: boolean,
): Record<string, unknown> {
  if (request.kind === "build") {
    return {
      build_id: request.buildId,
      stage: request.stage,
      log_levels: request.logLevels,
      audience: request.audience,
      subscribe,
      ...(request.count == null ? {} : { count: request.count }),
    };
  }
  return {
    test_run_id: request.testRunId,
    test_name: request.testName,
    log_levels: request.logLevels,
    audience: request.audience,
    subscribe,
    ...(request.count == null ? {} : { count: request.count }),
  };
}

export function createLogRequest(
  target: LogTarget,
  filters: {
    audience: UiBuildLogRequest["audience"];
    logLevels: UiBuildLogRequest["logLevels"] extends infer T
      ? Exclude<T, null>
      : never;
    count?: number | null;
  },
): LogRequest {
  const shared = {
    audience: filters.audience,
    count: filters.count ?? null,
    logLevels: filters.logLevels.length > 0 ? filters.logLevels : null,
  };

  if (target.mode === "test") {
    return {
      kind: "test",
      testRunId: target.testRunId.trim(),
      testName: target.testName?.trim() || null,
      ...shared,
    };
  }

  return {
    kind: "build",
    buildId: target.buildId.trim(),
    stage: target.stage?.trim() || null,
    ...shared,
  };
}

export class LogRpcClient {
  private _logs: UiLogEntry[] = [];
  private _streaming = false;
  private _error: string | null = null;
  private _connectionState: LogConnectionState = "disconnected";
  private _activeRequest: LogRequest | null = null;
  private _listeners = new Set<() => void>();

  constructor(private readonly _transport: LogTransport) {
    this._connectionState = _transport.isConnected() ? "connected" : "disconnected";
    _transport.addRawListener(this._handleRawMessage);
    _transport.addConnectionListener(this._handleConnectionChange);
  }

  connect(): void {
    this._transport.connect();
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
    this._transport.removeRawListener(this._handleRawMessage);
    this._transport.removeConnectionListener(this._handleConnectionChange);
    this._transport.disconnect();
  }

  clearLogs(): void {
    this._logs = [];
    this._notify();
  }

  startStream(request: LogRequest): void {
    if (request.kind === "build" && !request.buildId.trim()) {
      this._error = "Build ID is required";
      this._notify();
      return;
    }
    if (request.kind === "test" && !request.testRunId.trim()) {
      this._error = "Test run ID is required";
      this._notify();
      return;
    }

    this._activeRequest = request;
    this._logs = [];
    this._streaming = true;
    this._error = null;
    this._notify();

    if (!this._transport.isConnected()) {
      this._connectionState = "connecting";
      this._transport.connect();
      this._notify();
      return;
    }

    this._sendSubscription();
  }

  stopStream(): void {
    this._activeRequest = null;
    this._transport.stopStream();
    this._streaming = false;
    this._notify();
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
    let message: RawLogMessage;
    try {
      message = JSON.parse(data) as RawLogMessage;
    } catch {
      return;
    }
    if (
      message.type !== "logs_stream" &&
      message.type !== "logs_result" &&
      message.type !== "test_logs_stream" &&
      message.type !== "test_logs_result" &&
      message.type !== "logs_error"
    ) {
      return;
    }
    if (!matchesActiveRequest(this._activeRequest, message)) {
      return;
    }
    if (message.type === "logs_error") {
      this._error = message.error;
      this._streaming = false;
      this._notify();
      return;
    }
    const isAppend =
      message.type === "logs_stream" || message.type === "test_logs_stream";
    const mode = message.type.startsWith("test_") ? "test" : "build";
    const entries = (message.logs || []).map((entry) => normalizeLogEntry(entry, mode));
    this._logs = isAppend ? [...this._logs, ...entries] : entries;
    this._error = null;
    this._notify();
  };

  private _sendSubscription(): void {
    if (!this._activeRequest) return;
    try {
      this._transport.startStream(this._activeRequest);
      this._streaming = true;
      this._error = null;
    } catch {
      this._streaming = false;
      this._error = "Not connected";
    }
    this._notify();
  }

  private _notify(): void {
    for (const listener of this._listeners) {
      listener();
    }
  }
}

export function useLogState(client: LogRpcClient | null): {
  connectionState: LogConnectionState;
  error: string | null;
  logs: UiLogEntry[];
  streaming: boolean;
} {
  const [, bump] = useState(0);

  useEffect(() => {
    if (!client) {
      return;
    }

    const callback = () => bump((value) => value + 1);
    client.addListener(callback);
    return () => {
      client.removeListener(callback);
    };
  }, [client]);

  return {
    connectionState: client?.connectionState ?? "disconnected",
    error: client?.error ?? null,
    logs: client?.logs ?? [],
    streaming: client?.streaming ?? false,
  };
}

export function createLogClient(
  config:
    | { mode: "vscode"; rpcClient: VscodeRpcClient }
    | { mode: "standalone"; apiUrl: string },
): LogRpcClient {
  if (config.mode === "vscode") {
    return new LogRpcClient({
      connect() {},
      disconnect() {},
      isConnected: () => config.rpcClient.isConnected(),
      addRawListener: (listener) => config.rpcClient.addRawListener(listener),
      removeRawListener: (listener) => config.rpcClient.removeRawListener(listener),
      addConnectionListener: (listener) =>
        config.rpcClient.addConnectionListener(listener),
      removeConnectionListener: (listener) =>
        config.rpcClient.removeConnectionListener(listener),
      startStream(request) {
        config.rpcClient.sendAction("unsubscribeLogs");
        config.rpcClient.sendAction("subscribeLogs", serializeVscodeRequest(request));
      },
      stopStream() {
        config.rpcClient.sendAction("unsubscribeLogs");
      },
    });
  }
  const wsUrl = new URL("/ws/logs", config.apiUrl).toString().replace(/^http/, "ws");
  const transport = new WebSocketTransport(
    () => new WebSocket(wsUrl) as unknown as SocketLike,
  );
  let connected = false;
  const rawListeners = new Set<(data: string) => void>();
  const connectionListeners = new Set<(connected: boolean) => void>();
  transport.onOpen = () => {
    connected = true;
    for (const listener of connectionListeners) {
      listener(true);
    }
  };
  transport.onClose = () => {
    connected = false;
    for (const listener of connectionListeners) {
      listener(false);
    }
  };
  transport.onMessage = (data) => {
    for (const listener of rawListeners) {
      listener(data);
    }
  };
  return new LogRpcClient({
    connect: () => transport.connect(),
    disconnect: () => transport.close(),
    isConnected: () => connected,
    addRawListener: (listener) => rawListeners.add(listener),
    removeRawListener: (listener) => rawListeners.delete(listener),
    addConnectionListener: (listener) => connectionListeners.add(listener),
    removeConnectionListener: (listener) => connectionListeners.delete(listener),
    startStream(request) {
      transport.send(JSON.stringify(serializeWebSocketRequest(request, true)));
    },
    stopStream() {
      if (connected) {
        transport.send(JSON.stringify({ unsubscribe: true }));
      }
    },
  });
}
