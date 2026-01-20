/**
 * WebSocket client for agent streaming and global events
 * Works in both browser and Node.js/Bun environments
 *
 * Note: In Node.js, you need to provide a WebSocket implementation (e.g., 'ws' package)
 * via the constructor. In browser, native WebSocket is used.
 */

import type { StreamEvent, GlobalEvent } from './types';

export type MessageHandler = (event: StreamEvent) => void;
export type GlobalMessageHandler = (event: GlobalEvent) => void;
export type ErrorHandler = (error: Event | Error) => void;
export type CloseHandler = (code: number, reason: string) => void;

interface ConnectionHandlers {
  onMessage?: MessageHandler;
  onError?: ErrorHandler;
  onClose?: CloseHandler;
}

interface Connection {
  ws: WebSocket;
  handlers: ConnectionHandlers;
  reconnectAttempts: number;
}

// WebSocket interface for cross-environment compatibility
type WebSocketConstructor = new (url: string) => WebSocket;

export class WebSocketClient {
  private baseUrl: string;
  private connections: Map<string, Connection> = new Map();
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private WebSocketImpl: WebSocketConstructor;

  constructor(baseUrl: string, wsImpl?: WebSocketConstructor) {
    this.baseUrl = baseUrl;
    // Use provided WebSocket implementation or fall back to global
    this.WebSocketImpl = wsImpl || (typeof WebSocket !== 'undefined' ? WebSocket : undefined as unknown as WebSocketConstructor);

    if (!this.WebSocketImpl) {
      throw new Error('WebSocket is not available. In Node.js, provide a WebSocket implementation.');
    }
  }

  connect(
    agentId: string,
    onMessage?: MessageHandler,
    onError?: ErrorHandler,
    onClose?: CloseHandler
  ): void {
    // Close existing connection if any
    this.disconnect(agentId);

    const url = `${this.baseUrl}/ws/agents/${agentId}`;
    const ws = new this.WebSocketImpl(url);

    const connection: Connection = {
      ws,
      handlers: { onMessage, onError, onClose },
      reconnectAttempts: 0,
    };

    this.connections.set(agentId, connection);

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as StreamEvent;
        connection.handlers.onMessage?.(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (event: Event) => {
      console.error(`WebSocket error for agent ${agentId}:`, event);
      connection.handlers.onError?.(event);
    };

    ws.onclose = (event: CloseEvent) => {
      console.log(`WebSocket closed for agent ${agentId}:`, event.code, event.reason);
      connection.handlers.onClose?.(event.code, event.reason);

      // Remove from connections map
      this.connections.delete(agentId);

      // Attempt reconnect if not a clean close
      if (event.code !== 1000 && event.code !== 1001) {
        this.attemptReconnect(agentId, connection.handlers);
      }
    };
  }

  disconnect(agentId: string): void {
    const connection = this.connections.get(agentId);
    if (connection) {
      try {
        connection.ws.close(1000, 'Client disconnect');
      } catch {
        // Ignore errors during close
      }
      this.connections.delete(agentId);
    }
  }

  disconnectAll(): void {
    for (const agentId of this.connections.keys()) {
      this.disconnect(agentId);
    }
  }

  isConnected(agentId: string): boolean {
    const connection = this.connections.get(agentId);
    return connection?.ws.readyState === WebSocket.OPEN;
  }

  send(agentId: string, data: unknown): boolean {
    const connection = this.connections.get(agentId);
    if (connection?.ws.readyState === WebSocket.OPEN) {
      connection.ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }

  sendPing(agentId: string): boolean {
    return this.send(agentId, { type: 'ping' });
  }

  private attemptReconnect(agentId: string, handlers: ConnectionHandlers): void {
    const currentAttempts = this.connections.get(agentId)?.reconnectAttempts ?? 0;

    if (currentAttempts >= this.maxReconnectAttempts) {
      console.log(`Max reconnect attempts reached for agent ${agentId}`);
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, currentAttempts);
    console.log(`Attempting reconnect for agent ${agentId} in ${delay}ms (attempt ${currentAttempts + 1})`);

    setTimeout(() => {
      // Track the reconnect attempt
      const newAttempts = currentAttempts + 1;

      // Reconnect with the same handlers
      this.connect(
        agentId,
        handlers.onMessage,
        handlers.onError,
        handlers.onClose
      );

      // Update reconnect attempts on the new connection
      const connection = this.connections.get(agentId);
      if (connection) {
        connection.reconnectAttempts = newAttempts;
      }
    }, delay);
  }

  // Global events connection
  private globalConnection: {
    ws: WebSocket;
    handler: GlobalMessageHandler;
    reconnectAttempts: number;
  } | null = null;

  /**
   * Connect to the global events WebSocket for real-time UI updates.
   *
   * CRITICAL: This is the primary mechanism for real-time UI updates.
   * DO NOT modify this method without understanding the full event flow:
   *
   * 1. WebSocket connects to /ws/events
   * 2. Backend sends events (agent_spawned, session_node_status_changed, etc.)
   * 3. onmessage handler parses JSON and calls the handler callback
   * 4. Handler (in UILogic.handleGlobalEvent) updates state via setState()
   * 5. setState() notifies all React subscribers via notifyListeners()
   * 6. React components re-render with new state
   *
   * If UI updates stop working, check:
   * - ws.onopen is defined (connection established)
   * - ws.onmessage is defined (messages received)
   * - handler callback is being invoked (events processed)
   * - setState is calling notifyListeners (subscribers notified)
   */
  connectGlobal(onMessage: GlobalMessageHandler): void {
    // Close existing connection if any
    this.disconnectGlobal();

    const url = `${this.baseUrl}/ws/events`;
    const ws = new this.WebSocketImpl(url);

    this.globalConnection = {
      ws,
      handler: onMessage,
      reconnectAttempts: 0,
    };

    // CRITICAL: onopen must be defined for the connection to work properly
    ws.onopen = () => {
      console.log('[WebSocket] Global events connected');
      // Reset reconnect attempts on successful connection
      if (this.globalConnection) {
        this.globalConnection.reconnectAttempts = 0;
      }
    };

    // CRITICAL: onmessage must be defined to receive events
    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as GlobalEvent;
        console.log('[WebSocket] Received global event:', data.type, data);
        // CRITICAL: handler must be invoked for UI to update
        if (this.globalConnection) {
          console.log('[WebSocket] Calling handler...');
          this.globalConnection.handler(data);
        } else {
          console.error('[WebSocket] ERROR: globalConnection is null, handler not called!');
        }
      } catch (e) {
        console.error('Failed to parse global WebSocket message:', e);
      }
    };

    ws.onerror = (event: Event) => {
      console.error('Global events WebSocket error:', event);
    };

    ws.onclose = (event: CloseEvent) => {
      console.log('[WebSocket] Global events disconnected:', event.code, event.reason);
      // Attempt reconnect if not a clean close
      if (event.code !== 1000 && event.code !== 1001 && this.globalConnection) {
        this.attemptGlobalReconnect();
      } else {
        this.globalConnection = null;
      }
    };
  }

  disconnectGlobal(): void {
    if (this.globalConnection) {
      try {
        this.globalConnection.ws.close(1000, 'Client disconnect');
      } catch {
        // Ignore errors during close
      }
      this.globalConnection = null;
    }
  }

  isGlobalConnected(): boolean {
    return this.globalConnection?.ws.readyState === WebSocket.OPEN;
  }

  sendGlobalPing(): boolean {
    if (this.globalConnection?.ws.readyState === WebSocket.OPEN) {
      this.globalConnection.ws.send(JSON.stringify({ type: 'ping' }));
      return true;
    }
    return false;
  }

  private attemptGlobalReconnect(): void {
    if (!this.globalConnection) return;

    const currentAttempts = this.globalConnection.reconnectAttempts;

    if (currentAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached for global events');
      this.globalConnection = null;
      return;
    }

    const handler = this.globalConnection.handler;
    const delay = this.reconnectDelay * Math.pow(2, currentAttempts);
    console.log(`Attempting global reconnect in ${delay}ms (attempt ${currentAttempts + 1})`);

    setTimeout(() => {
      // Track the reconnect attempt
      const newAttempts = currentAttempts + 1;

      // Reconnect
      this.connectGlobal(handler);

      // Update reconnect attempts on the new connection
      if (this.globalConnection) {
        this.globalConnection.reconnectAttempts = newAttempts;
      }
    }, delay);
  }
}
