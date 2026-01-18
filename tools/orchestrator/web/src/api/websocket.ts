import type { StreamEvent } from './types';

type MessageHandler = (event: StreamEvent) => void;
type ErrorHandler = (error: Event) => void;
type CloseHandler = (event: CloseEvent) => void;

const WS_BASE = import.meta.env.DEV
  ? `ws://${window.location.hostname}:8765`
  : (import.meta.env.VITE_WS_URL || `ws://${window.location.host}`);

export class WebSocketManager {
  private connections: Map<string, WebSocket> = new Map();
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private errorHandlers: Map<string, Set<ErrorHandler>> = new Map();
  private closeHandlers: Map<string, Set<CloseHandler>> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(
    agentId: string,
    onMessage?: MessageHandler,
    onError?: ErrorHandler,
    onClose?: CloseHandler
  ): WebSocket {
    // Close existing connection if any
    this.disconnect(agentId);

    const ws = new WebSocket(`${WS_BASE}/ws/agents/${agentId}`);

    // Store connection
    this.connections.set(agentId, ws);
    this.reconnectAttempts.set(agentId, 0);

    // Set up handlers
    if (onMessage) {
      this.addMessageHandler(agentId, onMessage);
    }
    if (onError) {
      this.addErrorHandler(agentId, onError);
    }
    if (onClose) {
      this.addCloseHandler(agentId, onClose);
    }

    // Wire up WebSocket events
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StreamEvent;
        this.notifyMessageHandlers(agentId, data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (event) => {
      console.error(`WebSocket error for agent ${agentId}:`, event);
      this.notifyErrorHandlers(agentId, event);
    };

    ws.onclose = (event) => {
      console.log(`WebSocket closed for agent ${agentId}:`, event.code, event.reason);
      this.notifyCloseHandlers(agentId, event);
      this.connections.delete(agentId);

      // Attempt reconnect if not a clean close
      if (event.code !== 1000 && event.code !== 1001) {
        this.attemptReconnect(agentId, onMessage, onError, onClose);
      }
    };

    return ws;
  }

  disconnect(agentId: string): void {
    const ws = this.connections.get(agentId);
    if (ws) {
      ws.close(1000, 'Client disconnect');
      this.connections.delete(agentId);
    }
    this.messageHandlers.delete(agentId);
    this.errorHandlers.delete(agentId);
    this.closeHandlers.delete(agentId);
    this.reconnectAttempts.delete(agentId);
  }

  disconnectAll(): void {
    for (const agentId of this.connections.keys()) {
      this.disconnect(agentId);
    }
  }

  isConnected(agentId: string): boolean {
    const ws = this.connections.get(agentId);
    return ws?.readyState === WebSocket.OPEN;
  }

  send(agentId: string, data: unknown): boolean {
    const ws = this.connections.get(agentId);
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }

  sendPing(agentId: string): boolean {
    return this.send(agentId, { type: 'ping' });
  }

  private addMessageHandler(agentId: string, handler: MessageHandler): void {
    if (!this.messageHandlers.has(agentId)) {
      this.messageHandlers.set(agentId, new Set());
    }
    this.messageHandlers.get(agentId)!.add(handler);
  }

  private addErrorHandler(agentId: string, handler: ErrorHandler): void {
    if (!this.errorHandlers.has(agentId)) {
      this.errorHandlers.set(agentId, new Set());
    }
    this.errorHandlers.get(agentId)!.add(handler);
  }

  private addCloseHandler(agentId: string, handler: CloseHandler): void {
    if (!this.closeHandlers.has(agentId)) {
      this.closeHandlers.set(agentId, new Set());
    }
    this.closeHandlers.get(agentId)!.add(handler);
  }

  private notifyMessageHandlers(agentId: string, event: StreamEvent): void {
    const handlers = this.messageHandlers.get(agentId);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(event);
        } catch (e) {
          console.error('Error in message handler:', e);
        }
      }
    }
  }

  private notifyErrorHandlers(agentId: string, event: Event): void {
    const handlers = this.errorHandlers.get(agentId);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(event);
        } catch (e) {
          console.error('Error in error handler:', e);
        }
      }
    }
  }

  private notifyCloseHandlers(agentId: string, event: CloseEvent): void {
    const handlers = this.closeHandlers.get(agentId);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(event);
        } catch (e) {
          console.error('Error in close handler:', e);
        }
      }
    }
  }

  private attemptReconnect(
    agentId: string,
    onMessage?: MessageHandler,
    onError?: ErrorHandler,
    onClose?: CloseHandler
  ): void {
    const attempts = this.reconnectAttempts.get(agentId) || 0;

    if (attempts >= this.maxReconnectAttempts) {
      console.log(`Max reconnect attempts reached for agent ${agentId}`);
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, attempts);
    console.log(`Attempting reconnect for agent ${agentId} in ${delay}ms (attempt ${attempts + 1})`);

    setTimeout(() => {
      this.reconnectAttempts.set(agentId, attempts + 1);
      this.connect(agentId, onMessage, onError, onClose);
    }, delay);
  }
}

// Singleton instance
export const wsManager = new WebSocketManager();

export default wsManager;
