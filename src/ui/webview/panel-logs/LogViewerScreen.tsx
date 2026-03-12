import type { CSSProperties, PointerEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../shared/components/Select";
import { RegexSearchBar, SearchBar } from "../shared/components/SearchBar";
import { Button } from "../shared/components/Button";
import type { SourceMode, TimeMode, TreeNode } from "../../shared/types";
import { LEVEL_SHORT } from "../../shared/types";
import type {
  UiAudience,
  UiLogEntry,
  UiLogLevel,
} from "../../shared/generated-types";
import type { SearchOptions } from "../shared/utils/searchUtils";
import {
  ansiConverter,
  computeRowDisplay,
  countDescendants,
  filterByLoggers,
  filterLogs,
  getUniqueTopLevelLoggers,
  groupLogsIntoTrees,
  initLogSettings,
  isSeparatorLine,
  loadEnabledLoggers,
  saveEnabledLoggers,
} from "./logUtils";
import {
  createLogRequest,
  LogRpcClient,
  useLogState,
  type LogTarget,
} from "./logRpcClient";
import "./LogViewer.css";

type ResizableColumnKey = "source" | "scope";

const LOG_COL_WIDTHS: Record<ResizableColumnKey, number> = {
  source: 96,
  scope: 96,
};

initLogSettings();

function getScopeLabel(mode: LogTarget["mode"]): string {
  return mode === "test" ? "Test" : "Stage";
}

function getScopeValue(entry: UiLogEntry, mode: LogTarget["mode"]): string | null {
  return mode === "test" ? entry.testName : entry.stage;
}

function LogRowCells({
  entry,
  display,
  scopeMode,
  levelFull,
  toggleHandlers,
}: {
  entry: UiLogEntry;
  display: ReturnType<typeof computeRowDisplay>;
  scopeMode: LogTarget["mode"];
  levelFull: boolean;
  toggleHandlers: {
    toggleTimeMode: () => void;
    toggleLevelWidth: () => void;
    toggleSourceMode: () => void;
  };
}) {
  const scopeValue = getScopeValue(entry, scopeMode);

  return (
    <>
      <span
        className="lv-ts"
        onClick={toggleHandlers.toggleTimeMode}
        title="Click: toggle format"
      >
        {display.ts}
      </span>
      <span
        className={`lv-level-badge ${entry.level.toLowerCase()} ${
          levelFull ? "" : "short"
        }`}
        onClick={toggleHandlers.toggleLevelWidth}
        title="Click: toggle short/full"
      >
        {levelFull ? entry.level : LEVEL_SHORT[entry.level]}
      </span>
      <span
        className="lv-source-badge"
        title={display.sourceTooltip}
        onClick={toggleHandlers.toggleSourceMode}
        style={display.sourceStyle}
      >
        {display.sourceDisplayValue}
      </span>
      <span className="lv-stage-badge" title={scopeValue || ""}>
        {scopeValue || "\u2014"}
      </span>
    </>
  );
}

function TraceDetails({
  label,
  content,
  className,
  defaultOpen = false,
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
        <span className={`lv-trace-arrow ${isOpen ? "open" : ""}`}>
          &#x25B8;
        </span>
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

function TracebacksInline({ entry }: { entry: UiLogEntry }) {
  if (!entry.atoTraceback && !entry.pythonTraceback) return null;
  return (
    <div className="lv-tracebacks lv-tracebacks-inline">
      {entry.atoTraceback && (
        <TraceDetails
          label="ato traceback"
          content={entry.atoTraceback}
          className="lv-trace-ato"
          defaultOpen
        />
      )}
      {entry.pythonTraceback && (
        <TraceDetails
          label="python traceback"
          content={entry.pythonTraceback}
          className="lv-trace-python"
        />
      )}
    </div>
  );
}

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
  scopeMode,
  toggleHandlers,
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
  scopeMode: LogTarget["mode"];
  toggleHandlers: {
    toggleTimeMode: () => void;
    toggleLevelWidth: () => void;
    toggleSourceMode: () => void;
  };
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const hasChildren = node.children.length > 0;
  const { entry, content } = node;
  const display = computeRowDisplay(
    entry,
    content,
    search,
    searchOptions,
    timeMode,
    sourceMode,
    firstTimestamp,
  );
  const descendantCount = countDescendants(node);

  return (
    <>
      <div
        className={`lv-tree-row ${entry.level.toLowerCase()} ${
          indentLevel === 0 ? "lv-tree-root" : "lv-tree-child"
        }`}
      >
        <LogRowCells
          entry={entry}
          display={display}
          scopeMode={scopeMode}
          levelFull={levelFull}
          toggleHandlers={toggleHandlers}
        />
        <div className="lv-tree-message-cell">
          <div className="lv-tree-message-main">
            {indentLevel > 0 && (
              <span
                className="lv-tree-indent"
                style={{ width: `${indentLevel * 1.2}em` }}
              />
            )}
            {hasChildren && (
              <button
                className={`lv-tree-toggle ${
                  isExpanded ? "expanded" : "collapsed"
                }`}
                onClick={() => setIsExpanded(!isExpanded)}
                title={isExpanded ? "Collapse" : "Expand"}
              >
                <span className="lv-tree-toggle-icon">&#x25B8;</span>
                {!isExpanded && (
                  <span className="lv-tree-child-count">{descendantCount}</span>
                )}
              </button>
            )}
            <pre
              className="lv-message"
              dangerouslySetInnerHTML={{ __html: display.html }}
            />
          </div>
          <TracebacksInline entry={entry} />
        </div>
      </div>
      {hasChildren &&
        isExpanded &&
        node.children.map((child, idx) => (
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
            scopeMode={scopeMode}
            toggleHandlers={toggleHandlers}
          />
        ))}
    </>
  );
}

function StandaloneLogRow({
  entry,
  content,
  search,
  searchOptions,
  levelFull,
  timeMode,
  sourceMode,
  firstTimestamp,
  scopeMode,
  toggleHandlers,
}: {
  entry: UiLogEntry;
  content: string;
  search: string;
  searchOptions: SearchOptions;
  levelFull: boolean;
  timeMode: TimeMode;
  sourceMode: SourceMode;
  firstTimestamp: number;
  scopeMode: LogTarget["mode"];
  toggleHandlers: {
    toggleTimeMode: () => void;
    toggleLevelWidth: () => void;
    toggleSourceMode: () => void;
  };
}) {
  const display = computeRowDisplay(
    entry,
    content,
    search,
    searchOptions,
    timeMode,
    sourceMode,
    firstTimestamp,
  );
  const sepInfo = isSeparatorLine(entry.message);

  return (
    <div className={`lv-entry-row lv-entry-standalone ${entry.level.toLowerCase()}`}>
      <LogRowCells
        entry={entry}
        display={display}
        scopeMode={scopeMode}
        levelFull={levelFull}
        toggleHandlers={toggleHandlers}
      />
      <div className="lv-message-cell">
        {sepInfo.isSeparator ? (
          <div
            className={`separator-line separator-${
              sepInfo.char === "=" ? "double" : "single"
            }`}
          >
            <span className="separator-line-bar" />
            {sepInfo.label && (
              <span className="separator-line-label">{sepInfo.label}</span>
            )}
            {sepInfo.label && <span className="separator-line-bar" />}
          </div>
        ) : (
          <pre
            className="lv-message"
            dangerouslySetInnerHTML={{ __html: display.html }}
          />
        )}
        <TracebacksInline entry={entry} />
      </div>
    </div>
  );
}

function LoggerFilter({
  logs,
  enabledLoggers,
  onEnabledLoggersChange,
}: {
  logs: UiLogEntry[];
  enabledLoggers: Set<string> | null;
  onEnabledLoggersChange: (enabled: Set<string> | null) => void;
}) {
  const availableLoggers = useMemo(() => getUniqueTopLevelLoggers(logs), [logs]);

  const currentEnabled = useMemo(() => {
    if (enabledLoggers === null) return new Set(availableLoggers);
    return enabledLoggers;
  }, [enabledLoggers, availableLoggers]);

  const toggleLogger = useCallback(
    (logger: string) => {
      const next = new Set(currentEnabled);
      if (next.has(logger)) next.delete(logger);
      else next.add(logger);

      const allEnabled =
        next.size === availableLoggers.length &&
        availableLoggers.every((name) => next.has(name));
      const value = allEnabled ? null : next;
      onEnabledLoggersChange(value);
      saveEnabledLoggers(value);
    },
    [availableLoggers, currentEnabled, onEnabledLoggersChange],
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        title="Filter by logger namespace"
        className="lv-select-trigger lv-logger-trigger"
        disabled={availableLoggers.length === 0}
      >
        Loggers
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        {availableLoggers.map((logger) => (
          <DropdownMenuCheckboxItem
            key={logger}
            checked={currentEnabled.has(logger)}
            onCheckedChange={() => toggleLogger(logger)}
          >
            {logger}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export interface LogViewerScreenProps {
  client: LogRpcClient;
  target: LogTarget | null;
  scopeValue?: string;
  onScopeChange?: (value: string) => void;
  targetControl?: ReactNode;
}

export function LogViewerScreen({
  client,
  target,
  scopeValue = "",
  onScopeChange,
  targetControl,
}: LogViewerScreenProps) {
  const [logLevels, setLogLevels] = useState<UiLogLevel[]>(() => {
    try {
      const parsed = JSON.parse(localStorage.getItem("lv-logLevels") || "[]");
      return Array.isArray(parsed) ? (parsed as UiLogLevel[]) : [];
    } catch {
      return [];
    }
  });
  const [audience, setAudience] = useState<UiAudience>("developer");
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [searchRegex, setSearchRegex] = useState(false);
  const [sourceRegex, setSourceRegex] = useState(false);
  const [searchCaseSensitive, setSearchCaseSensitive] = useState(false);
  const [sourceCaseSensitive, setSourceCaseSensitive] = useState(false);
  const [enabledLoggers, setEnabledLoggers] = useState<Set<string> | null>(() =>
    loadEnabledLoggers(),
  );
  const [levelFull, setLevelFull] = useState(
    () => localStorage.getItem("lv-levelFull") === "true",
  );
  const [timeMode, setTimeMode] = useState<TimeMode>(
    () => localStorage.getItem("lv-timeMode") as TimeMode,
  );
  const [sourceMode, setSourceMode] = useState<SourceMode>(
    () => localStorage.getItem("lv-sourceMode") as SourceMode,
  );
  const [autoScroll, setAutoScroll] = useState(true);
  const [allExpanded, setAllExpanded] = useState(false);
  const [expandKey, setExpandKey] = useState(0);
  const [columnWidths, setColumnWidths] =
    useState<Record<ResizableColumnKey, number>>(LOG_COL_WIDTHS);

  const resizeRef = useRef<{
    column: ResizableColumnKey;
    startX: number;
    startWidth: number;
  } | null>(null);
  const columnWidthsRef = useRef(columnWidths);
  const contentRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(autoScroll);

  columnWidthsRef.current = columnWidths;

  const { connectionState, error, logs, streaming } = useLogState(client);

  useEffect(() => {
    autoScrollRef.current = autoScroll;
  }, [autoScroll]);

  useEffect(() => {
    localStorage.setItem("lv-levelFull", String(levelFull));
  }, [levelFull]);

  useEffect(() => {
    localStorage.setItem("lv-timeMode", timeMode);
  }, [timeMode]);

  useEffect(() => {
    localStorage.setItem("lv-sourceMode", sourceMode);
  }, [sourceMode]);

  useEffect(() => {
    localStorage.setItem("lv-logLevels", JSON.stringify(logLevels));
  }, [logLevels]);

  useEffect(() => {
    if (!target) {
      client.stopStream();
      return;
    }

    client.startStream(
      createLogRequest(target, {
        audience,
        logLevels,
      }),
    );
    setAutoScroll(true);
  }, [audience, client, logLevels, target]);

  useEffect(() => {
    if (autoScrollRef.current && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [logs]);

  const searchOptions = useMemo<SearchOptions>(
    () => ({ isRegex: searchRegex, caseSensitive: searchCaseSensitive }),
    [searchCaseSensitive, searchRegex],
  );

  const sourceOptions = useMemo<SearchOptions>(
    () => ({ isRegex: sourceRegex, caseSensitive: sourceCaseSensitive }),
    [sourceCaseSensitive, sourceRegex],
  );

  const filteredLogs = useMemo(() => {
    const searchFiltered = filterLogs(
      logs,
      search,
      sourceFilter,
      searchOptions,
      sourceOptions,
    );
    return filterByLoggers(searchFiltered, enabledLoggers);
  }, [enabledLoggers, logs, search, searchOptions, sourceFilter, sourceOptions]);

  const firstTimestamp =
    filteredLogs.length > 0
      ? new Date(filteredLogs[0].timestamp).getTime()
      : 0;
  const groups = useMemo(() => groupLogsIntoTrees(filteredLogs), [filteredLogs]);
  const foldableCount = groups.filter(
    (group) => group.type === "tree" && group.root.children.length > 0,
  ).length;

  const toggleHandlers = useMemo(
    () => ({
      toggleTimeMode: () =>
        setTimeMode((value) => (value === "delta" ? "wall" : "delta")),
      toggleLevelWidth: () => setLevelFull((value) => !value),
      toggleSourceMode: () =>
        setSourceMode((value) => (value === "source" ? "logger" : "source")),
    }),
    [],
  );

  const toggleLevel = (level: UiLogLevel) => {
    setLogLevels((current) =>
      current.includes(level)
        ? current.filter((candidate) => candidate !== level)
        : [...current, level],
    );
  };

  const handleScroll = useCallback(() => {
    if (!contentRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = contentRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    if (!isAtBottom && autoScrollRef.current) {
      autoScrollRef.current = false;
      setAutoScroll(false);
    }
  }, []);

  const resizeHandleProps = useCallback(
    (column: ResizableColumnKey) => ({
      onPointerDown: (event: PointerEvent<HTMLDivElement>) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        resizeRef.current = {
          column,
          startWidth: columnWidthsRef.current[column],
          startX: event.clientX,
        };
      },
      onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
        const state = resizeRef.current;
        if (!state) return;
        setColumnWidths((current) => ({
          ...current,
          [state.column]: Math.max(
            60,
            Math.min(600, state.startWidth + event.clientX - state.startX),
          ),
        }));
      },
      onPointerUp: () => {
        resizeRef.current = null;
      },
      onDoubleClick: () =>
        setColumnWidths((current) => ({
          ...current,
          [column]: LOG_COL_WIDTHS[column],
        })),
    }),
    [],
  );

  const gridTemplateColumns = useMemo(
    () =>
      [
        timeMode === "delta" ? "60px" : "72px",
        levelFull ? "max-content" : "3ch",
        `${columnWidths.source}px`,
        `${columnWidths.scope}px`,
        "minmax(0, 1fr)",
      ].join(" "),
    [columnWidths, levelFull, timeMode],
  );

  const audienceItems = useMemo(
    () =>
      (["user", "developer", "agent"] as const).map((value) => ({
        label: value,
        value,
      })),
    [],
  );

  const scopeMode = target?.mode ?? "build";
  const scopeLabel = getScopeLabel(scopeMode);
  const emptyState = !target
    ? "No log target selected"
    : logs.length === 0
      ? streaming
        ? "Waiting for logs..."
        : "No logs"
      : "No matches";

  return (
    <div
      className="lv-container"
      style={{ "--lv-grid-template-columns": gridTemplateColumns } as CSSProperties}
    >
      <div className="lv-toolbar">
        <div className="lv-controls">
          <div className="lv-controls-left">
            <div
              className={`lv-status ${connectionState}`}
              title={`Status: ${connectionState}`}
            >
              <span className="lv-status-dot" />
              <span className="lv-status-count">
                {search || sourceFilter
                  ? `${filteredLogs.length}/${logs.length}`
                  : logs.length}
              </span>
            </div>
            {targetControl}
          </div>

          <div className="lv-controls-right">
            <DropdownMenu>
              <DropdownMenuTrigger className="lv-select-trigger">
                Log Levels
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {(["DEBUG", "INFO", "WARNING", "ERROR", "ALERT"] as const).map(
                  (level) => (
                    <DropdownMenuCheckboxItem
                      key={level}
                      checked={logLevels.includes(level)}
                      onCheckedChange={() => toggleLevel(level)}
                    >
                      <span className={`lv-level-badge ${level.toLowerCase()}`}>
                        {level}
                      </span>
                    </DropdownMenuCheckboxItem>
                  ),
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            <LoggerFilter
              logs={logs}
              enabledLoggers={enabledLoggers}
              onEnabledLoggersChange={setEnabledLoggers}
            />

            <Select
              items={audienceItems}
              value={audience}
              onValueChange={(value) => {
                if (value) setAudience(value as UiAudience);
              }}
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
              variant={autoScroll ? "default" : "secondary"}
              size="sm"
              className="lv-autoscroll-btn"
              onClick={() => setAutoScroll(!autoScroll)}
              title={autoScroll ? "Auto-scroll enabled" : "Auto-scroll disabled"}
            >
              {autoScroll ? "\u2B07 On" : "\u2B07 Off"}
            </Button>
          </div>
        </div>

        {error && <div className="inline-error">{error}</div>}
      </div>

      <div className="lv-log-grid">
        <div className="lv-column-headers">
          <div className="lv-col-header lv-col-ts">
            <span className="lv-col-label">Time</span>
          </div>
          <div className="lv-col-header lv-col-level">
            <span className="lv-col-label">Level</span>
          </div>
          <div className="lv-col-header lv-col-source lv-col-header-resizable">
            <RegexSearchBar
              value={sourceFilter}
              onChange={setSourceFilter}
              placeholder={sourceMode === "source" ? "file:line" : "logger"}
              isRegex={sourceRegex}
              onRegexChange={setSourceRegex}
              caseSensitive={sourceCaseSensitive}
              onCaseSensitiveChange={setSourceCaseSensitive}
              className="lv-col-search"
            />
            <div className="lv-column-resize-handle" {...resizeHandleProps("source")} />
          </div>
          <div className="lv-col-header lv-col-stage lv-col-header-resizable">
            {onScopeChange ? (
              <SearchBar
                value={scopeValue}
                onChange={onScopeChange}
                placeholder={scopeLabel}
                title={`Filter by ${scopeLabel.toLowerCase()}`}
                className="lv-col-search"
              />
            ) : (
              <span className="lv-col-label">{scopeLabel}</span>
            )}
            <div className="lv-column-resize-handle" {...resizeHandleProps("scope")} />
          </div>
          <div className="lv-col-header lv-col-message">
            <RegexSearchBar
              value={search}
              onChange={setSearch}
              placeholder="Search logs..."
              isRegex={searchRegex}
              onRegexChange={setSearchRegex}
              caseSensitive={searchCaseSensitive}
              onCaseSensitiveChange={setSearchCaseSensitive}
              className="lv-col-search lv-col-search-message"
            />
          </div>
        </div>

        <div className="lv-display-container">
          {foldableCount > 0 && (
            <div className="lv-expand-toolbar">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setAllExpanded(true);
                  setExpandKey((value) => value + 1);
                }}
                disabled={allExpanded}
                title="Expand all"
                className="lv-expand-btn"
              >
                &#x229E;
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setAllExpanded(false);
                  setExpandKey((value) => value + 1);
                }}
                disabled={!allExpanded}
                title="Collapse all"
                className="lv-expand-btn"
              >
                &#x229F;
              </Button>
            </div>
          )}
          <div className="lv-content" ref={contentRef} onScroll={handleScroll}>
            {filteredLogs.length === 0 ? (
              <div className="empty-state">{emptyState}</div>
            ) : (
              groups.map((group, groupIdx) => {
                if (group.type === "tree" && group.root.children.length > 0) {
                  return (
                    <TreeNodeRow
                      key={`${expandKey}-${groupIdx}`}
                      node={group.root}
                      search={search}
                      searchOptions={searchOptions}
                      levelFull={levelFull}
                      timeMode={timeMode}
                      sourceMode={sourceMode}
                      firstTimestamp={firstTimestamp}
                      indentLevel={0}
                      defaultExpanded={allExpanded}
                      scopeMode={scopeMode}
                      toggleHandlers={toggleHandlers}
                    />
                  );
                }

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
                    scopeMode={scopeMode}
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
