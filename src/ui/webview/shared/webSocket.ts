import { useEffect, useRef, useState, useCallback } from "react";

interface ServerMessage {
  type: "state" | "event" | "action_result";
  data?: Record<string, unknown>;
  event?: string;
  action?: string;
  result?: unknown;
}

interface UseWebSocketResult {
  connected: boolean;
  state: Record<string, unknown>;
  sendAction: (action: string, payload?: unknown) => void;
}

/**
 * React hook that connects to the Hub WebSocket server.
 *
 * Sends a `subscribe` message on connect, handles `state` / `event` /
 * `action_result` messages, and reconnects with exponential backoff.
 */
export function useWebSocket(hubUrl: string): UseWebSocketResult {
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<Record<string, unknown>>({});
  const wsRef = useRef<WebSocket | null>(null);
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
      ws.send(JSON.stringify({ type: "subscribe" }));
    };

    ws.onmessage = (event) => {
      try {
        const msg: ServerMessage = JSON.parse(event.data);
        switch (msg.type) {
          case "state":
            if (msg.data) setState(msg.data);
            break;
          case "event":
            break;
          case "action_result":
            break;
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

  const sendAction = useCallback((action: string, payload?: unknown) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "action", action, payload }));
    }
  }, []);

  return { connected, state, sendAction };
}
