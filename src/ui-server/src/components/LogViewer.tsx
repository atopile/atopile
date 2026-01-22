/**
 * Log Viewer - WebSocket wrapper with parameter inputs
 * Supports both build logs and test logs modes
 * Supports one-shot fetch and real-time streaming
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import AnsiToHtml from 'ansi-to-html';
import { useStore } from '../store';
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
  stage?: string | null;
  ato_traceback?: string | null;
  python_traceback?: string | null;
  objects?: unknown;
}

interface TestLogEntry extends BuildLogEntry {
  test_name?: string | null;
}

// Streaming entries include id for cursor tracking
interface StreamLogEntry extends BuildLogEntry {
  id: number;
}

interface TestStreamLogEntry extends TestLogEntry {
  id: number;
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

// Streaming results include last_id cursor
interface StreamResult {
  type: 'logs_stream';
  logs: StreamLogEntry[];
  last_id: number;
}

interface TestStreamResult {
  type: 'test_logs_stream';
  logs: TestStreamLogEntry[];
  last_id: number;
}

interface LogError {
  type: 'logs_error';
  error: string;
}

type LogResult = BuildLogResult | TestLogResult | StreamResult | TestStreamResult;

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
  const mode: LogMode = testRunId ? 'test' : 'build';
  return { mode, testRunId, buildId, testName };
}

// Chevron icon component
function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// Animated traceback details component
function TraceDetails({
  label,
  content,
  className
}: {
  label: string;
  content: string;
  className: string;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className={`lv-trace ${className}`}>
      <button className="lv-trace-summary" onClick={() => setIsOpen(!isOpen)}>
        <span className={`lv-trace-arrow ${isOpen ? 'open' : ''}`}>▸</span>
        {label}
      </button>
      {isOpen && (
        <pre
          className="lv-trace-content"
          dangerouslySetInnerHTML={{ __html: ansiConverter.toHtml(content) }}
        />
      )}
    </div>
  );
}

export function LogViewer() {
  // Get initial values from URL params
  const initialParams = getInitialParams();

  // Mode toggle: build logs vs test logs
  const [mode, setMode] = useState<LogMode>(initialParams.mode);

  // Query parameters - shared
  const [logLevels, setLogLevels] = useState<LogLevel[]>(['INFO', 'WARNING', 'ERROR', 'ALERT']);
  const [audience, setAudience] = useState<Audience>('developer');
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
  const queuedBuilds = useStore((state) => state.queuedBuilds);
  const builds = useStore((state) => state.builds);

  // Streaming state
  const [streaming, setStreaming] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const autoScrollRef = useRef(true); // Ref version for callbacks
  const lastIdRef = useRef(0);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const autoStartedRef = useRef(false);
  const lastAutoBuildIdRef = useRef<string | null>(null);

  // Level dropdown state
  const [levelDropdownOpen, setLevelDropdownOpen] = useState(false);
  const levelDropdownRef = useRef<HTMLDivElement>(null);

  // Status tooltip state
  const [showStatusTooltip, setShowStatusTooltip] = useState(false);

  // Keep ref in sync with state
  useEffect(() => {
    autoScrollRef.current = autoScroll;
  }, [autoScroll]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (levelDropdownRef.current && !levelDropdownRef.current.contains(event.target as Node)) {
        setLevelDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter logs by search
  const filteredLogs = search.trim()
    ? logs.filter(log => log.message.toLowerCase().includes(search.toLowerCase()))
    : logs;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const reconnectAttempts = useRef(0);
  const [wsUrl, setWsUrl] = useState<string | null>(null);

  const toggleLevel = (level: LogLevel) => {
    setLogLevels(prev =>
      prev.includes(level)
        ? prev.filter(l => l !== level)
        : [...prev, level]
    );
  };

  // Detect if user has scrolled up (auto-disable auto-scroll)
  const handleScroll = useCallback(() => {
    if (!logsContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    // Only auto-disable when scrolling up, don't auto-enable
    if (!isAtBottom && autoScrollRef.current) {
      autoScrollRef.current = false;
      setAutoScroll(false);
    }
  }, []); // No dependencies - uses ref

  // Auto-scroll when logs change
  useEffect(() => {
    if (autoScrollRef.current && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

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

    // Connect to /ws/logs - uses Vite proxy in dev, same host in production
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${wsProtocol}//${window.location.host}/ws/logs`;
    setWsUrl(url);
    const ws = new WebSocket(url);
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
      setStreaming(false); // Stop streaming on disconnect

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
      try {
        const data = JSON.parse(event.data) as LogResult | LogError;

        if (data.type === 'logs_result' || data.type === 'test_logs_result') {
          // One-shot response - replace logs
          setLogs(data.logs);
          setError(null);
        } else if (data.type === 'logs_stream' || data.type === 'test_logs_stream') {
          // Streaming response - append logs
          if (data.logs.length > 0) {
            setLogs(prev => [...prev, ...data.logs]);
            lastIdRef.current = data.last_id;
          }
          setError(null);
        } else if (data.type === 'logs_error') {
          setError(data.error);
          setStreaming(false);
        }
      } catch (e) {
        setError(`Failed to parse response: ${e}`);
      }
    };
  }, []); // No dependencies that change during streaming

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

  const toggleStreaming = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    if (streaming) {
      // Stop streaming
      setStreaming(false);
      wsRef.current.send(JSON.stringify({ unsubscribe: true }));
      return;
    }

    // Start streaming
    const id = mode === 'build' ? buildId.trim() : testRunId.trim();
    if (!id) {
      setError(mode === 'build' ? 'Build ID is required' : 'Test Run ID is required');
      return;
    }

    // Clear existing logs and reset cursor
    setLogs([]);
    lastIdRef.current = 0;
    autoScrollRef.current = true;
    setAutoScroll(true);
    setStreaming(true);
    setError(null);

    const payload = mode === 'build'
      ? {
          build_id: buildId.trim(),
          stage: stage.trim() || null,
          log_levels: logLevels.length > 0 ? logLevels : null,
          audience: audience,
          after_id: 0,
          count: 1000,
          subscribe: true,
        }
      : {
          test_run_id: testRunId.trim(),
          test_name: testName.trim() || null,
          log_levels: logLevels.length > 0 ? logLevels : null,
          audience: audience,
          after_id: 0,
          count: 1000,
          subscribe: true,
        };

    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (e) {
      setStreaming(false);
      setError(`Failed to start streaming: ${e}`);
    }
  }, [streaming, mode, buildId, testRunId, stage, testName, logLevels, audience]);

  // Auto-start streaming when connected with a valid ID from URL params
  useEffect(() => {
    if (autoStartedRef.current) return;
    if (connectionState !== 'connected') return;
    if (streaming) return;

    const id = mode === 'build' ? buildId.trim() : testRunId.trim();
    if (!id) return;

    // Auto-start streaming
    autoStartedRef.current = true;
    toggleStreaming();
  }, [connectionState, mode, buildId, testRunId, streaming, toggleStreaming]);
  // Auto-start streaming when a new build_id is provided
  useEffect(() => {
    const trimmedBuildId = buildId.trim();
    if (mode !== 'build') return;
    if (!trimmedBuildId) return;
    if (connectionState !== 'connected') return;
    if (streaming) return;
    if (lastAutoBuildIdRef.current === trimmedBuildId) return;

    autoStartedRef.current = true;
    lastAutoBuildIdRef.current = trimmedBuildId;
    toggleStreaming();
  }, [buildId, mode, connectionState, streaming, toggleStreaming]);

  // Populate build_id from the latest active build when available
  useEffect(() => {
    if (mode !== 'build') return;

    const candidates = [...queuedBuilds, ...builds].filter((build) => build.buildId);
    if (candidates.length === 0) return;

    let latest = candidates[0];
    for (const candidate of candidates) {
      const candidateTs = candidate.startedAt ?? 0;
      const latestTs = latest.startedAt ?? 0;
      if (candidateTs > latestTs) {
        latest = candidate;
      }
    }

    const latestBuildId = latest.buildId ?? '';
    if (!latestBuildId || latestBuildId === buildId.trim()) return;

    if (streaming && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ unsubscribe: true }));
      setStreaming(false);
    }

    autoStartedRef.current = false;
    lastAutoBuildIdRef.current = latestBuildId;
    setBuildId(latestBuildId);
  }, [queuedBuilds, builds, mode, buildId, streaming]);

  // Get display label for level dropdown
  const getLevelLabel = () => {
    return `Log Levels (${logLevels.length})`;
  };

  return (
    <div className="lv-container">
      {/* Fixed Toolbar */}
      <div className="lv-toolbar">
        <div className="lv-controls">
          {/* Left section: Status + Mode + ID */}
          <div className="lv-controls-left">
            {/* Status indicator */}
            <div
              className={`lv-status ${connectionState}`}
              onMouseEnter={() => setShowStatusTooltip(true)}
              onMouseLeave={() => setShowStatusTooltip(false)}
            >
              <span className="lv-status-dot" />
              <span className="lv-status-count">
                {search ? `${filteredLogs.length}/${logs.length}` : logs.length}
              </span>
              {streaming && <span className="lv-live-badge">LIVE</span>}
              {showStatusTooltip && wsUrl && (
                <div className="lv-status-tooltip">
                  <div className="lv-status-tooltip-row">
                    <span className="lv-status-tooltip-label">Status:</span>
                    <span className="lv-status-tooltip-value">{connectionState}</span>
                  </div>
                  <div className="lv-status-tooltip-row">
                    <span className="lv-status-tooltip-label">URL:</span>
                    <span className="lv-status-tooltip-value">{wsUrl}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Mode Toggle */}
            <div className="lv-mode-toggle">
              <button
                className={`lv-mode-btn ${mode === 'build' ? 'active' : ''}`}
                onClick={() => setMode('build')}
                disabled={streaming}
              >
                Build
              </button>
              <button
                className={`lv-mode-btn ${mode === 'test' ? 'active' : ''}`}
                onClick={() => setMode('test')}
                disabled={streaming}
              >
                Test
              </button>
            </div>

            {/* Mode-specific ID input */}
            {mode === 'build' ? (
              <input
                type="text"
                value={buildId}
                onChange={(e) => setBuildId(e.target.value)}
                placeholder="Build ID"
                className="lv-input"
                disabled={streaming}
              />
            ) : (
              <input
                type="text"
                value={testRunId}
                onChange={(e) => setTestRunId(e.target.value)}
                placeholder="Test Run ID"
                className="lv-input"
                disabled={streaming}
              />
            )}

            <button
              className={`lv-btn ${streaming ? 'lv-btn-danger' : 'lv-btn-success'}`}
              onClick={toggleStreaming}
              disabled={connectionState !== 'connected'}
            >
              {streaming ? 'Stop' : 'Stream'}
            </button>
          </div>

          {/* Right section: Filters */}
          <div className="lv-controls-right">
            {/* Stage/Test name filter + Search grouped together */}
            {mode === 'build' ? (
              <input
                type="text"
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                placeholder="Stage"
                className="lv-input lv-input-search"
                disabled={streaming}
              />
            ) : (
              <input
                type="text"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                placeholder="Test Name"
                className="lv-input lv-input-search"
                disabled={streaming}
              />
            )}

            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              className="lv-input lv-input-search"
            />

            <span className="lv-separator" />

            {/* Level dropdown */}
            <div className="lv-dropdown" ref={levelDropdownRef}>
              <button
                className={`selector-trigger ${levelDropdownOpen ? 'open' : ''}`}
                onClick={() => setLevelDropdownOpen(!levelDropdownOpen)}
                disabled={streaming}
              >
                <span className="selector-label">{getLevelLabel()}</span>
                <ChevronDown className={`selector-chevron ${levelDropdownOpen ? 'rotated' : ''}`} />
              </button>
              {levelDropdownOpen && (
                <div className="selector-dropdown">
                  {LOG_LEVELS.map(level => (
                    <label key={level} className="dropdown-item">
                      <input
                        type="checkbox"
                        checked={logLevels.includes(level)}
                        onChange={() => toggleLevel(level)}
                      />
                      <span className={`lv-level-badge ${level.toLowerCase()}`}>{level}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <select
              value={audience}
              onChange={(e) => setAudience(e.target.value as Audience)}
              className="lv-select"
              disabled={streaming}
            >
              {AUDIENCES.map(aud => (
                <option key={aud} value={aud}>{aud}</option>
              ))}
            </select>

            <span className="lv-separator" />

            <button
              className={`lv-btn lv-btn-small ${autoScroll ? 'lv-btn-active' : ''}`}
              onClick={() => {
                const newValue = !autoScroll;
                autoScrollRef.current = newValue;
                setAutoScroll(newValue);
                if (newValue && logsContainerRef.current) {
                  logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
                }
              }}
              title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
            >
              {autoScroll ? '⬇ On' : '⬇ Off'}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="lv-error">
            {error}
          </div>
        )}
      </div>

      {/* Scrollable Log Content */}
      <div
        className="lv-content"
        ref={logsContainerRef}
        onScroll={handleScroll}
      >
        {filteredLogs.length === 0 ? (
          <div className="lv-empty">
            {logs.length === 0 ? (streaming ? 'Waiting for logs...' : 'No logs') : 'No matches'}
          </div>
        ) : (
          filteredLogs.map((entry, idx) => {
            // Format timestamp to HH:MM:SS
            const ts = entry.timestamp.split('T')[1]?.split('.')[0] || entry.timestamp;
            // Convert ANSI then highlight search matches
            const html = highlightText(ansiConverter.toHtml(entry.message), search);
            // Get test name if in test mode
            const testEntry = entry as TestLogEntry;
            const testLabel = mode === 'test' && testEntry.test_name ? testEntry.test_name : null;
            // Get stage if available
            const stageLabel = (entry as BuildLogEntry).stage || null;
            return (
              <div key={idx} className={`lv-entry ${entry.level.toLowerCase()}`}>
                <div className="lv-entry-row">
                  <span className="lv-ts">{ts}</span>
                  <span className={`lv-level-badge ${entry.level.toLowerCase()}`}>
                    {entry.level}
                  </span>
                  {stageLabel && (
                    <span className="lv-stage-badge">
                      {stageLabel}
                    </span>
                  )}
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
                {(entry.ato_traceback || entry.python_traceback) && (
                  <div className="lv-tracebacks">
                    {entry.ato_traceback && (
                      <TraceDetails
                        label="ato traceback"
                        content={entry.ato_traceback}
                        className="lv-trace-ato"
                      />
                    )}
                    {entry.python_traceback && (
                      <TraceDetails
                        label="python traceback"
                        content={entry.python_traceback}
                        className="lv-trace-python"
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
