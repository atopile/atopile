/**
 * WebSocket hook for log streaming
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { WS_LOGS_URL } from '../../api';
import {
  ConnectionState,
  LogEntry,
  LogResult,
  LogLevel,
  Audience,
  BuildLogRequest,
  TestLogRequest,
} from './logTypes';

export interface UseLogWebSocketOptions {
  onLogsReceived?: (logs: LogEntry[], isAppend: boolean) => void;
}

export interface UseLogWebSocketReturn {
  connectionState: ConnectionState;
  error: string | null;
  logs: LogEntry[];
  streaming: boolean;
  lastId: number;
  wsUrl: string | null;
  setLogs: React.Dispatch<React.SetStateAction<LogEntry[]>>;
  connect: () => void;
  startBuildStream: (request: BuildLogRequest) => void;
  startTestStream: (request: TestLogRequest) => void;
  stopStream: () => void;
  sendRequest: (payload: BuildLogRequest | TestLogRequest) => void;
}

export function useLogWebSocket(options: UseLogWebSocketOptions = {}): UseLogWebSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [wsUrl, setWsUrl] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const reconnectAttempts = useRef(0);
  const lastIdRef = useRef(0);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setConnectionState('connecting');
    setWsUrl(WS_LOGS_URL);

    const ws = new WebSocket(WS_LOGS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      reconnectAttempts.current = 0;
      setConnectionState('connected');
      setError(null);
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;

      wsRef.current = null;
      setConnectionState('disconnected');
      setStreaming(false);

      // Exponential backoff: 1s, 2s, 4s, 8s, max 10s
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
      reconnectAttempts.current++;

      reconnectTimeoutRef.current = window.setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, delay);
    };

    ws.onerror = () => {
      if (mountedRef.current) {
        setError('Connection failed - retrying...');
      }
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data) as LogResult;

        if (data.type === 'logs_result' || data.type === 'test_logs_result') {
          // One-shot response - replace logs
          setLogs(data.logs);
          setError(null);
          options.onLogsReceived?.(data.logs, false);
        } else if (data.type === 'logs_stream' || data.type === 'test_logs_stream') {
          // Streaming response - append logs
          if (data.logs.length > 0) {
            setLogs(prev => [...prev, ...data.logs]);
            lastIdRef.current = data.last_id;
            options.onLogsReceived?.(data.logs, true);
          }
          setError(null);
        } else if (data.type === 'logs_error') {
          setError(data.error);
          setStreaming(false);
        }
      } catch (e) {
        setError(`Failed to parse response: ${e}`);
      }
    };
  }, [options]);

  // Track mounted state and cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  // Expose connect function for lazy connection
  const ensureConnected = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
      connect();
    }
  }, [connect]);

  const sendRequest = useCallback((payload: BuildLogRequest | TestLogRequest) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (e) {
      setError(`Failed to send request: ${e}`);
    }
  }, []);

  const startBuildStream = useCallback((request: BuildLogRequest) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    if (!request.build_id.trim()) {
      setError('Build ID is required');
      return;
    }

    setLogs([]);
    lastIdRef.current = 0;
    setStreaming(true);
    setError(null);

    const payload: BuildLogRequest = {
      ...request,
      after_id: 0,
      count: request.count ?? 1000,
      subscribe: true,
    };

    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (e) {
      setStreaming(false);
      setError(`Failed to start streaming: ${e}`);
    }
  }, []);

  const startTestStream = useCallback((request: TestLogRequest) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    if (!request.test_run_id.trim()) {
      setError('Test Run ID is required');
      return;
    }

    setLogs([]);
    lastIdRef.current = 0;
    setStreaming(true);
    setError(null);

    const payload: TestLogRequest = {
      ...request,
      after_id: 0,
      count: request.count ?? 1000,
      subscribe: true,
    };

    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (e) {
      setStreaming(false);
      setError(`Failed to start streaming: ${e}`);
    }
  }, []);

  const stopStream = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ unsubscribe: true }));
    }
    setStreaming(false);
  }, []);

  return {
    connectionState,
    error,
    logs,
    streaming,
    lastId: lastIdRef.current,
    wsUrl,
    setLogs,
    connect: ensureConnected,
    startBuildStream,
    startTestStream,
    stopStream,
    sendRequest,
  };
}

// Helper to build request payloads
export function buildBuildLogRequest(
  buildId: string,
  stage: string,
  logLevels: LogLevel[],
  audience: Audience
): BuildLogRequest {
  return {
    build_id: buildId.trim(),
    stage: stage.trim() || null,
    log_levels: logLevels.length > 0 ? logLevels : null,
    audience,
  };
}

export function buildTestLogRequest(
  testRunId: string,
  testName: string | null | undefined,
  logLevels: LogLevel[],
  audience: Audience
): TestLogRequest {
  return {
    test_run_id: testRunId.trim(),
    test_name: testName?.trim() || null,
    log_levels: logLevels.length > 0 ? logLevels : null,
    audience,
  };
}
