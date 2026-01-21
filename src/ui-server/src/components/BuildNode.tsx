/**
 * BuildNode - Build target card component.
 * Displays build status, progress, stages, and actions.
 * Compact when not selected, expanded with details when selected.
 */

import { useState, useRef, useEffect, memo, useMemo } from 'react';
import {
  ChevronDown, ChevronRight, Play, Clock, Check, X,
  AlertTriangle, AlertCircle, Circle, SkipForward,
  FileCode, Search, Grid3X3, Layout, Cuboid, Box, Square, Trash2
} from 'lucide-react';
import type { Selection, BuildTarget, BuildStage, ModuleDefinition } from './projectsTypes';
import { SymbolNode } from './SymbolNode';
import { NameValidationDropdown } from './NameValidationDropdown';
import { validateName } from '../utils/nameValidation';
import './BuildNode.css';

// Timer component for running stages - isolated to prevent parent re-renders
function StageTimer() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setSeconds(s => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return <>{seconds}s</>;
}

// Format time in mm:ss or hh:mm:ss
export function formatBuildTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Parse timestamp that may be in format "YYYY-MM-DD_HH-MM-SS" or ISO format
function parseTimestamp(timestamp: string): Date {
  const normalized = timestamp.replace(/_/g, 'T').replace(/-(\d{2})-(\d{2})$/, ':$1:$2');
  return new Date(normalized);
}

// Format relative time (e.g., "2m ago", "1h ago", "yesterday")
export function formatRelativeTime(timestamp: string): string {
  const date = parseTimestamp(timestamp);
  if (isNaN(date.getTime())) return '';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// Get status icon for build target
export function getStatusIcon(status: BuildTarget['status'], size: number = 12, queuePosition?: number) {
  switch (status) {
    case 'building':
      return <Circle size={size} className="status-icon building" />;
    case 'queued':
      return (
        <span className="status-icon queued" title={queuePosition ? `Queue position: ${queuePosition}` : 'Queued'}>
          <Clock size={size} />
          {queuePosition && <span className="queue-position">{queuePosition}</span>}
        </span>
      );
    case 'success':
      return <Check size={size} className="status-icon success" />;
    case 'error':
      return <X size={size} className="status-icon error" />;
    case 'warning':
      return <AlertTriangle size={size} className="status-icon warning" />;
    default:
      return <div className="status-dot idle" />;
  }
}

// Get stage status icon
export function getStageIcon(status: BuildStage['status'], size: number = 12) {
  switch (status) {
    case 'running':
      return <Circle size={size} className="stage-icon running" />;
    case 'success':
      return <Check size={size} className="stage-icon success" />;
    case 'warning':
      return <AlertTriangle size={size} className="stage-icon warning" />;
    case 'error':
      return <X size={size} className="stage-icon error" />;
    case 'skipped':
      return <SkipForward size={size} className="stage-icon skipped" />;
    case 'pending':
    default:
      return <Circle size={size} className="stage-icon pending" />;
  }
}

// Get status icon for last build (dimmed version)
export function getLastBuildStatusIcon(status: string, size: number = 12) {
  switch (status) {
    case 'success':
      return <Check size={size} className="status-icon success dimmed" />;
    case 'warning':
      return <AlertTriangle size={size} className="status-icon warning dimmed" />;
    case 'error':
    case 'failed':
      return <AlertCircle size={size} className="status-icon error dimmed" />;
    default:
      return <Circle size={size} className="status-icon idle dimmed" />;
  }
}

interface BuildNodeProps {
  build: BuildTarget;
  projectId: string;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void;
  onCancelBuild?: (buildId: string) => void;
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void;
  onUpdateBuild?: (projectId: string, buildId: string, updates: Partial<BuildTarget>) => void;
  onDeleteBuild?: (projectId: string, buildId: string) => void;
  onOpenSource?: (projectId: string, entry: string) => void;
  onOpenKiCad?: (projectId: string, buildId: string) => void;
  onOpenLayout?: (projectId: string, buildId: string) => void;
  onOpen3D?: (projectId: string, buildId: string) => void;
  availableModules?: ModuleDefinition[];
  // Read-only mode for packages: hides build/delete buttons, status icon, progress
  readOnly?: boolean;
}

export const BuildNode = memo(function BuildNode({
  build,
  projectId,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  onUpdateBuild,
  onDeleteBuild,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  availableModules = [],
  readOnly = false
}: BuildNodeProps) {
  const [showStages, setShowStages] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [isEditingEntry, setIsEditingEntry] = useState(false);
  const [buildName, setBuildName] = useState(build.name);
  const [entryPoint, setEntryPoint] = useState(build.entry);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Timer state for live build time display
  const [elapsedTime, setElapsedTime] = useState(build.elapsedSeconds || 0);
  const isBuilding = build.status === 'building';

  // Track previous stage for animation
  const [prevStage, setPrevStage] = useState<string | null>(null);
  const [stageAnimating, setStageAnimating] = useState(false);

  // Update timer every second while building
  useEffect(() => {
    if (!isBuilding) {
      setElapsedTime(build.elapsedSeconds || build.duration || 0);
      return;
    }

    setElapsedTime(build.elapsedSeconds || 0);

    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isBuilding, build.elapsedSeconds, build.duration]);

  // Progress calculation using totalStages from backend
  // TODO: Replace this estimate once builds are defined in the graph
  const ESTIMATED_TOTAL_STAGES = 20;  // Fallback if backend doesn't provide totalStages

  const getProgress = () => {
    if (!build.stages || build.stages.length === 0) return 0;

    // Use backend-provided totalStages or fall back to estimate
    const totalStages = build.totalStages || ESTIMATED_TOTAL_STAGES;

    let completedCount = 0;
    let runningCount = 0;

    for (const stage of build.stages) {
      const isComplete = stage.status === 'success' || stage.status === 'warning' ||
                        stage.status === 'error' || stage.status === 'skipped';
      const isRunning = stage.status === 'running';

      if (isComplete) {
        completedCount += 1;
      } else if (isRunning) {
        runningCount += 0.5;  // Running stage counts as half complete
      }
    }

    const progress = ((completedCount + runningCount) / totalStages) * 100;
    return Math.min(progress, 100);
  };

  // Get current running stage name
  const getCurrentStage = () => {
    if (build.currentStage) return build.currentStage;
    if (!build.stages) return null;
    const running = build.stages.find(s => s.status === 'running');
    return running?.displayName || running?.name || null;
  };

  // Trigger scroll-up animation when stage changes
  const currentStage = getCurrentStage();
  useEffect(() => {
    if (currentStage && currentStage !== prevStage) {
      setStageAnimating(true);
      setPrevStage(currentStage);
      const timer = setTimeout(() => setStageAnimating(false), 300);
      return () => clearTimeout(timer);
    }
  }, [currentStage, prevStage]);

  // Filter modules based on search
  const filteredModules = availableModules
    .filter(m => m.type === 'module' || m.type === 'component')
    .filter(m => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        m.name.toLowerCase().includes(query) ||
        m.entry.toLowerCase().includes(query) ||
        m.file.toLowerCase().includes(query)
      );
    });

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isEditingEntry && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isEditingEntry]);

  // Validate build name as user types
  const nameValidation = useMemo(() => validateName(buildName), [buildName]);

  const handleNameSave = () => {
    // Only save if valid
    if (!nameValidation.isValid) {
      return; // Keep editing, don't close
    }
    setIsEditingName(false);
    if (onUpdateBuild) {
      onUpdateBuild(projectId, build.id, { name: buildName });
    }
  };

  const handleApplyNameSuggestion = (suggestion: string) => {
    setBuildName(suggestion);
  };

  const handleEntrySearch = (value: string) => {
    setSearchQuery(value);
  };

  const handleSelectModule = (module: ModuleDefinition) => {
    setEntryPoint(module.entry);
    setIsEditingEntry(false);
    setSearchQuery('');
    if (onUpdateBuild) {
      onUpdateBuild(projectId, build.id, { entry: module.entry });
    }
  };

  const hasSymbols = build.symbols && build.symbols.length > 0;
  const hasStages = build.stages && build.stages.length > 0;
  const isSelected = selection.type === 'build' && selection.buildId === `${projectId}:${build.id}`;

  return (
    <div
      className={`build-card ${isSelected ? 'selected' : ''} ${isBuilding ? 'building' : ''}`}
      onClick={(e) => {
        e.stopPropagation();
        onSelect({
          type: 'build',
          projectId,
          buildId: `${projectId}:${build.id}`,
          label: `${build.name}`
        });
      }}
    >
      {/* Header row - always visible */}
      <div
        className="build-card-header"
        onClick={(e) => {
          // If already selected and clicking on the header background, collapse
          if (isSelected) {
            e.stopPropagation();
            onSelect({ type: 'none' });
          }
        }}
      >
        <div className="build-header-left">
          {/* Status icon - hide in readOnly mode, show simple bullet instead */}
          {readOnly ? (
            <div className="build-status-icon">
              <Circle size={8} className="status-icon idle" />
            </div>
          ) : (
            <div className="build-status-icon">
              {getStatusIcon(build.status, 12, build.queuePosition)}
            </div>
          )}

          {/* Editable build name - not editable in readOnly mode */}
          {isEditingName && isSelected && !readOnly ? (
            <div className="name-input-wrapper" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                className={`build-name-input ${!nameValidation.isValid ? 'invalid' : ''}`}
                value={buildName}
                onChange={(e) => setBuildName(e.target.value)}
                onBlur={() => {
                  // Only close if valid, otherwise stay open
                  if (nameValidation.isValid) {
                    handleNameSave();
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleNameSave();
                  if (e.key === 'Escape') {
                    setBuildName(build.name);
                    setIsEditingName(false);
                  }
                }}
                autoFocus
              />
              <NameValidationDropdown
                validation={nameValidation}
                onApplySuggestion={handleApplyNameSuggestion}
              />
            </div>
          ) : (
            <span
              className={`build-card-name ${isSelected && !readOnly ? 'editable' : ''}`}
              onClick={isSelected && !readOnly ? (e) => {
                e.stopPropagation();
                setIsEditingName(true);
              } : undefined}
              title={isSelected && !readOnly ? "Click to edit build name" : undefined}
            >
              {buildName}
            </span>
          )}

          {/* Current stage shown inline during building - hide in readOnly */}
          {!readOnly && isBuilding && currentStage && (
            <span className={`build-inline-stage ${stageAnimating ? 'animating' : ''}`}>
              {currentStage}
            </span>
          )}
        </div>

        <div className="build-header-right">
          {/* Indicators and buttons - hide in readOnly mode */}
          {!readOnly && (
            <>
              {/* Indicators wrapper */}
              <div className="build-indicators">
                {isBuilding && (
                  <span className="build-elapsed-time-inline">{formatBuildTime(elapsedTime)}</span>
                )}
                {!isBuilding && (
                  <>
                    {build.errors !== undefined && build.errors > 0 && (
                      <span
                        className="error-indicator clickable"
                        onClick={(e) => {
                          e.stopPropagation();
                          onStageFilter?.('', build.id, projectId);
                        }}
                        title="Click to filter problems for this build"
                      >
                        <AlertCircle size={12} />
                        <span>{build.errors}</span>
                      </span>
                    )}
                    {build.warnings !== undefined && build.warnings > 0 && (
                      <span
                        className="warning-indicator clickable"
                        onClick={(e) => {
                          e.stopPropagation();
                          onStageFilter?.('', build.id, projectId);
                        }}
                        title="Click to filter problems for this build"
                      >
                        <AlertTriangle size={12} />
                        <span>{build.warnings}</span>
                      </span>
                    )}

                    {build.duration ? (
                      <span className="build-duration">{build.duration.toFixed(1)}s</span>
                    ) : build.lastBuild ? (
                      <span className="last-build-info" title={`Last build: ${build.lastBuild.status}`}>
                        {getLastBuildStatusIcon(build.lastBuild.status, 10)}
                        <span className="last-build-time">{formatRelativeTime(build.lastBuild.timestamp)}</span>
                      </span>
                    ) : null}
                  </>
                )}
              </div>

              {/* Build play/cancel/delete button */}
              {isBuilding ? (
                <button
                  className="build-target-cancel-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (build.buildId && onCancelBuild) {
                      onCancelBuild(build.buildId);
                    }
                  }}
                  title={`Cancel build ${build.name}`}
                >
                  <Square size={10} fill="currentColor" />
                </button>
              ) : isSelected ? (
                <button
                  className="build-target-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowDeleteConfirm(true);
                  }}
                  title={`Delete build ${build.name}`}
                >
                  <Trash2 size={12} />
                </button>
              ) : (
                <button
                  className="build-target-play-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onBuild('build', `${projectId}:${build.id}`, build.name);
                  }}
                  title={`Build ${build.name}`}
                >
                  <Play size={12} />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Delete confirmation dialog - only in edit mode */}
      {!readOnly && showDeleteConfirm && (
        <div className="build-delete-confirm" onClick={(e) => e.stopPropagation()}>
          <span className="delete-confirm-text">Delete "{build.name}"?</span>
          <div className="delete-confirm-buttons">
            <button
              className="delete-confirm-btn cancel"
              onClick={() => setShowDeleteConfirm(false)}
            >
              Cancel
            </button>
            <button
              className="delete-confirm-btn confirm"
              onClick={() => {
                setShowDeleteConfirm(false);
                onDeleteBuild?.(projectId, build.id);
              }}
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {/* Build progress bar - only in edit mode */}
      {!readOnly && isBuilding && (
        <div className="build-progress-container">
          <div className="build-progress-bar">
            <div
              className="build-progress-fill"
              style={{ width: `${getProgress()}%` }}
            />
          </div>
        </div>
      )}

      {/* Expanded content - only when selected */}
      {isSelected && (
        <>
          {/* Entry point */}
          <div className="build-card-entry-row">
            <FileCode size={12} />
            {isEditingEntry ? (
              <div className="entry-picker" onClick={(e) => e.stopPropagation()}>
                <div className="entry-search-box">
                  <Search size={10} />
                  <input
                    ref={searchInputRef}
                    type="text"
                    className="entry-search-input"
                    value={searchQuery}
                    onChange={(e) => handleEntrySearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setSearchQuery('');
                        setIsEditingEntry(false);
                      }
                      if (e.key === 'Enter' && filteredModules.length === 1) {
                        handleSelectModule(filteredModules[0]);
                      }
                    }}
                    placeholder="Search modules..."
                  />
                  <button
                    className="entry-close-btn"
                    onClick={() => {
                      setSearchQuery('');
                      setIsEditingEntry(false);
                    }}
                  >
                    <X size={10} />
                  </button>
                </div>
                <div className="entry-dropdown">
                  {filteredModules.length > 0 ? (
                    filteredModules.map(module => (
                      <div
                        key={module.entry}
                        className={`entry-option ${module.entry === entryPoint ? 'selected' : ''}`}
                        onClick={() => handleSelectModule(module)}
                      >
                        <Box size={10} className={`module-type-icon ${module.type}`} />
                        <span className="entry-option-name">{module.name}</span>
                        <span className="entry-option-file">{module.file}</span>
                      </div>
                    ))
                  ) : availableModules.length === 0 ? (
                    <div className="entry-empty">
                      <span>No modules found in project</span>
                    </div>
                  ) : (
                    <div className="entry-empty">
                      <span>No matching modules for "{searchQuery}"</span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <span
                className="entry-path editable"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsEditingEntry(true);
                  setSearchQuery('');
                }}
                title="Click to change entry point"
              >
                {entryPoint}
              </span>
            )}
            {build.duration && (
              <span className="build-duration">
                <Clock size={10} />
                {build.duration.toFixed(1)}s
              </span>
            )}
          </div>

          {/* Build stages */}
          {hasStages && (
            <div className="build-stages-section">
              <button
                className="stages-toggle"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowStages(!showStages);
                }}
              >
                {showStages ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span>Build Stages</span>
                <span className="stages-summary">
                  {build.stages!.filter(s => s.status === 'success').length}/{build.stages!.length} complete
                </span>
              </button>

              {showStages && (
                <div className="build-stages-list">
                  {build.stages!.map((stage) => {
                    const isClickable = (stage.status === 'warning' || stage.status === 'error') && onStageFilter;
                    const stageDuration = stage.duration ?? stage.elapsedSeconds;
                    return (
                      <div
                        key={stage.name}
                        className={`stage-row ${stage.status} ${isClickable ? 'clickable' : ''}`}
                        onClick={isClickable ? (e) => {
                          e.stopPropagation();
                          onStageFilter(stage.name, build.id, projectId);
                        } : undefined}
                        title={isClickable ? `Filter problems to ${stage.displayName || stage.name} stage` : undefined}
                      >
                        {getStageIcon(stage.status)}
                        <span className="stage-name">{stage.displayName || stage.name}</span>
                        {stage.message && (
                          <span className="stage-message">{stage.message}</span>
                        )}
                        <span className="stage-duration">
                          {stage.status === 'running' ? (
                            <StageTimer />
                          ) : stageDuration != null ? (
                            `${stageDuration.toFixed(1)}s`
                          ) : (
                            ''
                          )}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="build-card-actions">
            <button
              className="build-action-btn primary"
              onClick={(e) => {
                e.stopPropagation();
                onBuild('build', `${projectId}:${build.id}`, build.name);
              }}
              title={`Build ${build.name}`}
            >
              <Play size={12} />
              <span>Build</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpenSource?.(projectId, build.entry);
              }}
              title="Open Source Code"
            >
              <FileCode size={12} />
              <span>ato</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpenKiCad?.(projectId, build.id);
              }}
              title="Open in KiCad"
            >
              <Grid3X3 size={12} />
              <span>KiCad</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpenLayout?.(projectId, build.id);
              }}
              title="Edit Layout"
            >
              <Layout size={12} />
              <span>Layout</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpen3D?.(projectId, build.id);
              }}
              title="3D Preview"
            >
              <Cuboid size={12} />
              <span>3D</span>
            </button>
          </div>

          {/* Entry point symbol */}
          {hasSymbols && build.symbols![0] && (
            <div className="build-card-symbols">
              <SymbolNode
                key={build.symbols![0].path}
                symbol={build.symbols![0]}
                depth={0}
                projectId={projectId}
                selection={selection}
                onSelect={onSelect}
                onBuild={onBuild}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
});
