/**
 * Problems Panel - Shows all errors and warnings from builds.
 * Similar to VS Code's Problems panel.
 */

import { useState, useMemo } from 'react';
import { AlertCircle, AlertTriangle, FileCode, ChevronDown, ChevronRight, Search, X } from 'lucide-react';
import './ProblemsPanel.css';

interface Problem {
  id: string;
  level: 'error' | 'warning';
  message: string;
  file?: string;
  line?: number;
  column?: number;
  stage?: string;        // Build stage that produced this problem
  logger?: string;       // Logger name
  buildName?: string;    // Which build target
  projectName?: string;  // Which project
  timestamp?: string;    // When it occurred
  ato_traceback?: string; // Source traceback if available
}

interface ProblemsPanelProps {
  problems: Problem[];
  onProblemClick?: (problem: Problem) => void;
}

// Group problems by file, sorting errors first within each group
function groupByFile(problems: Problem[]): Map<string, Problem[]> {
  const grouped = new Map<string, Problem[]>();

  for (const problem of problems) {
    const key = problem.file || '(no file)';
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key)!.push(problem);
  }

  // Sort each group: errors first, then warnings
  for (const [, fileProblems] of grouped) {
    fileProblems.sort((a, b) => {
      if (a.level === 'error' && b.level === 'warning') return -1;
      if (a.level === 'warning' && b.level === 'error') return 1;
      return 0;
    });
  }

  return grouped;
}

export function ProblemsPanel({
  problems,
  onProblemClick,
}: ProblemsPanelProps) {
  // Track collapsed file groups
  const [collapsedFiles, setCollapsedFiles] = useState<Set<string>>(new Set());
  // Search query state
  const [searchQuery, setSearchQuery] = useState('');

  // Filter problems by search query
  const filteredProblems = useMemo(() => {
    if (!searchQuery.trim()) return problems;
    const query = searchQuery.toLowerCase();
    return problems.filter(p =>
      p.message.toLowerCase().includes(query) ||
      p.file?.toLowerCase().includes(query) ||
      p.stage?.toLowerCase().includes(query)
    );
  }, [problems, searchQuery]);

  const errorCount = filteredProblems.filter(p => p.level === 'error').length;
  const grouped = useMemo(() => groupByFile(filteredProblems), [filteredProblems]);

  const toggleFileCollapse = (file: string) => {
    setCollapsedFiles(prev => {
      const next = new Set(prev);
      if (next.has(file)) {
        next.delete(file);
      } else {
        next.add(file);
      }
      return next;
    });
  };

  // Check if no problems at all or just filtered to empty
  const hasNoProblems = problems.length === 0;
  const hasNoMatches = !hasNoProblems && filteredProblems.length === 0;

  // Render toolbar
  const renderToolbar = () => (
    <div className="panel-toolbar">
      <div className="panel-toolbar-row">
        {/* Error count only */}
        {errorCount > 0 && (
          <div className="problems-summary-inline">
            <span className="problems-count error">
              <AlertCircle size={12} />
              {errorCount}
            </span>
          </div>
        )}

        <div className="search-box">
          <Search size={14} />
          <input
            type="text"
            placeholder="Filter problems..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              className="search-clear"
              onClick={() => setSearchQuery('')}
              title="Clear search"
            >
              <X size={12} />
            </button>
          )}
        </div>

      </div>
    </div>
  );

  if (hasNoProblems || hasNoMatches) {
    return (
      <div className="problems-panel empty" data-testid="problems-panel">
        {renderToolbar()}
        <div className="problems-empty-state">
          <AlertCircle size={24} className="problems-empty-icon" />
          <span className="problems-empty-text">
            {hasNoMatches ? 'No matching problems' : 'No problems for the active project'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="problems-panel" data-testid="problems-panel">
      {renderToolbar()}

      {/* Problems list grouped by file - scrollable */}
      <div className="problems-list">
        {Array.from(grouped.entries()).map(([file, fileProblems]) => {
          const isCollapsed = collapsedFiles.has(file);
          const fileErrors = fileProblems.filter(p => p.level === 'error').length;
          const fileWarnings = fileProblems.filter(p => p.level === 'warning').length;

          return (
            <div key={file} className={`problems-file-group ${isCollapsed ? 'collapsed' : ''}`}>
              <div
                className="problems-file-header"
                onClick={() => toggleFileCollapse(file)}
              >
                <span className="problems-file-expand">
                  {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                </span>
                <FileCode size={12} />
                <span className="problems-file-name" title={file}>
                  {file.split('/').pop() || file}
                </span>
                <span className="problems-file-path" title={file}>
                  {file}
                </span>
                <span className="problems-file-counts">
                  {fileErrors > 0 && (
                    <span className="problems-file-count error">{fileErrors}</span>
                  )}
                  {fileWarnings > 0 && (
                    <span className="problems-file-count warning">{fileWarnings}</span>
                  )}
                </span>
              </div>

              {!isCollapsed && (
                <div className="problems-file-items">
                  {fileProblems.map(problem => (
                    <div
                      key={problem.id}
                      className={`problem-item ${problem.level} ${problem.file ? 'clickable' : ''}`}
                      onClick={() => problem.file && onProblemClick?.(problem)}
                      title={problem.file ? `Click to go to ${problem.file}:${problem.line || 1}` : undefined}
                    >
                      <span className="problem-icon">
                        {problem.level === 'error'
                          ? <AlertCircle size={12} />
                          : <AlertTriangle size={12} />
                        }
                      </span>
                      <span className="problem-message">{problem.message}</span>
                      {problem.line && (
                        <span className="problem-location">
                          [{problem.line}{problem.column ? `:${problem.column}` : ''}]
                        </span>
                      )}
                      {problem.stage && (
                        <span className="problem-source">{problem.stage}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
