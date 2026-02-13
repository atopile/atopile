/**
 * Test Log Viewer - Props-controlled variant for Test Explorer integration
 *
 * Uses shared log-viewer modules for consistent behavior with LogViewer.
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  LOG_LEVELS,
  LogLevel,
  Audience,
  TimeMode,
  SourceMode,
  useLogWebSocket,
  buildTestLogRequest,
  LogDisplay,
  ChevronDown,
  HeaderSearchBox,
  getStoredSetting,
  LoggerFilter,
  loadEnabledLoggers,
  calculateSourceColumnWidth,
} from './log-viewer';
import './LogViewer.css';

export interface TestLogViewerProps {
  testRunId: string;
  testName?: string | null;
  autoStream?: boolean;
}

export function TestLogViewer({ testRunId, testName, autoStream = false }: TestLogViewerProps) {
  // Display settings (persisted in localStorage)
  const [logLevels, setLogLevels] = useState<LogLevel[]>(() => {
    const stored = localStorage.getItem('lv-logLevels');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.every(l => LOG_LEVELS.includes(l))) {
          return parsed;
        }
      } catch { /* ignore */ }
    }
    return ['INFO', 'WARNING', 'ERROR', 'ALERT'];
  });
  const [audience] = useState<Audience>('developer');
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');

  // Logger filter state - persisted in localStorage (shared with LogViewer)
  const [enabledLoggers, setEnabledLoggers] = useState<Set<string> | null>(() => loadEnabledLoggers());

  // Display toggles
  const [levelFull, setLevelFull] = useState(() =>
    getStoredSetting('lv-levelFull', false)
  );
  const [stageFull, setStageFull] = useState(() =>
    getStoredSetting('lv-stageFull', false)
  );
  const [timeMode, setTimeMode] = useState<TimeMode>(() =>
    getStoredSetting('lv-timeMode', 'delta' as TimeMode, v => v === 'delta' || v === 'wall')
  );
  const [sourceMode, setSourceMode] = useState<SourceMode>(() =>
    getStoredSetting('lv-sourceMode', 'source' as SourceMode, v => v === 'source' || v === 'logger')
  );
  const [autoScroll, setAutoScroll] = useState(true);

  // Expand/collapse all state - start collapsed
  const [allExpanded, setAllExpanded] = useState(false);
  const [expandKey, setExpandKey] = useState(0);

  // Level dropdown
  const [levelDropdownOpen, setLevelDropdownOpen] = useState(false);
  const levelDropdownRef = useRef<HTMLDivElement>(null);

  // Track previous testRunId to detect changes
  const prevTestRunIdRef = useRef<string | null>(null);

  // WebSocket connection (lazy - connects on demand)
  const {
    connectionState,
    error,
    logs,
    streaming,
    connect: connectWs,
    startTestStream,
    stopStream,
    sendRequest,
  } = useLogWebSocket();

  // Connect to WebSocket on mount
  useEffect(() => {
    connectWs();
  }, [connectWs]);

  // Persist display states
  useEffect(() => {
    localStorage.setItem('lv-levelFull', String(levelFull));
  }, [levelFull]);
  useEffect(() => {
    localStorage.setItem('lv-timeMode', timeMode);
  }, [timeMode]);
  useEffect(() => {
    localStorage.setItem('lv-sourceMode', sourceMode);
  }, [sourceMode]);
  useEffect(() => {
    localStorage.setItem('lv-stageFull', String(stageFull));
  }, [stageFull]);
  useEffect(() => {
    localStorage.setItem('lv-logLevels', JSON.stringify(logLevels));
  }, [logLevels]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (levelDropdownRef.current && !levelDropdownRef.current.contains(event.target as Node)) {
        setLevelDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Start streaming
  const handleStartStream = useCallback(() => {
    startTestStream(buildTestLogRequest(testRunId, testName, logLevels, audience));
  }, [testRunId, testName, logLevels, audience, startTestStream]);

  // Toggle streaming
  const toggleStreaming = useCallback(() => {
    if (streaming) {
      stopStream();
    } else {
      handleStartStream();
    }
  }, [streaming, stopStream, handleStartStream]);

  // Auto-start when connected or when testRunId changes
  useEffect(() => {
    if (connectionState !== 'connected') return;
    if (!testRunId.trim()) return;

    // Check if testRunId changed
    const testRunIdChanged = prevTestRunIdRef.current !== testRunId;
    prevTestRunIdRef.current = testRunId;

    // Only start if this is initial load or testRunId changed
    if (!testRunIdChanged && streaming) return;

    // Stop any existing stream before starting new one
    if (testRunIdChanged && streaming) {
      stopStream();
    }

    if (autoStream) {
      handleStartStream();
    } else {
      // One-shot fetch
      const request = buildTestLogRequest(testRunId, testName, logLevels, audience);
      sendRequest({ ...request, count: 1000 });
    }
  }, [connectionState, testRunId, testName, autoStream, logLevels, audience, handleStartStream, sendRequest, streaming, stopStream]);

  const toggleLevel = (level: LogLevel) => {
    setLogLevels(prev =>
      prev.includes(level)
        ? prev.filter(l => l !== level)
        : [...prev, level]
    );
  };

  const handleAutoScrollChange = useCallback((value: boolean) => {
    setAutoScroll(value);
  }, []);

  const handleExpandAll = useCallback(() => {
    setAllExpanded(true);
    setExpandKey(k => k + 1);
  }, []);

  const handleCollapseAll = useCallback(() => {
    setAllExpanded(false);
    setExpandKey(k => k + 1);
  }, []);

  // Calculate dynamic source column width based on content
  const sourceColumnWidth = useMemo(
    () => calculateSourceColumnWidth(logs, sourceMode),
    [logs, sourceMode]
  );
  const gridTemplateColumns = useMemo(
    () => [
      timeMode === 'delta' ? 'var(--lv-col-time-compact)' : 'var(--lv-col-time)',
      levelFull ? 'max-content' : '3ch',
      'var(--lv-source-width)',
      stageFull ? 'max-content' : '12ch',
      'minmax(0, 1fr)',
    ].join(' '),
    [timeMode, levelFull, stageFull]
  );

  return (
    <div
      className="lv-container"
      style={{
        '--lv-source-width': `${sourceColumnWidth}ch`,
        '--lv-grid-template-columns': gridTemplateColumns,
      } as React.CSSProperties}
    >
      {/* Toolbar */}
      <div className="lv-toolbar">
        <div className="lv-controls">
          <div className="lv-controls-left">
            {/* Status */}
            <div className={`lv-status ${connectionState}`}>
              <span className="lv-status-dot" />
              <span className="lv-status-count">
                {search ? `${logs.filter(l => l.message.toLowerCase().includes(search.toLowerCase())).length}/${logs.length}` : logs.length}
              </span>
              {streaming && <span className="lv-live-badge">LIVE</span>}
            </div>

            {/* Stream button */}
            <button
              className={`lv-btn ${streaming ? 'lv-btn-danger' : 'lv-btn-success'}`}
              onClick={toggleStreaming}
              disabled={connectionState !== 'connected'}
            >
              {streaming ? 'Stop' : 'Stream'}
            </button>

            {/* Log levels dropdown */}
            <div className="lv-dropdown" ref={levelDropdownRef}>
              <button
                className={`selector-trigger ${levelDropdownOpen ? 'open' : ''}`}
                onClick={() => setLevelDropdownOpen(!levelDropdownOpen)}
              >
                <span className="selector-label">Levels ({logLevels.length})</span>
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

            {/* Logger filter dropdown */}
            <LoggerFilter
              logs={logs}
              enabledLoggers={enabledLoggers}
              onEnabledLoggersChange={setEnabledLoggers}
            />
          </div>

          <div className="lv-controls-right">
            {/* Source/Logger toggle */}
            <button
              className="lv-btn lv-btn-small"
              onClick={() => setSourceMode(m => m === 'source' ? 'logger' : 'source')}
              title="Toggle source/logger display"
            >
              {sourceMode === 'source' ? 'Src' : 'Log'}
            </button>

            {/* Auto-scroll toggle */}
            <button
              className={`lv-btn lv-btn-small ${autoScroll ? 'lv-btn-active' : ''}`}
              onClick={() => setAutoScroll(!autoScroll)}
              title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
            >
              {autoScroll ? '⬇ On' : '⬇ Off'}
            </button>
          </div>
        </div>

        {/* ID display */}
        <div className="lv-id-row">
          <span className="lv-id-label">Test Run:</span>
          <code className="lv-id-value">{testRunId}</code>
          {testName && (
            <>
              <span className="lv-id-label" style={{ marginLeft: '12px' }}>Test:</span>
              <code className="lv-id-value">{testName.split('::').pop()}</code>
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="lv-error">{error}</div>
        )}
      </div>

      <div className="lv-log-grid">
        {/* Column Headers */}
        <div className="lv-column-headers">
          <div className="lv-col-header lv-col-ts">
            <span className="lv-col-label">Time</span>
          </div>
          <div className="lv-col-header lv-col-level">
            <span className="lv-col-label">Level</span>
          </div>
          <div className="lv-col-header lv-col-source">
            <HeaderSearchBox
              value={sourceFilter}
              onChange={setSourceFilter}
              placeholder={sourceMode === 'source' ? 'file:line' : 'logger'}
            />
          </div>
          <div className="lv-col-header lv-col-stage">
            <span className="lv-col-label">Stage</span>
          </div>
          <div className="lv-col-header lv-col-message">
            <HeaderSearchBox
              value={search}
              onChange={setSearch}
              placeholder="Message"
              inputClassName="lv-col-search-message"
              wrapperClassName="lv-search-wrapper-message"
            />
          </div>
        </div>

        {/* Log Display */}
        <LogDisplay
          logs={logs}
          search={search}
          sourceFilter={sourceFilter}
          enabledLoggers={enabledLoggers}
          levelFull={levelFull}
          stageFull={stageFull}
          timeMode={timeMode}
          sourceMode={sourceMode}
          autoScroll={autoScroll}
          streaming={streaming}
          onAutoScrollChange={handleAutoScrollChange}
          setLevelFull={setLevelFull}
          setTimeMode={setTimeMode}
          setSourceMode={setSourceMode}
          setStageFull={setStageFull}
          allExpanded={allExpanded}
          expandKey={expandKey}
          onExpandAll={handleExpandAll}
          onCollapseAll={handleCollapseAll}
        />
      </div>
    </div>
  );
}
