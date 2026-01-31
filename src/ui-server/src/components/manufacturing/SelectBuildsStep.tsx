/**
 * SelectBuildsStep - Step 1 of the manufacturing wizard.
 * Allows user to select which build targets to include.
 * Shows uncommitted changes warning if applicable.
 */

import { useMemo } from 'react';
import { AlertTriangle, GitCommit, Check } from 'lucide-react';
import type { BuildTarget } from '../../types/build';
import type { ManufacturingBuild } from './types';

interface SelectBuildsStepProps {
  targets: BuildTarget[];
  selectedBuilds: ManufacturingBuild[];
  hasUncommittedChanges: boolean;
  uncommittedWarningDismissed: boolean;
  changedFiles: string[];
  isLoadingGitStatus: boolean;
  onToggleBuild: (targetName: string) => void;
  onDismissWarning: () => void;
  onCommitNow: () => void;
  onNext: () => void;
}

export function SelectBuildsStep({
  targets,
  selectedBuilds,
  hasUncommittedChanges,
  uncommittedWarningDismissed,
  changedFiles,
  isLoadingGitStatus,
  onToggleBuild,
  onDismissWarning,
  onCommitNow,
  onNext,
}: SelectBuildsStepProps) {
  const selectedTargetNames = useMemo(
    () => new Set(selectedBuilds.map((b) => b.targetName)),
    [selectedBuilds]
  );

  const canProceed = selectedBuilds.length > 0;
  const showWarning = hasUncommittedChanges && !uncommittedWarningDismissed;

  return (
    <div className="select-builds-step">
      {/* Uncommitted changes warning */}
      {showWarning && (
        <div className="uncommitted-warning">
          <div className="uncommitted-warning-icon">
            <AlertTriangle size={20} />
          </div>
          <div className="uncommitted-warning-content">
            <div className="uncommitted-warning-title">Uncommitted Changes</div>
            <div className="uncommitted-warning-text">
              You have {changedFiles.length} uncommitted file{changedFiles.length !== 1 ? 's' : ''}.
              Manufacturing files should be generated from a clean commit for reproducibility.
            </div>
            {changedFiles.length > 0 && changedFiles.length <= 5 && (
              <div className="uncommitted-files">
                {changedFiles.map((file) => (
                  <div key={file} className="uncommitted-file">{file}</div>
                ))}
              </div>
            )}
            {changedFiles.length > 5 && (
              <div className="uncommitted-files-overflow">
                and {changedFiles.length - 5} more files...
              </div>
            )}
          </div>
          <div className="uncommitted-warning-actions">
            <button
              className="warning-btn primary"
              onClick={onCommitNow}
            >
              <GitCommit size={14} />
              Commit Now
            </button>
            <button
              className="warning-btn secondary"
              onClick={onDismissWarning}
            >
              Continue Anyway
            </button>
          </div>
        </div>
      )}

      {/* Loading state for git status */}
      {isLoadingGitStatus && (
        <div className="git-status-loading">
          <span className="spinner" />
          <span>Checking for uncommitted changes...</span>
        </div>
      )}

      {/* Build targets list */}
      <div className="builds-selection">
        <div className="builds-selection-header">
          <span className="builds-selection-title">Select Builds</span>
          <span className="builds-selection-count">
            {selectedBuilds.length} of {targets.length} selected
          </span>
        </div>

        <div className="builds-list">
          {targets.length === 0 ? (
            <div className="builds-empty">
              No build targets defined in this project.
            </div>
          ) : (
            targets.map((target) => {
              const isSelected = selectedTargetNames.has(target.name);
              return (
                <div
                  key={target.name}
                  className={`build-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => onToggleBuild(target.name)}
                >
                  <div className={`build-checkbox ${isSelected ? 'checked' : ''}`}>
                    {isSelected && <Check size={12} />}
                  </div>
                  <div className="build-info">
                    <span className="build-name">{target.name}</span>
                    <span className="build-entry">{target.entry}</span>
                  </div>
                  {target.lastBuild && (
                    <div className={`build-last-status status-${target.lastBuild.status}`}>
                      {target.lastBuild.status}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Next button */}
      <div className="step-actions">
        <button
          className="step-btn primary"
          onClick={onNext}
          disabled={!canProceed}
        >
          Next: Build & Review
        </button>
      </div>
    </div>
  );
}
