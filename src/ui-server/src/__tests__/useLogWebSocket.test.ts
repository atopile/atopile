/**
 * Integration tests for the useLogWebSocket React hook.
 *
 * Tests coordination between the log WebSocket and the main app WebSocket,
 * including connect/disconnect lifecycle, streaming, and cleanup.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStore } from '../store';

// ---------------------------------------------------------------------------
// MockWebSocket
// ---------------------------------------------------------------------------
class MockWebSocket {
  static CONNECTING = 0 as const;
  static OPEN = 1 as const;
  static CLOSING = 2 as const;
  static CLOSED = 3 as const;
  static instances: MockWebSocket[] = [];
  static latest(): MockWebSocket {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }
  static reset(): void {
    MockWebSocket.instances = [];
  }

  CONNECTING = 0 as const;
  OPEN = 1 as const;
  CLOSING = 2 as const;
  CLOSED = 3 as const;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  simulateOpen(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  simulateClose(code = 1000, reason = ''): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code, reason }));
  }

  simulateMessage(data: unknown): void {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
}

// Install MockWebSocket globally
(globalThis as Record<string, unknown>).WebSocket = MockWebSocket as unknown as typeof WebSocket;

describe('useLogWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.reset();
    (globalThis as Record<string, unknown>).WebSocket = MockWebSocket as unknown as typeof WebSocket;
    // Start with main WS connected
    useStore.setState({ isConnected: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // Dynamic import to avoid config.ts throwing before mocks are ready
  async function getHook() {
    const { useLogWebSocket } = await import('../components/log-viewer/useLogWebSocket');
    return useLogWebSocket;
  }

  it('connects log WS when main WS is connected', async () => {
    const useLogWebSocket = await getHook();
    const { result } = renderHook(() => useLogWebSocket());

    // The hook should auto-connect via the mainWsConnected effect
    await act(async () => {});

    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(1);
    const ws = MockWebSocket.latest();
    expect(ws.url).toContain('/ws/logs');
  });

  it('updates connectionState on open', async () => {
    const useLogWebSocket = await getHook();
    const { result } = renderHook(() => useLogWebSocket());

    await act(async () => {});

    const ws = MockWebSocket.latest();
    act(() => {
      ws.simulateOpen();
    });

    expect(result.current.connectionState).toBe('connected');
  });

  it('pauses log WS reconnect when main WS disconnects', async () => {
    const useLogWebSocket = await getHook();
    const { result } = renderHook(() => useLogWebSocket());

    await act(async () => {});

    const ws = MockWebSocket.latest();
    act(() => {
      ws.simulateOpen();
    });

    // Simulate main WS disconnect
    const countBefore = MockWebSocket.instances.length;
    act(() => {
      useStore.setState({ isConnected: false });
    });

    // Close the log WS
    act(() => {
      ws.simulateClose();
    });

    // Advance timers — no new log WS should be created because main is down
    act(() => {
      vi.advanceTimersByTime(30000);
    });
    expect(MockWebSocket.instances.length).toBe(countBefore);
  });

  it('reconnects log WS when main WS reconnects', async () => {
    const useLogWebSocket = await getHook();
    const { result } = renderHook(() => useLogWebSocket());

    await act(async () => {});

    const ws = MockWebSocket.latest();
    act(() => {
      ws.simulateOpen();
    });

    // Main disconnects
    act(() => {
      useStore.setState({ isConnected: false });
    });
    act(() => {
      ws.simulateClose();
    });

    const countBefore = MockWebSocket.instances.length;

    // Main reconnects — log WS should auto-reconnect
    act(() => {
      useStore.setState({ isConnected: true });
    });

    expect(MockWebSocket.instances.length).toBe(countBefore + 1);
  });

  it('startBuildStream sends correct payload', async () => {
    const useLogWebSocket = await getHook();
    const { result } = renderHook(() => useLogWebSocket());

    await act(async () => {});

    const ws = MockWebSocket.latest();
    act(() => {
      ws.simulateOpen();
    });

    act(() => {
      result.current.startBuildStream({
        build_id: 'build-123',
        stage: null,
        log_levels: null,
        audience: 'developer',
      });
    });

    expect(ws.send).toHaveBeenCalledWith(
      expect.stringContaining('"build_id":"build-123"')
    );
    expect(ws.send).toHaveBeenCalledWith(
      expect.stringContaining('"subscribe":true')
    );
  });

  it('onmessage updates logs state', async () => {
    const useLogWebSocket = await getHook();
    const { result } = renderHook(() => useLogWebSocket());

    await act(async () => {});

    const ws = MockWebSocket.latest();
    act(() => {
      ws.simulateOpen();
    });

    act(() => {
      ws.simulateMessage({
        type: 'logs_result',
        logs: [
          { id: 1, level: 'INFO', message: 'Hello', audience: 'developer' },
        ],
      });
    });

    expect(result.current.logs).toHaveLength(1);
    expect(result.current.logs[0].message).toBe('Hello');
  });

  it('cleans up WebSocket and timers on unmount', async () => {
    const useLogWebSocket = await getHook();
    const { result, unmount } = renderHook(() => useLogWebSocket());

    await act(async () => {});

    const ws = MockWebSocket.latest();
    act(() => {
      ws.simulateOpen();
    });

    unmount();

    expect(ws.close).toHaveBeenCalled();
  });
});
