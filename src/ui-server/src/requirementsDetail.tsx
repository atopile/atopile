import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactDOM from 'react-dom/client';
import { RequirementsAllPage } from './components/RequirementsAllPage';
import { initializeTheme } from './hooks/useTheme';
import { preloadPlotly } from './components/requirements/charts';
import { fetchRequirements } from './components/requirements/api';
import type { RequirementsData } from './components/requirements/types';
import './styles/index.css';

// Start loading Plotly immediately — runs in parallel with React mount
preloadPlotly();

initializeTheme();

type WindowGlobals = Window & {
  __ATOPILE_REQUIREMENT_ID__?: string;
  __ATOPILE_REQUIREMENT_DATA__?: RequirementsData;
  __ATOPILE_BUILD_TIME__?: string;
  __ATOPILE_API_URL__?: string;
  __ATOPILE_WS_URL__?: string;
  __ATOPILE_PROJECT_ROOT__?: string;
  __ATOPILE_TARGET__?: string;
  __ATOPILE_INITIAL_SEARCH__?: string;
};

const w = window as WindowGlobals;

/** Derive a WebSocket URL from the injected globals. */
function getWsStateUrl(): string | null {
  const wsUrl = w.__ATOPILE_WS_URL__;
  if (wsUrl) {
    try {
      const origin = new URL(wsUrl).origin.replace(/^http/, 'ws');
      return `${origin}/ws/state`;
    } catch { /* fall through */ }
  }
  const apiUrl = w.__ATOPILE_API_URL__;
  if (apiUrl) {
    try {
      const url = new URL(apiUrl);
      const proto = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${proto}//${url.host}/ws/state`;
    } catch { /* fall through */ }
  }
  return null;
}

function App() {
  const initialAllData = w.__ATOPILE_REQUIREMENT_DATA__ as RequirementsData | undefined;
  const initialBuildTime = w.__ATOPILE_BUILD_TIME__ ?? '';
  const initialSearch = w.__ATOPILE_INITIAL_SEARCH__ ?? '';
  const buildTarget = w.__ATOPILE_TARGET__ ?? '';

  const [allData, setAllData] = useState<RequirementsData | null>(initialAllData ?? null);
  const [buildTime, setBuildTime] = useState(initialAllData?.buildTime ?? initialBuildTime);
  const [search, setSearch] = useState(initialSearch);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const refresh = useCallback(async () => {
    try {
      const data = await fetchRequirements();
      if (!data) return;
      const typed = data as unknown as RequirementsData;
      setAllData(typed);
      setBuildTime(typed.buildTime ?? '');
    } catch (err) {
      console.warn('[RequirementsDetail] refresh failed:', err);
    }
  }, []);

  // Fetch latest data on mount (ensures fresh data when target changes)
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Listen for messages from the VS Code extension (e.g. target/data changes
  // triggered by sidebar refresh or build target switch, or search updates)
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      if (msg?.type === 'requirementsUpdated') {
        if (msg.target) {
          (window as WindowGlobals).__ATOPILE_TARGET__ = msg.target;
        }
        if (msg.projectRoot) {
          (window as WindowGlobals).__ATOPILE_PROJECT_ROOT__ = msg.projectRoot;
        }
        refresh();
      } else if (msg?.type === 'setSearch') {
        setSearch(msg.search ?? '');
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [refresh]);

  // WebSocket connection for auto-refresh
  useEffect(() => {
    const wsUrl = getWsStateUrl();
    if (!wsUrl) return;

    let disposed = false;

    function connect() {
      if (disposed) return;
      const ws = new WebSocket(wsUrl!);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'subscribe' }));
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'event' && msg.event === 'requirements_changed') {
            refresh();
          }
        } catch { /* ignore non-JSON */ }
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (!disposed) {
          reconnectTimer.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      disposed = true;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [refresh]);

  return (
    <RequirementsAllPage
      requirements={allData?.requirements ?? []}
      buildTime={buildTime}
      simStats={allData?.simStats}
      initialSearch={search}
      buildTarget={buildTarget}
    />
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
