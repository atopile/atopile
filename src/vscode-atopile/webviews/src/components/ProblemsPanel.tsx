/**
 * Problems Panel - Shows all errors and warnings from builds.
 * Similar to VS Code's Problems panel.
 */

import { useState } from 'react';
import { AlertCircle, AlertTriangle, FileCode, ChevronDown, ChevronRight } from 'lucide-react';
import { BuildSelector, type Selection, type Project } from './BuildSelector';
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

interface ProblemFilter {
  levels: ('error' | 'warning')[];
  buildNames: string[];
  stageIds: string[];
}

interface ProblemsPanelProps {
  problems: Problem[];
  filter?: ProblemFilter;
  selection?: Selection;
  onSelectionChange?: (selection: Selection) => void;
  projects?: Project[];
  onProblemClick?: (problem: Problem) => void;
  onToggleLevelFilter?: (level: 'error' | 'warning') => void;
}

// Group problems by file
function groupByFile(problems: Problem[]): Map<string, Problem[]> {
  const grouped = new Map<string, Problem[]>();
  
  for (const problem of problems) {
    const key = problem.file || '(no file)';
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key)!.push(problem);
  }
  
  return grouped;
}

export function ProblemsPanel({
  problems,
  filter,
  selection,
  onSelectionChange,
  projects = [],
  onProblemClick,
  onToggleLevelFilter
}: ProblemsPanelProps) {
  // Track collapsed file groups
  const [collapsedFiles, setCollapsedFiles] = useState<Set<string>>(new Set());

  const errorCount = problems.filter(p => p.level === 'error').length;
  const warningCount = problems.filter(p => p.level === 'warning').length;
  const grouped = groupByFile(problems);

  // Check if a filter is active
  const showErrors = !filter?.levels?.length || filter.levels.includes('error');
  const showWarnings = !filter?.levels?.length || filter.levels.includes('warning');

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

  if (problems.length === 0) {
    return (
      <div className="problems-panel empty" data-testid="problems-panel">
        {/* Toolbar even when empty */}
        <div className="problems-toolbar">
          <div className="problems-filters">
            <button
              className={`problems-filter-btn ${showErrors ? 'active' : ''} error`}
              onClick={() => onToggleLevelFilter?.('error')}
              title={showErrors ? 'Hide errors' : 'Show errors'}
            >
              <AlertCircle size={12} />
              <span>0</span>
            </button>
            <button
              className={`problems-filter-btn ${showWarnings ? 'active' : ''} warning`}
              onClick={() => onToggleLevelFilter?.('warning')}
              title={showWarnings ? 'Hide warnings' : 'Show warnings'}
            >
              <AlertTriangle size={12} />
              <span>0</span>
            </button>
          </div>
          <div className="problems-actions">
            {selection && onSelectionChange && projects.length > 0 && (
              <BuildSelector
                selection={selection}
                onSelectionChange={onSelectionChange}
                projects={projects}
                showSymbols={false}
                compact
              />
            )}
          </div>
        </div>
        <div className="problems-empty-state">
          <AlertCircle size={24} className="problems-empty-icon" />
          <span className="problems-empty-text">No problems</span>
        </div>
      </div>
    );
  }

  return (
    <div className="problems-panel" data-testid="problems-panel">
      {/* Toolbar with filters and build selector */}
      <div className="problems-toolbar">
        <div className="problems-filters">
          <button
            className={`problems-filter-btn ${showErrors ? 'active' : ''} error`}
            onClick={() => onToggleLevelFilter?.('error')}
            title={showErrors ? 'Hide errors' : 'Show errors'}
          >
            <AlertCircle size={12} />
            <span>{errorCount}</span>
          </button>
          <button
            className={`problems-filter-btn ${showWarnings ? 'active' : ''} warning`}
            onClick={() => onToggleLevelFilter?.('warning')}
            title={showWarnings ? 'Hide warnings' : 'Show warnings'}
          >
            <AlertTriangle size={12} />
            <span>{warningCount}</span>
          </button>
        </div>
        <div className="problems-actions">
          {selection && onSelectionChange && projects.length > 0 && (
            <BuildSelector
              selection={selection}
              onSelectionChange={onSelectionChange}
              projects={projects}
              showSymbols={false}
              compact
            />
          )}
        </div>
      </div>

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

// Mock problems for development
export const mockProblems: Problem[] = [
  {
    id: '1',
    level: 'error',
    message: 'Cannot find module "missing-module"',
    file: 'src/main.ato',
    line: 15,
    column: 8,
    stage: 'initializing build context',  // Matches UI stage name
    buildName: 'default',
    projectName: 'my-project',
  },
  {
    id: '2',
    level: 'error',
    message: 'Type mismatch: expected Resistor, got Capacitor',
    file: 'src/main.ato',
    line: 42,
    stage: 'post instantiation design check',  // Matches UI stage name
    buildName: 'default',
    projectName: 'my-project',
  },
  {
    id: '3',
    level: 'warning',
    message: 'Unused parameter: debug_mode',
    file: 'src/main.ato',
    line: 8,
    stage: 'initializing build context',  // Matches UI stage name
    buildName: 'default',
    projectName: 'my-project',
  },
  {
    id: '4',
    level: 'warning',
    message: 'Multiple matches for C1, using first match',
    file: 'src/power.ato',
    line: 23,
    stage: 'picker',
    buildName: 'default',
    projectName: 'other-project',
  },
  {
    id: '5',
    level: 'error',
    message: 'Constraint violation: voltage out of range (3.3V not in 5V±10%)',
    file: 'src/power.ato',
    line: 31,
    stage: 'post solve checks',  // Matches UI stage name
    buildName: 'example',
    projectName: 'other-project',
  },
];
