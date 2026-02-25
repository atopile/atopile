import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactDOM from 'react-dom/client';
import { RequirementsDetailPage } from './components/RequirementsDetailPage';
import { RequirementsAllPage } from './components/RequirementsAllPage';
import { initializeTheme } from './hooks/useTheme';
import { preloadPlotly } from './components/requirements/charts';
import { fetchRequirements } from './components/requirements/api';
import type { RequirementData, RequirementsData } from './components/requirements/types';
import './styles/index.css';

// Start loading Plotly immediately — runs in parallel with React mount
preloadPlotly();

initializeTheme();

type WindowGlobals = Window & {
  __ATOPILE_REQUIREMENT_ID__?: string;
  __ATOPILE_REQUIREMENT_DATA__?: RequirementData | RequirementsData;
  __ATOPILE_BUILD_TIME__?: string;
  __ATOPILE_API_URL__?: string;
  __ATOPILE_WS_URL__?: string;
  __ATOPILE_PROJECT_ROOT__?: string;
  __ATOPILE_TARGET__?: string;
};

const w = window as WindowGlobals;

function getRequirementId(): string {
  const params = new URLSearchParams(window.location.search);
  const fromParam = params.get('requirementId');
  if (fromParam) return fromParam;
  return w.__ATOPILE_REQUIREMENT_ID__ ?? '';
}

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

const requirementId = getRequirementId();
const isAllMode = requirementId === '__ALL__';

function App() {
  const initialAllData = w.__ATOPILE_REQUIREMENT_DATA__ as RequirementsData | undefined;
  const initialBuildTime = w.__ATOPILE_BUILD_TIME__ ?? '';

  const [allData, setAllData] = useState<RequirementsData | null>(
    isAllMode ? (initialAllData ?? null) : null,
  );
  const [buildTime, setBuildTime] = useState(initialAllData?.buildTime ?? initialBuildTime);

  // For detail mode
  const [detailData, setDetailData] = useState<RequirementData | null>(
    !isAllMode ? (w.__ATOPILE_REQUIREMENT_DATA__ as RequirementData ?? null) : null,
  );

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const refresh = useCallback(async () => {
    try {
      const data = await fetchRequirements();
      if (!data) return;
      const typed = data as unknown as RequirementsData;
      if (isAllMode) {
        setAllData(typed);
        setBuildTime(typed.buildTime ?? '');
      } else {
        const match = typed.requirements.find((r: RequirementData) => r.id === requirementId);
        if (match) {
          setDetailData(match);
          setBuildTime(typed.buildTime ?? '');
        }
      }
    } catch (err) {
      console.warn('[RequirementsDetail] refresh failed:', err);
    }
  }, []);

  // Fetch latest data on mount (ensures fresh data when target changes)
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Listen for messages from the VS Code extension (e.g. target/data changes
  // triggered by sidebar refresh or build target switch)
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      if (msg?.type === 'requirementsUpdated') {
        // Update the target if it changed, then re-fetch
        if (msg.target) {
          (window as WindowGlobals).__ATOPILE_TARGET__ = msg.target;
        }
        if (msg.projectRoot) {
          (window as WindowGlobals).__ATOPILE_PROJECT_ROOT__ = msg.projectRoot;
        }
        refresh();
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
        // Subscribe to events
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

  if (isAllMode) {
    return (
      <RequirementsAllPage
        requirements={allData?.requirements ?? []}
        buildTime={buildTime}
        simStats={allData?.simStats}
      />
    );
  }

  return (
    <RequirementsDetailPage
      requirementId={requirementId}
      injectedData={detailData}
      injectedBuildTime={buildTime}
    />
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
