import { useEffect, useRef, useState, useCallback } from "react";

interface ServerMessage {
  type: "state";
  key: string;
  data?: unknown;
}

interface UseWebSocketResult {
  connected: boolean;
  state: Record<string, unknown>;
  sendAction: (action: string, payload?: Record<string, unknown>) => void;
}

/**
 * React hook that connects to the Hub WebSocket server.
 *
 * Subscribes to specific store keys. When a key changes, the full
 * value for that key is received and replaced (no merging).
 * Reconnects with exponential backoff.
 */
export function useWebSocket(hubUrl: string, keys: string[]): UseWebSocketResult {
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<Record<string, unknown>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const keysRef = useRef(keys);
  keysRef.current = keys;
  const reconnectDelay = useRef(1000);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const disposed = useRef(false);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(hubUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectDelay.current = 1000;
      ws.send(JSON.stringify({ type: "subscribe", keys: keysRef.current }));
    };

    ws.onmessage = (event) => {
      try {
        const msg: ServerMessage = JSON.parse(event.data);
        if (msg.type === "state" && msg.key !== undefined) {
          setState((prev) => ({ ...prev, [msg.key]: msg.data }));
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      if (disposed.current) return;
      reconnectTimer.current = setTimeout(() => {
        reconnectTimer.current = null;
        connect();
      }, reconnectDelay.current);
      reconnectDelay.current = Math.min(reconnectDelay.current * 2, 10000);
    };

    ws.onerror = () => {};
  }, [hubUrl]);

  useEffect(() => {
    disposed.current = false;
    connect();

    return () => {
      disposed.current = true;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const sendAction = useCallback(
    (action: string, payload?: Record<string, unknown>) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({ type: "action", action, ...payload })
        );
      }
    },
    []
  );

  return { connected, state, sendAction };
}
