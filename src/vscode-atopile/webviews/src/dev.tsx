/**
 * Dev mode entry point.
 * Renders both Sidebar and LogViewer for browser-based development.
 * 
 * Polyfills acquireVsCodeApi to connect to the dev server via WebSocket.
 * IMPORTANT: Polyfill must be installed BEFORE importing components.
 */

const DEV_SERVER_URL = 'ws://localhost:3001';

// Global error handler for uncaught errors
window.onerror = (message, source, lineno, colno, error) => {
  console.error('[Dev] Global error:', { message, source, lineno, colno, error });
  return false;
};

// Global handler for unhandled promise rejections
window.onunhandledrejection = (event) => {
  console.error('[Dev] Unhandled promise rejection:', event.reason);
};

// Shared WebSocket connection for all components
let sharedWs: WebSocket | null = null;
let wsReady = false;
const pendingMessages: unknown[] = [];

// Cache the last received state to replay for late-mounting components
let lastReceivedState: unknown = null;

function connectWebSocket() {
  sharedWs = new WebSocket(DEV_SERVER_URL);
  
  sharedWs.onopen = () => {
    console.log('[Dev] Connected to dev server');
    wsReady = true;
    // Send any pending messages
    pendingMessages.forEach(msg => {
      sharedWs?.send(JSON.stringify(msg));
    });
    pendingMessages.length = 0;
  };
  
  sharedWs.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      // Log state messages for debugging
      if (msg.type === 'state') {
        console.log('[Dev] Received state:', {
          projects: msg.data?.projects?.length,
          packages: msg.data?.packages?.length,
          builds: msg.data?.builds?.length,
          problems: msg.data?.problems?.length,
          isConnected: msg.data?.isConnected,
          selectedProjectRoot: msg.data?.selectedProjectRoot,
          keys: Object.keys(msg.data || {}).slice(0, 20),
        });
        // Cache state for late-mounting components
        lastReceivedState = msg;
      }
      // Dispatch as a window message event (same as VS Code does)
      window.dispatchEvent(new MessageEvent('message', { data: msg }));
    } catch (e) {
      console.error('[Dev] Failed to parse message:', e);
    }
  };
  
  sharedWs.onclose = () => {
    console.log('[Dev] Disconnected, reconnecting...');
    wsReady = false;
    setTimeout(connectWebSocket, 2000);
  };
  
  sharedWs.onerror = (e) => {
    console.error('[Dev] WebSocket error:', e);
  };
}

// Start connection immediately
connectWebSocket();

// Install the polyfill globally BEFORE any imports
// All components share the same WebSocket connection
(window as any).acquireVsCodeApi = () => ({
  postMessage: (message: unknown) => {
    // When a component signals 'ready', replay the cached state if available
    // This handles the race condition where state arrives before components mount
    if (typeof message === 'object' && message !== null && (message as any).type === 'ready') {
      if (lastReceivedState) {
        console.log('[Dev] Component ready, replaying cached state');
        // Use setTimeout to ensure the event listener is registered
        setTimeout(() => {
          window.dispatchEvent(new MessageEvent('message', { data: lastReceivedState }));
        }, 0);
      }
    }

    if (wsReady && sharedWs?.readyState === WebSocket.OPEN) {
      sharedWs.send(JSON.stringify(message));
    } else {
      console.log('[Dev] Queuing message until connected:', message);
      pendingMessages.push(message);
    }
  },
  getState: () => undefined,
  setState: () => {},
});

// NOW import CSS (after polyfill is installed)

Promise.all([
  import('react'),
  import('react-dom/client'),
  import('./components/Sidebar'),
  import('./components/LogViewer'),
]).then(([React, ReactDOM, SidebarModule, LogViewerModule]) => {
  const { Sidebar } = SidebarModule;
  const { LogViewer } = LogViewerModule;

  // Error Boundary component to catch and display React errors
  class ErrorBoundary extends React.Component<
    { children: React.ReactNode; name: string },
    { hasError: boolean; error: Error | null }
  > {
    constructor(props: { children: React.ReactNode; name: string }) {
      super(props);
      this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error) {
      return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
      console.error(`[${this.props.name}] React error:`, error, errorInfo);
    }

    render() {
      if (this.state.hasError) {
        return React.createElement('div', {
          style: {
            padding: '20px',
            background: '#1a1a1a',
            color: '#ff6b6b',
            fontFamily: 'monospace',
            fontSize: '12px',
            whiteSpace: 'pre-wrap',
          }
        },
          React.createElement('h3', { style: { color: '#ff6b6b', marginTop: 0 } },
            `Error in ${this.props.name}`
          ),
          React.createElement('p', { style: { color: '#888' } },
            this.state.error?.message || 'Unknown error'
          ),
          React.createElement('pre', { style: { color: '#666', fontSize: '10px' } },
            this.state.error?.stack || ''
          ),
          React.createElement('button', {
            onClick: () => this.setState({ hasError: false, error: null }),
            style: {
              marginTop: '10px',
              padding: '8px 16px',
              background: '#333',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }
          }, 'Retry')
        );
      }
      return this.props.children;
    }
  }

  // Render Sidebar with error boundary
  const sidebarRoot = document.getElementById('sidebar-root');
  if (sidebarRoot) {
    ReactDOM.createRoot(sidebarRoot).render(
      React.createElement(React.StrictMode, null,
        React.createElement(ErrorBoundary, { name: 'Sidebar', children: React.createElement(Sidebar) })
      )
    );
  }

  // Render LogViewer with error boundary
  const logRoot = document.getElementById('log-root');
  if (logRoot) {
    ReactDOM.createRoot(logRoot).render(
      React.createElement(React.StrictMode, null,
        React.createElement(ErrorBoundary, { name: 'LogViewer', children: React.createElement(LogViewer) })
      )
    );
  }
});
