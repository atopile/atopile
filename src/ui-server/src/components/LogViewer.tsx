/**
 * Minimal Log Viewer - WebSocket wrapper with parameter inputs
 * Supports both build logs and test logs modes
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import AnsiToHtml from 'ansi-to-html';
import './LogViewer.css';

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'] as const;
const AUDIENCES = ['user', 'developer', 'agent'] as const;

type LogLevel = typeof LOG_LEVELS[number];
type Audience = typeof AUDIENCES[number];
type LogMode = 'build' | 'test';

interface BuildLogEntry {
  timestamp: string;
  level: LogLevel;
  audience: Audience;
  logger_name: string;
  message: string;
  ato_traceback?: string | null;
  python_traceback?: string | null;
  objects?: unknown;
}

interface TestLogEntry extends BuildLogEntry {
  test_name?: string | null;
}

type LogEntry = BuildLogEntry | TestLogEntry;

interface BuildLogResult {
  type: 'logs_result';
  logs: BuildLogEntry[];
}

interface TestLogResult {
  type: 'test_logs_result';
  logs: TestLogEntry[];
}

interface LogError {
  type: 'logs_error';
  error: string;
}

type LogResult = BuildLogResult | TestLogResult;

type ConnectionState = 'disconnected' | 'connecting' | 'connected';

const ansiConverter = new AnsiToHtml({
  fg: '#e5e5e5',
  bg: 'transparent',
  newline: true,
  escapeXML: true,
});

// Highlight search matches in text
function highlightText(text: string, search: string): string {
  if (!search.trim()) return text;
  const escaped = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  return text.replace(regex, '<mark class="lv-highlight">$1</mark>');
}

// Get initial values from URL query params
function getInitialParams(): { mode: LogMode; testRunId: string; buildId: string; testName: string } {
  const params = new URLSearchParams(window.location.search);
  const testRunId = params.get('test_run_id') || '';
  const buildId = params.get('build_id') || '';
  const testName = params.get('test_name') || '';
  // Auto-detect mode based on which ID is provided
  const mode: LogMode = testRunId ? 'test' : (buildId ? 'build' : 'test');
  return { mode, testRunId, buildId, testName };
}

export function LogViewer() {
  // Get initial values from URL params
  const initialParams = getInitialParams();

  // Mode toggle: build logs vs test logs
  const [mode, setMode] = useState<LogMode>(initialParams.mode);

  // Query parameters - shared
  const [logLevels, setLogLevels] = useState<LogLevel[]>(['INFO', 'WARNING', 'ERROR', 'ALERT']);
  const [audience, setAudience] = useState<Audience>('developer');
  const [count, setCount] = useState(100);
  const [search, setSearch] = useState('');

  // Build log specific parameters
  const [buildId, setBuildId] = useState(initialParams.buildId);
  const [stage, setStage] = useState('');

  // Test log specific parameters
  const [testRunId, setTestRunId] = useState(initialParams.testRunId);
  const [testName, setTestName] = useState(initialParams.testName);

  // Connection state
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);

  // Filter logs by search
  const filteredLogs = search.trim()
    ? logs.filter(log => log.message.toLowerCase().includes(search.toLowerCase()))
    : logs;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const reconnectAttempts = useRef(0);

  const toggleLevel = (level: LogLevel) => {
    setLogLevels(prev =>
      prev.includes(level)
        ? prev.filter(l => l !== level)
        : [...prev, level]
    );
  };

  const connect = useCallback(() => {
    // Don't connect if unmounted or already connected/connecting
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setConnectionState('connecting');

    // Connect to /ws/logs on the same host that served this page
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/logs`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      reconnectAttempts.current = 0;
      setConnectionState('connected');
      setError(null);
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;

      wsRef.current = null;
      setConnectionState('disconnected');

      // Exponential backoff: 1s, 2s, 4s, 8s, max 10s
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
      reconnectAttempts.current++;

      reconnectTimeoutRef.current = window.setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, delay);
    };

    ws.onerror = () => {
      // Error will be followed by close, so just set the error message
      if (mountedRef.current) {
        setError('Connection failed - retrying...');
      }
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      setLoading(false);
      try {
        const data = JSON.parse(event.data) as LogResult | LogError;
        if (data.type === 'logs_result') {
          setLogs(data.logs);
          setError(null);
        } else if (data.type === 'test_logs_result') {
          setLogs(data.logs);
          setError(null);
        } else if (data.type === 'logs_error') {
          setError(data.error);
        }
      } catch (e) {
        setError(`Failed to parse response: ${e}`);
      }
    };
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const fetchLogs = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    if (mode === 'build' && !buildId.trim()) {
      setError('Build ID is required');
      return;
    }

    if (mode === 'test' && !testRunId.trim()) {
      setError('Test Run ID is required');
      return;
    }

    setLoading(true);
    setError(null);

    const payload = mode === 'build'
      ? {
          build_id: buildId.trim(),
          stage: stage.trim() || null,
          log_levels: logLevels.length > 0 ? logLevels : null,
          audience: audience,
          count: count,
        }
      : {
          test_run_id: testRunId.trim(),
          test_name: testName.trim() || null,
          log_levels: logLevels.length > 0 ? logLevels : null,
          audience: audience,
          count: count,
        };

    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (e) {
      setLoading(false);
      setError(`Failed to send: ${e}`);
    }
  }, [mode, buildId, stage, testRunId, testName, logLevels, audience, count]);

  return (
    <div className="log-viewer-minimal">
      {/* Query Parameters - Compact */}
      <div className="lv-controls">
        <span className={`lv-status-dot ${connectionState}`} title={connectionState} />

        {/* Mode Toggle */}
        <div className="lv-mode-toggle">
          <button
            className={`lv-mode-btn ${mode === 'build' ? 'active' : ''}`}
            onClick={() => setMode('build')}
          >
            Build
          </button>
          <button
            className={`lv-mode-btn ${mode === 'test' ? 'active' : ''}`}
            onClick={() => setMode('test')}
          >
            Test
          </button>
        </div>

        {/* Mode-specific inputs */}
        {mode === 'build' ? (
          <>
            <input
              type="text"
              value={buildId}
              onChange={(e) => setBuildId(e.target.value)}
              placeholder="Build ID"
              className="lv-input"
            />
            <input
              type="text"
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              placeholder="Stage"
              className="lv-input lv-input-medium"
            />
          </>
        ) : (
          <>
            <input
              type="text"
              value={testRunId}
              onChange={(e) => setTestRunId(e.target.value)}
              placeholder="Test Run ID"
              className="lv-input"
            />
            <input
              type="text"
              value={testName}
              onChange={(e) => setTestName(e.target.value)}
              placeholder="Test Name"
              className="lv-input lv-input-medium"
            />
          </>
        )}

        <div className="lv-checkboxes">
          {LOG_LEVELS.map(level => (
            <label key={level} className={`lv-checkbox ${level.toLowerCase()}`}>
              <input
                type="checkbox"
                checked={logLevels.includes(level)}
                onChange={() => toggleLevel(level)}
              />
              {level.slice(0, 4)}
            </label>
          ))}
        </div>
        <select
          value={audience}
          onChange={(e) => setAudience(e.target.value as Audience)}
          className="lv-select"
        >
          {AUDIENCES.map(aud => (
            <option key={aud} value={aud}>{aud}</option>
          ))}
        </select>
        <input
          type="number"
          value={count}
          onChange={(e) => setCount(parseInt(e.target.value) || 100)}
          min={1}
          max={10000}
          className="lv-input lv-input-xs"
        />
        <button
          className="lv-btn lv-btn-primary"
          onClick={fetchLogs}
          disabled={connectionState !== 'connected' || loading}
        >
          {loading ? '...' : 'Fetch'}
        </button>
        <span className="lv-separator" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter..."
          className="lv-input lv-input-search"
        />
      </div>

      {/* Error Display */}
      {error && (
        <div className="lv-error">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="lv-results">
        <div className="lv-results-header">
          {search ? `${filteredLogs.length}/${logs.length}` : logs.length}
        </div>
        <div className="lv-logs">
          {filteredLogs.length === 0 ? (
            <div className="lv-empty">{logs.length === 0 ? 'No logs' : 'No matches'}</div>
          ) : (
            filteredLogs.map((entry, idx) => {
              // Format timestamp to HH:MM:SS
              const ts = entry.timestamp.split('T')[1]?.split('.')[0] || entry.timestamp;
              // Convert ANSI then highlight search matches
              const html = highlightText(ansiConverter.toHtml(entry.message), search);
              // Get test name if in test mode
              const testEntry = entry as TestLogEntry;
              const testLabel = mode === 'test' && testEntry.test_name ? testEntry.test_name : null;
              return (
                <div key={idx} className="lv-entry">
                  <span className="lv-ts">{ts}</span>
                  <span className={`lv-level-badge ${entry.level.toLowerCase()}`}>
                    {entry.level.slice(0, 4)}
                  </span>
                  {testLabel && (
                    <span className="lv-test-badge">
                      {testLabel}
                    </span>
                  )}
                  <pre
                    className="lv-message"
                    dangerouslySetInnerHTML={{ __html: html }}
                  />
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
