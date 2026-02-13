/**
 * Shared log display component for rendering log entries with tree grouping
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { StackInspector } from '../StackInspector';
import {
  LogEntry,
  TreeNode,
  LogTreeGroup,
  TimeMode,
  SourceMode,
  LEVEL_SHORT,
  TOOLTIPS,
} from './logTypes';
import {
  ansiConverter,
  hashStringToColor,
  highlightText,
  isSeparatorLine,
  formatTimestamp as formatTs,
  formatSource as formatSrc,
  tryParseStructuredTraceback,
  groupLogsIntoTrees,
  filterLogs,
  SearchOptions,
} from './logUtils';
import { filterByLoggers } from './LoggerFilter';

interface RowToggleHandlers {
  toggleTimeMode: () => void;
  toggleLevelWidth: () => void;
  toggleSourceMode: () => void;
  toggleStageWidth: () => void;
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
  className,
  defaultOpen = false
}: {
  label: string;
  content: string;
  className: string;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

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

// Collapsible wrapper for StackInspector
function CollapsibleStackTrace({
  traceback,
}: {
  traceback: Parameters<typeof StackInspector>[0]['traceback'];
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="lv-trace lv-trace-python">
      <button className="lv-trace-summary" onClick={() => setIsOpen(!isOpen)}>
        <span className={`lv-trace-arrow ${isOpen ? 'open' : ''}`}>▸</span>
        python traceback
      </button>
      {isOpen && <StackInspector traceback={traceback} />}
    </div>
  );
}

function TracebacksInline({
  entry,
}: {
  entry: LogEntry;
}) {
  if (!entry.ato_traceback && !entry.python_traceback) return null;

  const structuredTb = tryParseStructuredTraceback(entry.python_traceback);

  return (
    <div className="lv-tracebacks lv-tracebacks-inline">
      {entry.ato_traceback && (
        <TraceDetails
          label="ato traceback"
          content={entry.ato_traceback}
          className="lv-trace-ato"
          defaultOpen
        />
      )}
      {structuredTb && structuredTb.frames.length > 0 ? (
        <CollapsibleStackTrace traceback={structuredTb} />
      ) : entry.python_traceback ? (
        <TraceDetails
          label="python traceback"
          content={entry.python_traceback}
          className="lv-trace-python"
        />
      ) : null}
    </div>
  );
}

// Recursive tree node component for nested folding
function TreeNodeRow({
  node,
  search,
  searchOptions,
  levelFull,
  timeMode,
  sourceMode,
  firstTimestamp,
  indentLevel,
  defaultExpanded,
  rowToggleHandlers,
}: {
  node: TreeNode;
  search: string;
  searchOptions: SearchOptions;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  firstTimestamp: number;
  indentLevel: number;
  defaultExpanded: boolean;
  rowToggleHandlers: RowToggleHandlers;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const hasChildren = node.children.length > 0;

  const { entry, content } = node;
  const ts = formatTs(entry.timestamp, timeMode, firstTimestamp);
  const html = highlightText(ansiConverter.toHtml(content), search, searchOptions);
  const sourceLabel = formatSrc(entry.source_file, entry.source_line);
  const sourceColor = sourceMode === 'source'
    ? (entry.source_file ? hashStringToColor(entry.source_file) : undefined)
    : (entry.logger_name ? hashStringToColor(entry.logger_name) : undefined);
  const loggerShort = entry.logger_name?.split('.').pop() || '';
  const sourceDisplayValue = sourceMode === 'source' ? (sourceLabel || '—') : (loggerShort || '—');
  const sourceTooltip = sourceMode === 'source' ? (entry.source_file || '') : (entry.logger_name || '');

  // Count total descendants for collapsed badge
  const countDescendants = (n: TreeNode): number => {
    return n.children.length + n.children.reduce((sum, c) => sum + countDescendants(c), 0);
  };
  const descendantCount = countDescendants(node);

  return (
    <>
      <div className={`lv-tree-row ${entry.level.toLowerCase()} ${indentLevel === 0 ? 'lv-tree-root' : 'lv-tree-child'}`}>
        <span className="lv-ts" onClick={rowToggleHandlers.toggleTimeMode} title={TOOLTIPS.timestamp}>{ts}</span>
        <span className={`lv-level-badge ${entry.level.toLowerCase()} ${levelFull ? '' : 'short'}`} onClick={rowToggleHandlers.toggleLevelWidth} title={TOOLTIPS.level}>
          {levelFull ? entry.level : LEVEL_SHORT[entry.level]}
        </span>
        <span
          className="lv-source-badge"
          title={sourceTooltip}
          onClick={rowToggleHandlers.toggleSourceMode}
          style={sourceColor ? { color: sourceColor, borderColor: sourceColor } : undefined}
        >
          {sourceDisplayValue}
        </span>
        <span className="lv-stage-badge" title={entry.stage || ''} onClick={rowToggleHandlers.toggleStageWidth}>
          {entry.stage || '—'}
        </span>
        <div className="lv-tree-message-cell">
          <div className="lv-tree-message-main">
            {/* Space indentation for nested levels */}
            {indentLevel > 0 && (
              <span className="lv-tree-indent" style={{ width: `${indentLevel * 1.2}em` }} />
            )}
            {/* Toggle button if has children */}
            {hasChildren && (
              <button
                className={`lv-tree-toggle ${isExpanded ? 'expanded' : 'collapsed'}`}
                onClick={() => setIsExpanded(!isExpanded)}
                title={isExpanded ? 'Collapse' : 'Expand'}
              >
                <span className="lv-tree-toggle-icon">▸</span>
                {!isExpanded && <span className="lv-tree-child-count">{descendantCount}</span>}
              </button>
            )}
            <pre className="lv-message" dangerouslySetInnerHTML={{ __html: html }} />
          </div>
          <TracebacksInline entry={entry} />
        </div>
      </div>
      {/* Render children recursively */}
      {hasChildren && isExpanded && node.children.map((child, idx) => (
        <TreeNodeRow
          key={idx}
          node={child}
          search={search}
          searchOptions={searchOptions}
          levelFull={levelFull}
          timeMode={timeMode}
          sourceMode={sourceMode}
          firstTimestamp={firstTimestamp}
          indentLevel={indentLevel + 1}
          defaultExpanded={defaultExpanded}
          rowToggleHandlers={rowToggleHandlers}
        />
      ))}
    </>
  );
}

// Collapsible tree log group component
function TreeLogGroup({
  group,
  search,
  searchOptions,
  levelFull,
  timeMode,
  sourceMode,
  firstTimestamp,
  defaultExpanded,
  rowToggleHandlers,
}: {
  group: LogTreeGroup;
  search: string;
  searchOptions: SearchOptions;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  firstTimestamp: number;
  defaultExpanded: boolean;
  rowToggleHandlers: RowToggleHandlers;
}) {
  return (
    <TreeNodeRow
      node={group.root}
      search={search}
      searchOptions={searchOptions}
      levelFull={levelFull}
      timeMode={timeMode}
      sourceMode={sourceMode}
      firstTimestamp={firstTimestamp}
      indentLevel={0}
      defaultExpanded={defaultExpanded}
      rowToggleHandlers={rowToggleHandlers}
    />
  );
}

// Standalone log entry row
function StandaloneLogRow({
  entry,
  content,
  search,
  searchOptions,
  levelFull,
  timeMode,
  sourceMode,
  firstTimestamp,
  rowToggleHandlers,
}: {
  entry: LogEntry;
  content: string;
  search: string;
  searchOptions: SearchOptions;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  firstTimestamp: number;
  rowToggleHandlers: RowToggleHandlers;
}) {
  const ts = formatTs(entry.timestamp, timeMode, firstTimestamp);
  const html = highlightText(ansiConverter.toHtml(content), search, searchOptions);
  const sourceLabel = formatSrc(entry.source_file, entry.source_line);
  const sourceColor = sourceMode === 'source'
    ? (entry.source_file ? hashStringToColor(entry.source_file) : undefined)
    : (entry.logger_name ? hashStringToColor(entry.logger_name) : undefined);
  const loggerShort = entry.logger_name?.split('.').pop() || '';
  const sourceDisplayValue = sourceMode === 'source' ? (sourceLabel || '—') : (loggerShort || '—');
  const sourceTooltip = sourceMode === 'source' ? (entry.source_file || '') : (entry.logger_name || '');
  const sepInfo = isSeparatorLine(entry.message);

  return (
    <>
      <div className={`lv-entry-row lv-entry-standalone ${entry.level.toLowerCase()}`}>
        <span className="lv-ts" onClick={rowToggleHandlers.toggleTimeMode} title={TOOLTIPS.timestamp}>{ts}</span>
        <span className={`lv-level-badge ${entry.level.toLowerCase()} ${levelFull ? '' : 'short'}`} onClick={rowToggleHandlers.toggleLevelWidth} title={TOOLTIPS.level}>
          {levelFull ? entry.level : LEVEL_SHORT[entry.level]}
        </span>
        <span
          className="lv-source-badge"
          title={sourceTooltip}
          onClick={rowToggleHandlers.toggleSourceMode}
          style={sourceColor ? { color: sourceColor, borderColor: sourceColor } : undefined}
        >
          {sourceDisplayValue}
        </span>
        <span className="lv-stage-badge" title={entry.stage || ''} onClick={rowToggleHandlers.toggleStageWidth}>
          {entry.stage || '—'}
        </span>
        <div className="lv-message-cell">
          {sepInfo.isSeparator ? (
            <div className={`lv-separator-line lv-separator-${sepInfo.char === '=' ? 'double' : 'single'}`}>
              <span className="lv-separator-line-bar" />
              {sepInfo.label && <span className="lv-separator-line-label">{sepInfo.label}</span>}
              {sepInfo.label && <span className="lv-separator-line-bar" />}
            </div>
          ) : (
            <pre className="lv-message" dangerouslySetInnerHTML={{ __html: html }} />
          )}
          <TracebacksInline entry={entry} />
        </div>
      </div>
    </>
  );
}

export interface LogDisplayProps {
  logs: LogEntry[];
  search: string;
  sourceFilter: string;
  searchOptions?: SearchOptions;
  sourceOptions?: SearchOptions;
  enabledLoggers?: Set<string> | null;
  levelFull: boolean;
  stageFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  autoScroll: boolean;
  streaming: boolean;
  onAutoScrollChange: (value: boolean) => void;
  setLevelFull: (value: boolean) => void;
  setTimeMode: (value: TimeMode) => void;
  setSourceMode: (value: SourceMode) => void;
  setStageFull: (value: boolean) => void;
  // Expansion control
  allExpanded: boolean;
  expandKey: number;
  onExpandAll: () => void;
  onCollapseAll: () => void;
}

export function LogDisplay({
  logs,
  search,
  sourceFilter,
  searchOptions = { isRegex: false },
  sourceOptions = { isRegex: false },
  enabledLoggers,
  levelFull,
  stageFull,
  timeMode,
  sourceMode,
  autoScroll,
  streaming,
  onAutoScrollChange,
  setLevelFull,
  setTimeMode,
  setSourceMode,
  setStageFull,
  allExpanded,
  expandKey,
  onExpandAll,
  onCollapseAll,
}: LogDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(autoScroll);

  // Keep ref in sync
  useEffect(() => {
    autoScrollRef.current = autoScroll;
  }, [autoScroll]);

  // Filter logs by search/source, then by enabled loggers
  const filteredLogs = useMemo(() => {
    const searchFiltered = filterLogs(logs, search, sourceFilter, searchOptions, sourceOptions);
    return filterByLoggers(searchFiltered, enabledLoggers ?? null);
  }, [logs, search, sourceFilter, searchOptions, sourceOptions, enabledLoggers]);

  // First timestamp for delta calculation
  const firstTimestamp = filteredLogs.length > 0 ? new Date(filteredLogs[0].timestamp).getTime() : 0;

  // Group logs into trees
  const groups = useMemo(
    () => groupLogsIntoTrees(filteredLogs),
    [filteredLogs]
  );

  // Detect scroll up to disable auto-scroll
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    if (!isAtBottom && autoScrollRef.current) {
      autoScrollRef.current = false;
      onAutoScrollChange(false);
    }
  }, [onAutoScrollChange]);

  // Auto-scroll when logs change
  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  // Count how many groups have children (foldable)
  const foldableCount = groups.filter(g => g.type === 'tree' && g.root.children.length > 0).length;
  const rowToggleHandlers = useMemo<RowToggleHandlers>(() => ({
    toggleTimeMode: () => setTimeMode(m => m === 'delta' ? 'wall' : 'delta'),
    toggleLevelWidth: () => setLevelFull(v => !v),
    toggleSourceMode: () => setSourceMode(m => m === 'source' ? 'logger' : 'source'),
    toggleStageWidth: () => setStageFull(v => !v),
  }), []);

  return (
    <div className="lv-display-container">
      {/* Expand/Collapse toolbar */}
      {foldableCount > 0 && (
        <div className="lv-expand-toolbar">
          <button
            className="lv-expand-btn"
            onClick={onExpandAll}
            disabled={allExpanded}
            title="Expand all"
          >
            <span className="lv-expand-icon">⊞</span>
          </button>
          <button
            className="lv-expand-btn"
            onClick={onCollapseAll}
            disabled={!allExpanded}
            title="Collapse all"
          >
            <span className="lv-expand-icon">⊟</span>
          </button>
        </div>
      )}
      <div
        className="lv-content"
        ref={containerRef}
        onScroll={handleScroll}
      >
        {filteredLogs.length === 0 ? (
          <div className="lv-empty">
            {logs.length === 0 ? (streaming ? 'Waiting for logs...' : 'No logs') : 'No matches'}
          </div>
        ) : (
          groups.map((group, groupIdx) => {
            // Tree groups with children get the collapsible TreeLogGroup
            if (group.type === 'tree' && group.root.children.length > 0) {
              return (
                <TreeLogGroup
                  key={`${expandKey}-${groupIdx}`}
                  group={group}
                  search={search}
                  searchOptions={searchOptions}
                  levelFull={levelFull}
                  timeMode={timeMode}
                  sourceMode={sourceMode}
                  firstTimestamp={firstTimestamp}
                  defaultExpanded={allExpanded}
                  rowToggleHandlers={rowToggleHandlers}
                />
              );
            }

            // Standalone entries render normally
            return (
              <StandaloneLogRow
                key={groupIdx}
                entry={group.root.entry}
                content={group.root.content}
                search={search}
                searchOptions={searchOptions}
                levelFull={levelFull}
                timeMode={timeMode}
                sourceMode={sourceMode}
                firstTimestamp={firstTimestamp}
                rowToggleHandlers={rowToggleHandlers}
              />
            );
          })
        )}
      </div>
    </div>
  );
}

// Export sub-components for advanced usage
export { ChevronDown, TraceDetails, TreeNodeRow, TreeLogGroup, StandaloneLogRow };
