/**
 * UILogic - Main controller for the UI
 *
 * This is the core of the testable architecture:
 * - Pure TypeScript, no React dependencies
 * - Runs in browser (production) or Node.js/Bun (testing)
 * - Receives events, updates state, calls API
 * - Emits state changes via callbacks
 */

import { APIClient } from './api/client';
import { WebSocketClient } from './api/websocket';
import { createInitialState, type UIState, updateMap } from './state';
import type { UIEvent } from './events';
import { handleEvent } from './handlers';
import type { GlobalEvent, AgentState, PipelineSession } from './api/types';

export type StateListener = (state: UIState) => void;

export class UILogic {
  private state: UIState;
  readonly api: APIClient;
  readonly ws: WebSocketClient;
  private listeners: Set<StateListener> = new Set();

  constructor(
    apiBaseUrl: string,
    wsBaseUrl: string,
    wsImpl?: new (url: string) => WebSocket
  ) {
    this.state = createInitialState();
    this.api = new APIClient(apiBaseUrl);
    this.ws = new WebSocketClient(wsBaseUrl, wsImpl);
  }

  /**
   * Dispatch an event (this is what UI calls)
   */
  async dispatch(event: UIEvent): Promise<void> {
    await handleEvent(this, event);
  }

  /**
   * Subscribe to state changes
   * @returns Unsubscribe function
   */
  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    // Immediately notify with current state
    listener(this.state);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Get current state (for testing and initial render)
   */
  getState(): UIState {
    return this.state;
  }

  /**
   * Update state and notify listeners.
   * This is called by event handlers.
   *
   * CRITICAL: This method MUST call notifyListeners() after updating state.
   * Without this, React components will not re-render when state changes.
   */
  setState(updater: (state: UIState) => UIState): void {
    const prevState = this.state;
    const newState = updater(this.state);

    // Increment version to ensure React detects the change
    this.state = { ...newState, _version: prevState._version + 1 };

    // CRITICAL: Must notify listeners for React to re-render
    this.notifyListeners();
  }

  /**
   * Notify all listeners of state change.
   *
   * CRITICAL: This method is called after every state update.
   * Each listener is a React hook subscription that triggers forceUpdate().
   * DO NOT remove or skip this - UI updates depend on it.
   */
  private notifyListeners(): void {
    // Debug: uncomment to verify listeners are being notified
    // console.log(`[UILogic] Notifying ${this.listeners.size} listeners, state version: ${this.state._version}`);
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch (e) {
        console.error('Error in state listener:', e);
      }
    }
  }

  /**
   * Disconnect all WebSocket connections
   * Call this when unmounting/cleaning up
   */
  cleanup(): void {
    this.ws.disconnectAll();
    this.ws.disconnectGlobal();
    this.listeners.clear();
  }

  /**
   * Connect to the global events WebSocket for real-time state updates.
   * This replaces polling for agents, sessions, and pipelines.
   */
  connectGlobalEvents(): void {
    this.ws.connectGlobal((event: GlobalEvent) => {
      this.handleGlobalEvent(event);
    });
  }

  /**
   * Disconnect from global events WebSocket
   */
  disconnectGlobalEvents(): void {
    this.ws.disconnectGlobal();
  }

  /**
   * Check if connected to global events
   */
  isGlobalConnected(): boolean {
    return this.ws.isGlobalConnected();
  }

  /**
   * Handle incoming global events and update state accordingly.
   *
   * CRITICAL: This method processes WebSocket events and updates UI state.
   * Every setState() call here triggers notifyListeners() which updates React.
   * If UI updates stop working, add console.log to verify events are received.
   */
  private handleGlobalEvent(event: GlobalEvent): void {

    switch (event.type) {
      case 'connected':
        // Connected to global events stream
        console.log('[UILogic] Connected to global events stream');
        break;

      case 'agent_spawned':
        if (event.data?.agent) {
          const agent = event.data.agent as AgentState;
          this.setState((s) => ({
            ...s,
            agents: updateMap(s.agents, agent.id, agent),
          }));
        }
        break;

      case 'agent_status_changed':
        if (event.agent_id && event.data?.agent) {
          const agent = event.data.agent as AgentState;
          this.setState((s) => ({
            ...s,
            agents: updateMap(s.agents, agent.id, agent),
          }));
        }
        break;

      case 'agent_deleted':
        if (event.agent_id) {
          this.setState((s) => {
            const newAgents = new Map(s.agents);
            newAgents.delete(event.agent_id!);
            return { ...s, agents: newAgents };
          });
        }
        break;

      case 'agent_todos_changed':
        if (event.agent_id && event.data?.todos) {
          const todos = event.data.todos as AgentState['todos'];
          this.setState((s) => {
            const agent = s.agents.get(event.agent_id!);
            if (agent) {
              const updatedAgent = { ...agent, todos };
              return {
                ...s,
                agents: updateMap(s.agents, event.agent_id!, updatedAgent),
              };
            }
            return s;
          });
        }
        break;

      case 'session_status_changed':
        if (event.pipeline_id && event.data?.session) {
          const session = event.data.session as PipelineSession;
          this.setState((s) => {
            const sessions = s.pipelineSessions.get(event.pipeline_id!) || [];
            const updatedSessions = sessions.map((sess) =>
              sess.id === session.id ? session : sess
            );
            // If session not found, add it
            if (!sessions.find((sess) => sess.id === session.id)) {
              updatedSessions.unshift(session);
            }
            const newPipelineSessions = new Map(s.pipelineSessions);
            newPipelineSessions.set(event.pipeline_id!, updatedSessions);
            return { ...s, pipelineSessions: newPipelineSessions };
          });
        }
        break;

      case 'session_node_status_changed':
        if (event.pipeline_id && event.session_id && event.data?.session) {
          const session = event.data.session as PipelineSession;
          console.log('[UILogic] Session node status changed:', event.node_id, session.node_status);
          this.setState((s) => {
            const sessions = s.pipelineSessions.get(event.pipeline_id!) || [];
            const existingSession = sessions.find((sess) => sess.id === session.id);
            let updatedSessions: PipelineSession[];
            if (existingSession) {
              // Update existing session
              updatedSessions = sessions.map((sess) =>
                sess.id === session.id ? session : sess
              );
            } else {
              // Session not found - add it (handles case when session_created wasn't received)
              console.log('[UILogic] Adding new session from node status event:', session.id);
              updatedSessions = [session, ...sessions];
            }
            const newPipelineSessions = new Map(s.pipelineSessions);
            newPipelineSessions.set(event.pipeline_id!, updatedSessions);
            return { ...s, pipelineSessions: newPipelineSessions };
          });
        }
        break;

      case 'session_created':
        if (event.pipeline_id && event.data?.session) {
          const session = event.data.session as PipelineSession;
          this.setState((s) => {
            const sessions = s.pipelineSessions.get(event.pipeline_id!) || [];
            // Add to the beginning of the list
            const updatedSessions = [session, ...sessions];
            const newPipelineSessions = new Map(s.pipelineSessions);
            newPipelineSessions.set(event.pipeline_id!, updatedSessions);
            return {
              ...s,
              pipelineSessions: newPipelineSessions,
              // Auto-select the new session
              selectedSessionId: session.id,
            };
          });
        }
        break;

      case 'session_deleted':
        if (event.pipeline_id && event.session_id) {
          this.setState((s) => {
            const sessions = s.pipelineSessions.get(event.pipeline_id!) || [];
            const updatedSessions = sessions.filter((sess) => sess.id !== event.session_id);
            const newPipelineSessions = new Map(s.pipelineSessions);
            newPipelineSessions.set(event.pipeline_id!, updatedSessions);
            return {
              ...s,
              pipelineSessions: newPipelineSessions,
              selectedSessionId:
                s.selectedSessionId === event.session_id ? null : s.selectedSessionId,
            };
          });
        }
        break;

      case 'ping':
        // Respond with pong
        this.ws.sendGlobalPing();
        break;

      case 'pong':
        // Ignore pong responses
        break;
    }
  }
}

// Re-export everything for convenient imports
export * from './api/types';
export * from './api/client';
export * from './api/websocket';
export * from './state';
export * from './events';
export * from './viewmodels';
