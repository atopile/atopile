/**
 * Integration tests for the WebSocket reconnection state machine.
 *
 * Tests the connect/disconnect/reconnect lifecycle, exponential backoff,
 * backend-status pausing, connection timeout, and cleanup semantics.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// MockWebSocket — test double that records constructor calls
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
    const evt = new CloseEvent('close', { code, reason });
    this.onclose?.(evt);
  }

  simulateError(): void {
    this.onerror?.(new Event('error'));
  }

  simulateMessage(data: unknown): void {
    const evt = new MessageEvent('message', { data: JSON.stringify(data) });
    this.onmessage?.(evt);
  }
}

// ---------------------------------------------------------------------------
// Shared mocks — declared before vi.mock() calls
// ---------------------------------------------------------------------------
const mockSetConnected = vi.fn();
const mockReplaceState = vi.fn();
const mockSetProjects = vi.fn();
const mockSetLogViewerBuildId = vi.fn();

vi.mock('../store', () => ({
  useStore: {
    getState: () => ({
      setConnected: mockSetConnected,
      replaceState: mockReplaceState,
      setProjects: mockSetProjects,
      setLogViewerBuildId: mockSetLogViewerBuildId,
      setBuilds: vi.fn(),
      setQueuedBuilds: vi.fn(),
      setBuildHistory: vi.fn(),
      selectedProjectRoot: null,
      selectedTargetNames: [],
      projects: [],
      builds: [],
      queuedBuilds: [],
    }),
  },
}));

vi.mock('./vscodeApi', () => ({
  postMessage: vi.fn(),
}));

const mockApiProjectsList = vi.fn().mockResolvedValue({ projects: [] });
const mockApiBuildsActive = vi.fn().mockResolvedValue({ builds: [] });
const mockApiBuildsHistory = vi.fn().mockResolvedValue({ builds: [] });

vi.mock('./client', () => ({
  api: {
    projects: { list: mockApiProjectsList },
    builds: { active: mockApiBuildsActive, history: mockApiBuildsHistory },
  },
}));

vi.mock('./config', () => ({
  WS_STATE_URL: 'ws://127.0.0.1:12345/ws/state',
  WS_LOGS_URL: 'ws://127.0.0.1:12345/ws/logs',
  getWorkspaceFolders: () => [],
}));

// ---------------------------------------------------------------------------
// Module-level state: use resetModules + dynamic import per describe block
// ---------------------------------------------------------------------------
type WsModule = typeof import('../api/websocket');

async function freshModule(): Promise<WsModule> {
  vi.resetModules();
  // Re-apply global mock before importing the module
  (globalThis as Record<string, unknown>).WebSocket = MockWebSocket as unknown as typeof WebSocket;
  return import('../api/websocket');
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('websocket reconnection state machine', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.reset();
    (globalThis as Record<string, unknown>).WebSocket = MockWebSocket as unknown as typeof WebSocket;
    mockSetConnected.mockClear();
    mockReplaceState.mockClear();
    mockSetProjects.mockClear();
    mockApiProjectsList.mockClear();
    mockApiBuildsActive.mockClear();
    mockApiBuildsHistory.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('sets isConnected to true on open', async () => {
    const mod = await freshModule();
    mod.connect();

    const ws = MockWebSocket.latest();
    expect(ws).toBeDefined();

    ws.simulateOpen();
    expect(mockSetConnected).toHaveBeenCalledWith(true);
  });

  it('schedules reconnect after close', async () => {
    const mod = await freshModule();
    mod.connect();

    const ws = MockWebSocket.latest();
    ws.simulateOpen();
    ws.simulateClose();

    expect(mockSetConnected).toHaveBeenCalledWith(false);

    // Should schedule reconnect after RECONNECT_DELAY_MS (1000ms)
    const countBefore = MockWebSocket.instances.length;
    vi.advanceTimersByTime(1000);
    expect(MockWebSocket.instances.length).toBe(countBefore + 1);
  });

  it('applies exponential backoff on repeated reconnects', async () => {
    const mod = await freshModule();

    // First connection opens then closes
    mod.connect();
    let ws = MockWebSocket.latest();
    ws.simulateOpen();
    ws.simulateClose();

    // First reconnect at 1000ms (delay = 1000 * 1.5^0 = 1000)
    vi.advanceTimersByTime(999);
    expect(MockWebSocket.instances.length).toBe(1);
    vi.advanceTimersByTime(1);
    expect(MockWebSocket.instances.length).toBe(2);

    // Second WS closes without opening → reconnectAttempts stays incremented
    ws = MockWebSocket.latest();
    ws.simulateClose();

    // Second reconnect at 1500ms (delay = 1000 * 1.5^1 = 1500)
    vi.advanceTimersByTime(1499);
    expect(MockWebSocket.instances.length).toBe(2);
    vi.advanceTimersByTime(1);
    expect(MockWebSocket.instances.length).toBe(3);

    // Third WS closes without opening
    ws = MockWebSocket.latest();
    ws.simulateClose();

    // Third reconnect at 2250ms (delay = 1000 * 1.5^2 = 2250)
    vi.advanceTimersByTime(2249);
    expect(MockWebSocket.instances.length).toBe(3);
    vi.advanceTimersByTime(1);
    expect(MockWebSocket.instances.length).toBe(4);
  });

  it('pauses reconnect when backend is starting', async () => {
    const mod = await freshModule();

    // Notify backend is starting
    mod.notifyBackendStatus('starting', false);

    // Connect and close
    mod.connect();
    const ws = MockWebSocket.latest();
    ws.simulateOpen();
    ws.simulateClose();

    // No reconnect should be scheduled
    const countBefore = MockWebSocket.instances.length;
    vi.advanceTimersByTime(30000);
    expect(MockWebSocket.instances.length).toBe(countBefore);
  });

  it('reconnects immediately when backend transitions to running', async () => {
    const mod = await freshModule();

    // Start with backend down
    mod.notifyBackendStatus('starting', false);
    mod.connect();
    const ws = MockWebSocket.latest();
    ws.simulateOpen();
    ws.simulateClose();

    const countBefore = MockWebSocket.instances.length;

    // Backend becomes running → should reconnect immediately
    mod.notifyBackendStatus('running', false);
    expect(MockWebSocket.instances.length).toBe(countBefore + 1);
  });

  it('handles connection timeout', async () => {
    const mod = await freshModule();
    mod.connect();

    const ws = MockWebSocket.latest();
    // Don't call simulateOpen — stays in CONNECTING
    expect(ws.readyState).toBe(MockWebSocket.CONNECTING);

    // Advance past the 15s connection timeout
    vi.advanceTimersByTime(15000);

    expect(mockSetConnected).toHaveBeenCalledWith(false);

    // Advance past reconnect delay (1000ms) to trigger the reconnect
    vi.advanceTimersByTime(1000);
    expect(MockWebSocket.instances.length).toBeGreaterThan(1);
  });

  it('disconnect prevents all reconnection', async () => {
    const mod = await freshModule();
    mod.connect();

    const ws = MockWebSocket.latest();
    ws.simulateOpen();

    mod.disconnect();
    expect(mockSetConnected).toHaveBeenCalledWith(false);

    // Advance timers — no new WS should be created
    const countAfter = MockWebSocket.instances.length;
    vi.advanceTimersByTime(60000);
    expect(MockWebSocket.instances.length).toBe(countAfter);
  });

  it('cleanup rejects pending sendActionWithResponse promises', async () => {
    const mod = await freshModule();
    mod.connect();

    const ws = MockWebSocket.latest();
    ws.simulateOpen();

    // Send an action that expects a response
    const promise = mod.sendActionWithResponse('testAction', {});

    // Disconnect (which calls cleanup)
    mod.disconnect();

    await expect(promise).rejects.toThrow('WebSocket disconnected');
  });
});
