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
} from './logUtils';

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

// Recursive tree node component for nested folding
function TreeNodeRow({
  node,
  search,
  levelFull,
  timeMode,
  sourceMode,
  firstTimestamp,
  indentLevel,
  setLevelFull,
  setTimeMode,
}: {
  node: TreeNode;
  search: string;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  firstTimestamp: number;
  indentLevel: number;
  setLevelFull: (value: boolean) => void;
  setTimeMode: (value: TimeMode) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = node.children.length > 0;

  const { entry, content } = node;
  const ts = formatTs(entry.timestamp, timeMode, firstTimestamp);
  const html = highlightText(ansiConverter.toHtml(content), search);
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
      <div className={`lv-tree-row ${entry.level.toLowerCase()} ${indentLevel === 0 ? 'lv-tree-root' : 'lv-tree-child'} ${!levelFull ? 'lv-level-compact' : ''} ${timeMode === 'delta' ? 'lv-time-compact' : ''}`}>
        <span className="lv-ts" onClick={() => setTimeMode(timeMode === 'delta' ? 'wall' : 'delta')} title={TOOLTIPS.timestamp}>{ts}</span>
        <span className={`lv-level-badge ${entry.level.toLowerCase()} ${levelFull ? '' : 'short'}`} onClick={() => setLevelFull(!levelFull)} title={TOOLTIPS.level}>
          {levelFull ? entry.level : LEVEL_SHORT[entry.level]}
        </span>
        <span
          className="lv-source-badge"
          title={sourceTooltip}
          style={sourceColor ? { color: sourceColor, borderColor: sourceColor } : undefined}
        >
          {sourceDisplayValue}
        </span>
        <div className="lv-tree-message-cell">
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
      </div>
      {/* Tracebacks */}
      {(entry.ato_traceback || entry.python_traceback) && (() => {
        const structuredTb = tryParseStructuredTraceback(entry.python_traceback);
        return (
          <div className="lv-tracebacks" style={{ marginLeft: `${indentLevel * 1.2}em` }}>
            {entry.ato_traceback && (
              <TraceDetails
                label="ato traceback"
                content={entry.ato_traceback}
                className="lv-trace-ato"
              />
            )}
            {structuredTb && structuredTb.frames.length > 0 ? (
              <StackInspector traceback={structuredTb} />
            ) : entry.python_traceback ? (
              <TraceDetails
                label="python traceback"
                content={entry.python_traceback}
                className="lv-trace-python"
              />
            ) : null}
          </div>
        );
      })()}
      {/* Render children recursively */}
      {hasChildren && isExpanded && node.children.map((child, idx) => (
        <TreeNodeRow
          key={idx}
          node={child}
          search={search}
          levelFull={levelFull}
          timeMode={timeMode}
          sourceMode={sourceMode}
          firstTimestamp={firstTimestamp}
          indentLevel={indentLevel + 1}
          setLevelFull={setLevelFull}
          setTimeMode={setTimeMode}
        />
      ))}
    </>
  );
}

// Collapsible tree log group component
function TreeLogGroup({
  group,
  search,
  levelFull,
  timeMode,
  sourceMode,
  firstTimestamp,
  setLevelFull,
  setTimeMode,
}: {
  group: LogTreeGroup;
  search: string;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  firstTimestamp: number;
  setLevelFull: (value: boolean) => void;
  setTimeMode: (value: TimeMode) => void;
}) {
  return (
    <div className="lv-tree-group">
      <TreeNodeRow
        node={group.root}
        search={search}
        levelFull={levelFull}
        timeMode={timeMode}
        sourceMode={sourceMode}
        firstTimestamp={firstTimestamp}
        indentLevel={0}
        setLevelFull={setLevelFull}
        setTimeMode={setTimeMode}
      />
    </div>
  );
}

// Standalone log entry row
function StandaloneLogRow({
  entry,
  content,
  search,
  levelFull,
  timeMode,
  sourceMode,
  firstTimestamp,
  setLevelFull,
  setTimeMode,
}: {
  entry: LogEntry;
  content: string;
  search: string;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  firstTimestamp: number;
  setLevelFull: (value: boolean) => void;
  setTimeMode: (value: TimeMode) => void;
}) {
  const ts = formatTs(entry.timestamp, timeMode, firstTimestamp);
  const html = highlightText(ansiConverter.toHtml(content), search);
  const sourceLabel = formatSrc(entry.source_file, entry.source_line);
  const sourceColor = sourceMode === 'source'
    ? (entry.source_file ? hashStringToColor(entry.source_file) : undefined)
    : (entry.logger_name ? hashStringToColor(entry.logger_name) : undefined);
  const loggerShort = entry.logger_name?.split('.').pop() || '';
  const sourceDisplayValue = sourceMode === 'source' ? (sourceLabel || '—') : (loggerShort || '—');
  const sourceTooltip = sourceMode === 'source' ? (entry.source_file || '') : (entry.logger_name || '');
  const sepInfo = isSeparatorLine(entry.message);

  return (
    <div className={`lv-entry lv-entry-standalone ${entry.level.toLowerCase()}`}>
      <div className={`lv-entry-row ${!levelFull ? 'lv-level-compact' : ''} ${timeMode === 'delta' ? 'lv-time-compact' : ''}`}>
        <span className="lv-ts" onClick={() => setTimeMode(timeMode === 'delta' ? 'wall' : 'delta')} title={TOOLTIPS.timestamp}>{ts}</span>
        <span className={`lv-level-badge ${entry.level.toLowerCase()} ${levelFull ? '' : 'short'}`} onClick={() => setLevelFull(!levelFull)} title={TOOLTIPS.level}>
          {levelFull ? entry.level : LEVEL_SHORT[entry.level]}
        </span>
        <span
          className="lv-source-badge"
          title={sourceTooltip}
          style={sourceColor ? { color: sourceColor, borderColor: sourceColor } : undefined}
        >
          {sourceDisplayValue}
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
        </div>
      </div>
      {(entry.ato_traceback || entry.python_traceback) && (() => {
        const structuredTb = tryParseStructuredTraceback(entry.python_traceback);
        return (
          <div className="lv-tracebacks">
            {entry.ato_traceback && (
              <TraceDetails
                label="ato traceback"
                content={entry.ato_traceback}
                className="lv-trace-ato"
              />
            )}
            {structuredTb && structuredTb.frames.length > 0 ? (
              <StackInspector traceback={structuredTb} />
            ) : entry.python_traceback ? (
              <TraceDetails
                label="python traceback"
                content={entry.python_traceback}
                className="lv-trace-python"
              />
            ) : null}
          </div>
        );
      })()}
    </div>
  );
}

export interface LogDisplayProps {
  logs: LogEntry[];
  search: string;
  sourceFilter: string;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  autoScroll: boolean;
  streaming: boolean;
  onAutoScrollChange: (value: boolean) => void;
  setLevelFull: (value: boolean) => void;
  setTimeMode: (value: TimeMode) => void;
}

export function LogDisplay({
  logs,
  search,
  sourceFilter,
  levelFull,
  timeMode,
  sourceMode,
  autoScroll,
  streaming,
  onAutoScrollChange,
  setLevelFull,
  setTimeMode,
}: LogDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(autoScroll);

  // Keep ref in sync
  useEffect(() => {
    autoScrollRef.current = autoScroll;
  }, [autoScroll]);

  // Filter logs
  const filteredLogs = useMemo(
    () => filterLogs(logs, search, sourceFilter),
    [logs, search, sourceFilter]
  );

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

  return (
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
                key={groupIdx}
                group={group}
                search={search}
                levelFull={levelFull}
                timeMode={timeMode}
                sourceMode={sourceMode}
                firstTimestamp={firstTimestamp}
                setLevelFull={setLevelFull}
                setTimeMode={setTimeMode}
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
              levelFull={levelFull}
              timeMode={timeMode}
              sourceMode={sourceMode}
              firstTimestamp={firstTimestamp}
              setLevelFull={setLevelFull}
              setTimeMode={setTimeMode}
            />
          );
        })
      )}
    </div>
  );
}

// Export sub-components for advanced usage
export { ChevronDown, TraceDetails, TreeNodeRow, TreeLogGroup, StandaloneLogRow };
