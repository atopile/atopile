import { useEffect, useState } from "react";
import { MSG_TYPE, StoreState } from "../../shared/types";
import {
  ReconnectScheduler,
  parseMessage,
  sendSubscribe,
} from "../../shared/webSocketUtils";

// -- Module-level state -------------------------------------------------------

let state = new StoreState();
export let ws: WebSocket | null = null;

const listeners = new Set<() => void>();
const subscribedKeys = new Set<keyof StoreState>();

/** Keys managed locally by the provider, not subscribed from the hub. */
const LOCAL_KEYS: ReadonlySet<keyof StoreState> = new Set(["hubStatus"]);

function setState(key: keyof StoreState, data: unknown) {
  state = { ...state, [key]: data } as StoreState;
  for (const fn of listeners) fn();
}

// -- Connection ---------------------------------------------------------------

const reconnect = new ReconnectScheduler();

export function connect(hubUrl: string) {
  function open() {
    if (ws) ws.close();

    const socket = new WebSocket(hubUrl);
    ws = socket;

    socket.onopen = () => {
      reconnect.resetDelay();
      if (subscribedKeys.size > 0) sendSubscribe(ws, [...subscribedKeys]);
      setState("hubStatus", { connected: true });
    };

    socket.onmessage = (event) => {
      const msg = parseMessage(event.data);
      if (msg?.type === MSG_TYPE.STATE) {
        setState(msg.key as keyof StoreState, msg.data);
      }
    };

    socket.onclose = () => {
      ws = null;
      setState("hubStatus", { connected: false });
      reconnect.schedule(open);
    };

    socket.onerror = () => {};
  }

  reconnect.start();
  open();
}

// -- Hook ---------------------------------------------------------------------

export function useSubscribe<K extends keyof StoreState>(key: K): StoreState[K] {
  const [, bump] = useState(0);
  useEffect(() => {
    if (!LOCAL_KEYS.has(key) && !subscribedKeys.has(key)) {
      subscribedKeys.add(key);
      if (ws && ws.readyState === WebSocket.OPEN) {
        sendSubscribe(ws, [...subscribedKeys]);
      }
    }
    const cb = () => bump((n) => n + 1);
    listeners.add(cb);
    return () => { listeners.delete(cb); };
  }, [key]);
  return state[key];
}
