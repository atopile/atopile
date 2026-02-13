/**
 * Log Viewer - WebSocket wrapper with parameter inputs
 * Supports both build logs and test logs modes
 * Always streams; automatically restarts when filters change.
 */

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { useStore } from '../store';
import { sendAction } from '../api/websocket';
import {
  LOG_LEVELS,
  AUDIENCES,
  LogLevel,
  Audience,
  LogMode,
  TimeMode,
  SourceMode,
  useLogWebSocket,
  buildBuildLogRequest,
  buildTestLogRequest,
  LogDisplay,
  ChevronDown,
  getStoredSetting,
  isValidRegex,
  SearchOptions,
  HeaderSearchBox,
  LoggerFilter,
  loadEnabledLoggers,
  calculateSourceColumnWidth,
} from './log-viewer';
import './LogViewer.css';

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

export function LogViewer() {
  // Get initial values from URL params
  const initialParams = getInitialParams();

  // Mode toggle: build logs vs test logs
  const [mode, setMode] = useState<LogMode>(initialParams.mode);

  // Query parameters - shared (logLevels persisted in localStorage)
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
  const [audience, setAudience] = useState<Audience>('developer');
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [searchRegex, setSearchRegex] = useState(false);
  const [sourceRegex, setSourceRegex] = useState(false);
  const [searchCaseSensitive, setSearchCaseSensitive] = useState(false);
  const [sourceCaseSensitive, setSourceCaseSensitive] = useState(false);

  // Logger filter state - persisted in localStorage
  const [enabledLoggers, setEnabledLoggers] = useState<Set<string> | null>(() => loadEnabledLoggers());

  // Build log specific parameters - buildId lives in the shared store
  const buildId = useStore((state) => state.logViewerBuildId) ?? '';
  const setBuildId = useCallback((id: string) => {
    useStore.getState().setLogViewerBuildId(id || null);
    sendAction('setLogViewCurrentId', { buildId: id || null, stage: null });
  }, []);
  const [stage, setStage] = useState('');

  // Initialize buildId from URL params on mount
  useEffect(() => {
    if (initialParams.buildId) {
      setBuildId(initialParams.buildId);
    }
  }, [setBuildId]);

  // Listen for stage changes dispatched by the websocket handler
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ stage: string | null }>).detail;
      setStage(detail.stage ?? '');
    };
    window.addEventListener('atopile:log_view_stage_changed', handler);
    return () => window.removeEventListener('atopile:log_view_stage_changed', handler);
  }, []);

  // Test log specific parameters
  const [testRunId, setTestRunId] = useState(initialParams.testRunId);
  const [testName, setTestName] = useState(initialParams.testName);

  // Get queued/active builds for auto-selection
  const queuedBuilds = useStore((state) => state.queuedBuilds);
  const builds = useStore((state) => state.builds);

  // Display toggle states - persisted in localStorage
  const [levelFull, setLevelFull] = useState(() =>
    getStoredSetting('lv-levelFull', true)
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

  // Level dropdown state
  const [levelDropdownOpen, setLevelDropdownOpen] = useState(false);
  const levelDropdownRef = useRef<HTMLDivElement>(null);

  // Status tooltip state
  const [showStatusTooltip, setShowStatusTooltip] = useState(false);

  // WebSocket connection (lazy - connects on demand)
  const {
    connectionState,
    error,
    logs,
    streaming,
    wsUrl,
    setLogs,
    connect: connectWs,
    startBuildStream,
    startTestStream,
    stopStream,
  } = useLogWebSocket();

  // Connect to WebSocket on mount
  useEffect(() => {
    connectWs();
  }, [connectWs]);

  // Persist display states to localStorage
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

  // Auto-stream: (re)start the stream whenever any filter parameter changes.
  // A short debounce batches rapid changes (e.g. typing in an input).
  useEffect(() => {
    if (connectionState !== 'connected') return;

    const id = mode === 'build' ? buildId.trim() : testRunId.trim();
    if (!id) {
      stopStream();
      return;
    }

    const timer = setTimeout(() => {
      stopStream();
      setLogs([]);

      if (mode === 'build') {
        startBuildStream(buildBuildLogRequest(buildId, stage, logLevels, audience));
      } else {
        startTestStream(buildTestLogRequest(testRunId, testName, logLevels, audience));
      }
      setAutoScroll(true);
    }, 150);

    return () => clearTimeout(timer);
  }, [mode, buildId, stage, testRunId, testName, logLevels, audience, connectionState, stopStream, startBuildStream, startTestStream, setLogs]);

  // Populate build_id from the latest active build when none is set
  useEffect(() => {
    if (mode !== 'build') return;
    if (buildId.trim()) return;

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
    if (latestBuildId) {
      setBuildId(latestBuildId);
    }
  }, [queuedBuilds, builds, mode, buildId, setBuildId]);

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

  // Search options for regex support
  const searchOptions: SearchOptions = useMemo(() => ({
    isRegex: searchRegex,
    caseSensitive: searchCaseSensitive,
  }), [searchRegex, searchCaseSensitive]);

  const sourceOptions: SearchOptions = useMemo(() => ({
    isRegex: sourceRegex,
    caseSensitive: sourceCaseSensitive,
  }), [sourceRegex, sourceCaseSensitive]);

  // Validate regex patterns
  const searchRegexError = searchRegex ? isValidRegex(search).error : undefined;
  const sourceRegexError = sourceRegex ? isValidRegex(sourceFilter).error : undefined;

  // Calculate dynamic column widths based on content
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
                {search ? `${logs.filter(l => l.message.toLowerCase().includes(search.toLowerCase())).length}/${logs.length}` : logs.length}
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

            {/* Mode-specific ID input */}
            {mode === 'build' ? (
              <input
                type="text"
                value={buildId}
                onChange={(e) => setBuildId(e.target.value)}
                placeholder="Build ID"
                className="lv-input"
              />
            ) : (
              <input
                type="text"
                value={testRunId}
                onChange={(e) => setTestRunId(e.target.value)}
                placeholder="Test Run ID"
                className="lv-input"
              />
            )}
          </div>

          {/* Right section: Filters */}
          <div className="lv-controls-right">
            {/* Level dropdown */}
            <div className="lv-dropdown" ref={levelDropdownRef}>
              <button
                className={`selector-trigger ${levelDropdownOpen ? 'open' : ''}`}
                onClick={() => setLevelDropdownOpen(!levelDropdownOpen)}
              >
                <span className="selector-label">Log Levels ({logLevels.length})</span>
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

            <select
              value={audience}
              onChange={(e) => setAudience(e.target.value as Audience)}
              className="lv-select"
            >
              {AUDIENCES.map(aud => (
                <option key={aud} value={aud}>{aud}</option>
              ))}
            </select>

            <span className="lv-separator" />

            <button
              className={`lv-btn lv-btn-small ${autoScroll ? 'lv-btn-active' : ''}`}
              onClick={() => setAutoScroll(!autoScroll)}
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

      <div className="lv-log-grid">
        {/* Column Headers with Search */}
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
              error={sourceRegexError}
              caseSensitive={sourceCaseSensitive}
              onToggleCaseSensitive={() => setSourceCaseSensitive(!sourceCaseSensitive)}
              regex={sourceRegex}
              onToggleRegex={() => setSourceRegex(!sourceRegex)}
            />
          </div>
          <div className="lv-col-header lv-col-stage">
            <HeaderSearchBox
              value={mode === 'build' ? stage : testName}
              onChange={(value) => (mode === 'build' ? setStage(value) : setTestName(value))}
              placeholder={mode === 'build' ? 'Stage' : 'Test Name'}
              title={mode === 'build' ? 'Filter by build stage' : 'Filter by test name'}
              inputClassName="lv-col-search-stage"
            />
          </div>
          <div className="lv-col-header lv-col-message">
            <HeaderSearchBox
              value={search}
              onChange={setSearch}
              placeholder="Message"
              error={searchRegexError}
              caseSensitive={searchCaseSensitive}
              onToggleCaseSensitive={() => setSearchCaseSensitive(!searchCaseSensitive)}
              regex={searchRegex}
              onToggleRegex={() => setSearchRegex(!searchRegex)}
              inputClassName="lv-col-search-message"
              wrapperClassName="lv-search-wrapper-message"
            />
          </div>
        </div>

        {/* Scrollable Log Content */}
        <LogDisplay
          logs={logs}
          search={search}
          sourceFilter={sourceFilter}
          searchOptions={searchOptions}
          sourceOptions={sourceOptions}
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
