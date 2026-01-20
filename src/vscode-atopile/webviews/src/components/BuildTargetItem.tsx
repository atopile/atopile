/**
 * Build target item component - STATELESS.
 * Shows build stages for status display (not filtering).
 * Clicking the item selects the build for log viewing.
 */

import type { Build, BuildStage, BuildTarget } from '../types/build';
import { StatusIcon } from './StatusIcon';
import './BuildTargetItem.css';

interface BuildTargetItemProps {
  target: BuildTarget;
  build?: Build;
  isChecked: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  onToggle: () => void;
  onToggleExpand: () => void;
  onSelect: () => void;
  onOpenPcb: () => void;
}

function stripRichText(text: string): string {
  return text.replace(/\[\/?\w+\]/g, '').replace(/'/g, '');
}

function formatTime(seconds: number): string {
  if (seconds < 0.1) return '';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toFixed(0)}s`;
}

function formatTimestamp(isoString?: string): string {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    // Check if date is valid
    if (isNaN(date.getTime())) return '';

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    // For older builds, show the date
    return date.toLocaleDateString();
  } catch {
    return '';
  }
}

function getCurrentStage(build: Build): string | null {
  if (!build.stages || build.stages.length === 0) return null;
  return build.stages[build.stages.length - 1].name;
}

function StageItem({ stage }: { stage: BuildStage }) {
  return (
    <div className="stage-item">
      <StatusIcon status={stage.status} size={12} />
      <span className="stage-name">{stripRichText(stage.name)}</span>
      <div className="stage-stats">
        {stage.warnings > 0 && (
          <span className="stat warning">{stage.warnings}</span>
        )}
        {stage.errors > 0 && (
          <span className="stat error">{stage.errors}</span>
        )}
      </div>
    </div>
  );
}

export function BuildTargetItem({
  target,
  build,
  isChecked,
  isSelected,
  isExpanded,
  onToggle,
  onToggleExpand,
  onSelect,
  onOpenPcb,
}: BuildTargetItemProps) {
  const hasStages = build?.stages && build.stages.length > 0;
  const currentStage = build ? getCurrentStage(build) : null;
  const timeStr = build ? formatTime(build.elapsed_seconds) : '';

  // Clicking on the card header expands/collapses stages (if available) and selects the build
  const handleCardClick = (e: React.MouseEvent) => {
    // Don't expand if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('input')) {
      return;
    }

    // Select this build for log viewing
    onSelect();

    // Toggle expand if there are stages
    if (hasStages) {
      onToggleExpand();
    }
  };

  const handlePcbClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onOpenPcb();
  };

  return (
    <div
      className={`build-target-card ${isSelected ? 'selected' : ''} ${isExpanded ? 'expanded' : ''}`}
      onClick={handleCardClick}
    >
      {/* Card Header */}
      <div className="build-target-card-header">
        <input
          type="checkbox"
          checked={isChecked}
          onChange={onToggle}
          onClick={(e) => e.stopPropagation()}
        />

        {build && (
          <div className="build-status">
            <StatusIcon status={build.status} size={16} />
          </div>
        )}

        <div className="build-target-info">
          <span className="target-name">{target.name}</span>
          {build ? (
            <span className="build-meta">
              {currentStage && <span className="build-stage">{stripRichText(currentStage)}</span>}
              {currentStage && timeStr && <span className="meta-sep">·</span>}
              {timeStr && <span className="build-time">{timeStr}</span>}
              {(currentStage || timeStr) && <span className="meta-sep">·</span>}
              <span className="build-id" title={`Build ID: ${build.build_id}`}>{build.build_id.substring(0, 8)}</span>
              {formatTimestamp(build.timestamp) && (
                <>
                  <span className="meta-sep">·</span>
                  <span className="build-timestamp" title={build.timestamp}>{formatTimestamp(build.timestamp)}</span>
                </>
              )}
            </span>
          ) : (
            <span className="target-entry">{target.entry}</span>
          )}
        </div>

        {build && (
          <div className="build-indicators">
            {build.warnings > 0 && (
              <span className="indicator warning" title={`${build.warnings} warnings`}>
                {build.warnings}
              </span>
            )}
            {build.errors > 0 && (
              <span className="indicator error" title={`${build.errors} errors`}>
                {build.errors}
              </span>
            )}
          </div>
        )}

        {/* Expand chevron in header */}
        {hasStages && (
          <div className={`build-chevron ${isExpanded ? 'rotated' : ''}`}>
            <svg viewBox="0 0 16 16" fill="currentColor">
              <path d="M6 4l4 4-4 4" />
            </svg>
          </div>
        )}
      </div>

      {/* Card Actions */}
      <div className="build-target-card-actions">
        <button
          className="target-action-btn pcb-btn"
          onClick={handlePcbClick}
          title="Open PCB in KiCad"
        >
          <svg viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 2h12v12H2V2zm1 1v10h10V3H3zm2 2h2v2H5V5zm4 0h2v2H9V5zm-4 4h2v2H5V9zm4 0h2v2H9V9z" />
          </svg>
          <span>PCB</span>
        </button>
      </div>

      {/* Collapsible Stages Section */}
      {isExpanded && hasStages && (
        <div className="build-stages-section">
          <div className="build-stages">
            {build!.stages!.map((stage) => (
              <StageItem key={stage.stage_id} stage={stage} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
