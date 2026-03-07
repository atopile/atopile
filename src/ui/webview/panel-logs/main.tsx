/**
 * Log Viewer - Main component with build selection, filtering, and log display.
 * Build-logs only (no test mode). Streams through the shared RPC client.
 */

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { render } from "../shared/render";
import { WebviewRpcClient } from '../shared/rpcClient';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem, DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuCheckboxItem } from '../shared/components/Select';
import { SearchBar, RegexSearchBar } from '../shared/components/SearchBar';
import { Button } from '../shared/components/Button';
import {
  Build, ProjectState,
  LogLevel, Audience, TimeMode, SourceMode,
  LogEntry, TreeNode, LEVEL_SHORT,
} from '../../shared/types';
import type { SearchOptions } from '../shared/utils/searchUtils';
import {
  loadEnabledLoggers, getUniqueTopLevelLoggers, saveEnabledLoggers,
  ansiConverter, isSeparatorLine,
  groupLogsIntoTrees, filterLogs, filterByLoggers,
  computeRowDisplay, initLogSettings, countDescendants,
} from './logUtils';
import { LogRpcClient, logClient, connectLogClient } from './logRpcClient';
import './LogViewer.css';

type ResizableColumnKey = 'source' | 'stage';

const LOG_COL_WIDTHS: Record<ResizableColumnKey, number> = {
  source: 96,
  stage: 96,
};

initLogSettings();

// -- Row sub-components -------------------------------------------------------

function LogRowCells({ entry, display, levelFull, toggleHandlers }: {
  entry: LogEntry; display: ReturnType<typeof computeRowDisplay>;
  levelFull: boolean;
  toggleHandlers: { toggleTimeMode: () => void; toggleLevelWidth: () => void; toggleSourceMode: () => void };
}) {
  return (
    <>
      <span className="lv-ts" onClick={toggleHandlers.toggleTimeMode} title="Click: toggle format">{display.ts}</span>
      <span className={`lv-level-badge ${entry.level.toLowerCase()} ${levelFull ? '' : 'short'}`} onClick={toggleHandlers.toggleLevelWidth} title="Click: toggle short/full">
        {levelFull ? entry.level : LEVEL_SHORT[entry.level]}
      </span>
      <span className="lv-source-badge" title={display.sourceTooltip} onClick={toggleHandlers.toggleSourceMode} style={display.sourceStyle}>
        {display.sourceDisplayValue}
      </span>
      <span className="lv-stage-badge" title={entry.stage || ''}>{entry.stage || '\u2014'}</span>
    </>
  );
}

function TraceDetails({ label, content, className, defaultOpen = false }: {
  label: string; content: string; className: string; defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div className={`lv-trace ${className}`}>
      <button className="lv-trace-summary" onClick={() => setIsOpen(!isOpen)}>
        <span className={`lv-trace-arrow ${isOpen ? 'open' : ''}`}>&#x25B8;</span>
        {label}
      </button>
      {isOpen && (
        <pre className="lv-trace-content" dangerouslySetInnerHTML={{ __html: ansiConverter.toHtml(content) }} />
      )}
    </div>
  );
}

function TracebacksInline({ entry }: { entry: LogEntry }) {
  if (!entry.ato_traceback && !entry.python_traceback) return null;
  return (
    <div className="lv-tracebacks lv-tracebacks-inline">
      {entry.ato_traceback && (
        <TraceDetails label="ato traceback" content={entry.ato_traceback} className="lv-trace-ato" defaultOpen />
      )}
      {entry.python_traceback && (
        <TraceDetails label="python traceback" content={entry.python_traceback} className="lv-trace-python" />
      )}
    </div>
  );
}

function TreeNodeRow({
  node, search, searchOptions, levelFull, timeMode, sourceMode,
  firstTimestamp, indentLevel, defaultExpanded, toggleHandlers,
}: {
  node: TreeNode; search: string; searchOptions: SearchOptions;
  levelFull: boolean; timeMode: TimeMode; sourceMode: SourceMode;
  firstTimestamp: number; indentLevel: number; defaultExpanded: boolean;
  toggleHandlers: { toggleTimeMode: () => void; toggleLevelWidth: () => void; toggleSourceMode: () => void };
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const hasChildren = node.children.length > 0;
  const { entry, content } = node;
  const display = computeRowDisplay(entry, content, search, searchOptions, timeMode, sourceMode, firstTimestamp);
  const descendantCount = countDescendants(node);

  return (
    <>
      <div className={`lv-tree-row ${entry.level.toLowerCase()} ${indentLevel === 0 ? 'lv-tree-root' : 'lv-tree-child'}`}>
        <LogRowCells entry={entry} display={display} levelFull={levelFull} toggleHandlers={toggleHandlers} />
        <div className="lv-tree-message-cell">
          <div className="lv-tree-message-main">
            {indentLevel > 0 && <span className="lv-tree-indent" style={{ width: `${indentLevel * 1.2}em` }} />}
            {hasChildren && (
              <button
                className={`lv-tree-toggle ${isExpanded ? 'expanded' : 'collapsed'}`}
                onClick={() => setIsExpanded(!isExpanded)}
                title={isExpanded ? 'Collapse' : 'Expand'}
              >
                <span className="lv-tree-toggle-icon">&#x25B8;</span>
                {!isExpanded && <span className="lv-tree-child-count">{descendantCount}</span>}
              </button>
            )}
            <pre className="lv-message" dangerouslySetInnerHTML={{ __html: display.html }} />
          </div>
          <TracebacksInline entry={entry} />
        </div>
      </div>
      {hasChildren && isExpanded && node.children.map((child, idx) => (
        <TreeNodeRow
          key={idx} node={child} search={search} searchOptions={searchOptions}
          levelFull={levelFull} timeMode={timeMode} sourceMode={sourceMode}
          firstTimestamp={firstTimestamp} indentLevel={indentLevel + 1}
          defaultExpanded={defaultExpanded} toggleHandlers={toggleHandlers}
        />
      ))}
    </>
  );
}

function StandaloneLogRow({
  entry, content, search, searchOptions, levelFull, timeMode,
  sourceMode, firstTimestamp, toggleHandlers,
}: {
  entry: LogEntry; content: string; search: string; searchOptions: SearchOptions;
  levelFull: boolean; timeMode: TimeMode; sourceMode: SourceMode;
  firstTimestamp: number;
  toggleHandlers: { toggleTimeMode: () => void; toggleLevelWidth: () => void; toggleSourceMode: () => void };
}) {
  const display = computeRowDisplay(entry, content, search, searchOptions, timeMode, sourceMode, firstTimestamp);
  const sepInfo = isSeparatorLine(entry.message);

  return (
    <div className={`lv-entry-row lv-entry-standalone ${entry.level.toLowerCase()}`}>
      <LogRowCells entry={entry} display={display} levelFull={levelFull} toggleHandlers={toggleHandlers} />
      <div className="lv-message-cell">
        {sepInfo.isSeparator ? (
          <div className={`separator-line separator-${sepInfo.char === '=' ? 'double' : 'single'}`}>
            <span className="separator-line-bar" />
            {sepInfo.label && <span className="separator-line-label">{sepInfo.label}</span>}
            {sepInfo.label && <span className="separator-line-bar" />}
          </div>
        ) : (
          <pre className="lv-message" dangerouslySetInnerHTML={{ __html: display.html }} />
        )}
        <TracebacksInline entry={entry} />
      </div>
    </div>
  );
}

// -- LoggerFilter -------------------------------------------------------------

function LoggerFilter({ logs, enabledLoggers, onEnabledLoggersChange }: {
  logs: LogEntry[];
  enabledLoggers: Set<string> | null;
  onEnabledLoggersChange: (enabled: Set<string> | null) => void;
}) {
  const availableLoggers = useMemo(() => getUniqueTopLevelLoggers(logs), [logs]);

  const currentEnabled = useMemo(() => {
    if (enabledLoggers === null) return new Set(availableLoggers);
    return enabledLoggers;
  }, [enabledLoggers, availableLoggers]);

  const toggleLogger = useCallback((logger: string) => {
    const newEnabled = new Set(currentEnabled);
    if (newEnabled.has(logger)) newEnabled.delete(logger);
    else newEnabled.add(logger);

    if (newEnabled.size === availableLoggers.length && availableLoggers.every(l => newEnabled.has(l))) {
      onEnabledLoggersChange(null);
      saveEnabledLoggers(null);
    } else {
      onEnabledLoggersChange(newEnabled);
      saveEnabledLoggers(newEnabled);
    }
  }, [currentEnabled, availableLoggers, onEnabledLoggersChange]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger title="Filter by logger namespace" className="lv-select-trigger lv-logger-trigger" disabled={availableLoggers.length === 0}>
        Loggers
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        {availableLoggers.map(logger => (
          <DropdownMenuCheckboxItem key={logger} checked={currentEnabled.has(logger)} onCheckedChange={() => toggleLogger(logger)}>
            {logger}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// -- LogViewer (main) ---------------------------------------------------------

function LogViewer() {
  const projectState = WebviewRpcClient.useSubscribe('projectState') as ProjectState;
  const currentBuilds = WebviewRpcClient.useSubscribe('currentBuilds') as Build[];
  const previousBuilds = WebviewRpcClient.useSubscribe('previousBuilds') as Build[];

  // Query parameters
  const [buildId, setBuildId] = useState('');
  const [stage, setStage] = useState('');
  const [logLevels, setLogLevels] = useState<LogLevel[]>(
    () => JSON.parse(localStorage.getItem('lv-logLevels')!),
  );
  const [audience, setAudience] = useState<Audience>('developer');
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [searchRegex, setSearchRegex] = useState(false);
  const [sourceRegex, setSourceRegex] = useState(false);
  const [searchCaseSensitive, setSearchCaseSensitive] = useState(false);
  const [sourceCaseSensitive, setSourceCaseSensitive] = useState(false);

  // Logger filter state
  const [enabledLoggers, setEnabledLoggers] = useState<Set<string> | null>(() => loadEnabledLoggers());

  // Display toggle states
  const [levelFull, setLevelFull] = useState(() => localStorage.getItem('lv-levelFull') === 'true');
  const [timeMode, setTimeMode] = useState<TimeMode>(() => localStorage.getItem('lv-timeMode') as TimeMode);
  const [sourceMode, setSourceMode] = useState<SourceMode>(() => localStorage.getItem('lv-sourceMode') as SourceMode);
  const [autoScroll, setAutoScroll] = useState(true);

  // Expand/collapse
  const [allExpanded, setAllExpanded] = useState(false);
  const [expandKey, setExpandKey] = useState(0);

  // Column resize via pointer capture
  const resizeRef = useRef<{ column: ResizableColumnKey; startX: number; startWidth: number } | null>(null);
  const [columnWidths, setColumnWidths] = useState<Record<ResizableColumnKey, number>>(LOG_COL_WIDTHS);
  const columnWidthsRef = useRef(columnWidths);
  columnWidthsRef.current = columnWidths;

  // Scroll
  const contentRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(autoScroll);

  const { connectionState, error, logs, streaming } = LogRpcClient.useLogState();

  // Connect on mount
  useEffect(() => { if (!logClient) connectLogClient(); }, []);

  // Persist display states
  useEffect(() => { localStorage.setItem('lv-levelFull', String(levelFull)); }, [levelFull]);
  useEffect(() => { localStorage.setItem('lv-timeMode', timeMode); }, [timeMode]);
  useEffect(() => { localStorage.setItem('lv-sourceMode', sourceMode); }, [sourceMode]);
  useEffect(() => { localStorage.setItem('lv-logLevels', JSON.stringify(logLevels)); }, [logLevels]);

  // Auto-scroll tracking
  useEffect(() => { autoScrollRef.current = autoScroll; }, [autoScroll]);

  // Auto-stream: restart when selection/filter params change
  useEffect(() => {
    const id = buildId.trim();
    if (!id) { logClient?.stopStream(); return; }

    logClient?.startBuildStream({
      build_id: id,
      stage: stage.trim() || null,
      log_levels: logLevels.length > 0 ? logLevels : null,
      audience,
    });
    setAutoScroll(true);
  }, [buildId, stage, logLevels, audience]);

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    if (autoScrollRef.current && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [logs]);

  // Builds for the selected project/target
  const projectBuilds = useMemo(() => {
    const project = projectState.selectedProject;
    const target = projectState.selectedTarget;
    if (!project) return [];
    const matchesSelection = (b: Build) =>
      b.projectRoot === project && (!target || b.name === target);

    return [...(currentBuilds || []), ...(previousBuilds || [])]
      .filter(matchesSelection)
      .sort((a, b) => (b.startedAt ?? 0) - (a.startedAt ?? 0));
  }, [
    currentBuilds,
    previousBuilds,
    projectState.selectedProject,
    projectState.selectedTarget,
  ]);

  // Keep selected build if still visible; otherwise prefer active, then latest.
  useEffect(() => {
    if (buildId && projectBuilds.some(b => b.buildId === buildId)) return;
    const active = projectBuilds.find(b => b.status === 'building' || b.status === 'queued');
    setBuildId(active?.buildId ?? projectBuilds[0]?.buildId ?? '');
  }, [projectBuilds, buildId]);

  // Filtering
  const searchOptions: SearchOptions = useMemo(() => ({
    isRegex: searchRegex, caseSensitive: searchCaseSensitive,
  }), [searchRegex, searchCaseSensitive]);

  const sourceOptions: SearchOptions = useMemo(() => ({
    isRegex: sourceRegex, caseSensitive: sourceCaseSensitive,
  }), [sourceRegex, sourceCaseSensitive]);

  const filteredLogs = useMemo(() => {
    const searchFiltered = filterLogs(logs, search, sourceFilter, searchOptions, sourceOptions);
    return filterByLoggers(searchFiltered, enabledLoggers);
  }, [logs, search, sourceFilter, searchOptions, sourceOptions, enabledLoggers]);

  const firstTimestamp = filteredLogs.length > 0 ? new Date(filteredLogs[0].timestamp).getTime() : 0;
  const groups = useMemo(() => groupLogsIntoTrees(filteredLogs), [filteredLogs]);
  const foldableCount = groups.filter(g => g.type === 'tree' && g.root.children.length > 0).length;

  // Toggle handlers (functional updaters = no deps)
  const toggleHandlers = useMemo(() => ({
    toggleTimeMode: () => setTimeMode(t => t === 'delta' ? 'wall' : 'delta'),
    toggleLevelWidth: () => setLevelFull(f => !f),
    toggleSourceMode: () => setSourceMode(m => m === 'source' ? 'logger' : 'source'),
  }), []);

  const toggleLevel = (level: LogLevel) => {
    setLogLevels(prev => prev.includes(level) ? prev.filter(l => l !== level) : [...prev, level]);
  };

  // Scroll handler
  const handleScroll = useCallback(() => {
    if (!contentRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = contentRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    if (!isAtBottom && autoScrollRef.current) {
      autoScrollRef.current = false;
      setAutoScroll(false);
    }
  }, []);

  // Column resize via pointer capture (no document listeners needed)
  const resizeHandleProps = useCallback((column: ResizableColumnKey) => ({
    onPointerDown: (e: React.PointerEvent) => {
      e.currentTarget.setPointerCapture(e.pointerId);
      resizeRef.current = { column, startX: e.clientX, startWidth: columnWidthsRef.current[column] };
    },
    onPointerMove: (e: React.PointerEvent) => {
      const r = resizeRef.current;
      if (!r) return;
      setColumnWidths(prev => ({
        ...prev, [r.column]: Math.max(60, Math.min(600, r.startWidth + e.clientX - r.startX)),
      }));
    },
    onPointerUp: () => { resizeRef.current = null; },
    onDoubleClick: () => setColumnWidths(prev => ({ ...prev, [column]: LOG_COL_WIDTHS[column] })),
  }), []);

  // Grid template
  const gridTemplateColumns = useMemo(() => [
    timeMode === 'delta' ? '60px' : '72px',
    levelFull ? 'max-content' : '3ch',
    `${columnWidths.source}px`,
    `${columnWidths.stage}px`,
    'minmax(0, 1fr)',
  ].join(' '), [timeMode, levelFull, columnWidths]);

  const buildItems = useMemo(() =>
    projectBuilds.map(b => ({
      label: `${b.name || 'default'} - ${b.status} ${b.startedAt ? new Date(b.startedAt * 1000).toLocaleTimeString() : ''}`,
      value: b.buildId || '',
    })),
  [projectBuilds]);

  const audienceItems = useMemo(() =>
    (['user', 'developer', 'agent'] as const).map(aud => ({ label: aud, value: aud })),
  []);

  return (
    <div className="lv-container" style={{ '--lv-grid-template-columns': gridTemplateColumns } as React.CSSProperties}>
      {/* Toolbar */}
      <div className="lv-toolbar">
        <div className="lv-controls">
          <div className="lv-controls-left">
            <div className={`lv-status ${connectionState}`} title={`Status: ${connectionState}`}>
              <span className="lv-status-dot" />
              <span className="lv-status-count">
                {search || sourceFilter ? `${filteredLogs.length}/${logs.length}` : logs.length}
              </span>
            </div>

            <Select
              items={buildItems}
              value={buildId || null}
              onValueChange={(v) => setBuildId(v || '')}
              className="lv-build-select"
            >
              <SelectTrigger className="lv-select-trigger">
                <SelectValue placeholder="Select build..." />
              </SelectTrigger>
              <SelectContent>
                {buildItems.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="lv-controls-right">
            <DropdownMenu>
              <DropdownMenuTrigger className="lv-select-trigger">
                Log Levels
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'] as const).map(level => (
                  <DropdownMenuCheckboxItem key={level} checked={logLevels.includes(level)} onCheckedChange={() => toggleLevel(level)}>
                    <span className={`lv-level-badge ${level.toLowerCase()}`}>{level}</span>
                  </DropdownMenuCheckboxItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <LoggerFilter logs={logs} enabledLoggers={enabledLoggers} onEnabledLoggersChange={setEnabledLoggers} />

            <Select
              items={audienceItems}
              value={audience}
              onValueChange={(v) => { if (v) setAudience(v as Audience); }}
            >
              <SelectTrigger className="lv-select-trigger">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {audienceItems.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant={autoScroll ? 'default' : 'secondary'}
              size="sm"
              className="lv-autoscroll-btn"
              onClick={() => setAutoScroll(!autoScroll)}
              title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
            >
              {autoScroll ? '\u2B07 On' : '\u2B07 Off'}
            </Button>
          </div>
        </div>

        {error && <div className="inline-error">{error}</div>}
      </div>

      <div className="lv-log-grid">
        {/* Column Headers */}
        <div className="lv-column-headers">
          <div className="lv-col-header lv-col-ts"><span className="lv-col-label">Time</span></div>
          <div className="lv-col-header lv-col-level"><span className="lv-col-label">Level</span></div>
          <div className="lv-col-header lv-col-source lv-col-header-resizable">
            <RegexSearchBar
              value={sourceFilter} onChange={setSourceFilter}
              placeholder={sourceMode === 'source' ? 'file:line' : 'logger'}
              isRegex={sourceRegex} onRegexChange={setSourceRegex}
              caseSensitive={sourceCaseSensitive} onCaseSensitiveChange={setSourceCaseSensitive}
              className="lv-col-search"
            />
            <div className="lv-column-resize-handle"
              {...resizeHandleProps('source')}
              title="Drag to resize. Double-click to reset."
            />
          </div>
          <div className="lv-col-header lv-col-stage lv-col-header-resizable">
            <SearchBar
              value={stage} onChange={setStage}
              placeholder="Stage" title="Filter by build stage"
              className="lv-col-search"
            />
            <div className="lv-column-resize-handle"
              {...resizeHandleProps('stage')}
              title="Drag to resize. Double-click to reset."
            />
          </div>
          <div className="lv-col-header lv-col-message">
            <RegexSearchBar
              value={search} onChange={setSearch} placeholder="Message"
              isRegex={searchRegex} onRegexChange={setSearchRegex}
              caseSensitive={searchCaseSensitive} onCaseSensitiveChange={setSearchCaseSensitive}
              className="lv-col-search lv-col-search-message"
            />
          </div>
        </div>

        {/* Log Content */}
        <div className="lv-display-container">
          {foldableCount > 0 && (
            <div className="lv-expand-toolbar">
              <Button variant="ghost" size="sm" onClick={() => { setAllExpanded(true); setExpandKey(k => k + 1); }} disabled={allExpanded} title="Expand all" className="lv-expand-btn">
                &#x229E;
              </Button>
              <Button variant="ghost" size="sm" onClick={() => { setAllExpanded(false); setExpandKey(k => k + 1); }} disabled={!allExpanded} title="Collapse all" className="lv-expand-btn">
                &#x229F;
              </Button>
            </div>
          )}
          <div className="lv-content" ref={contentRef} onScroll={handleScroll}>
            {filteredLogs.length === 0 ? (
              <div className="empty-state">
                {logs.length === 0 ? (streaming ? 'Waiting for logs...' : 'No logs') : 'No matches'}
              </div>
            ) : (
              groups.map((group, groupIdx) => {
                if (group.type === 'tree' && group.root.children.length > 0) {
                  return (
                    <TreeNodeRow
                      key={`${expandKey}-${groupIdx}`} node={group.root} search={search}
                      searchOptions={searchOptions} levelFull={levelFull} timeMode={timeMode}
                      sourceMode={sourceMode} firstTimestamp={firstTimestamp} indentLevel={0}
                      defaultExpanded={allExpanded} toggleHandlers={toggleHandlers}
                    />
                  );
                }
                return (
                  <StandaloneLogRow
                    key={groupIdx} entry={group.root.entry} content={group.root.content}
                    search={search} searchOptions={searchOptions} levelFull={levelFull}
                    timeMode={timeMode} sourceMode={sourceMode} firstTimestamp={firstTimestamp}
                    toggleHandlers={toggleHandlers}
                  />
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

render(LogViewer);
