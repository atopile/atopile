/**
 * Build target item component - STATELESS.
 * All state (including expanded) comes from props.
 */

import type { Build, BuildStage, BuildTarget, BuildTargetStageStatus } from '../types/build';
import { StatusIcon } from './StatusIcon';
import './BuildTargetItem.css';

interface BuildTargetItemProps {
  target: BuildTarget;
  build?: Build;
  isChecked: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  selectedStageIds: string[];
  onToggle: () => void;
  onToggleExpand: () => void;
  onToggleStage: (stageId: string) => void;
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

// Parse timestamp that may be in format "YYYY-MM-DD_HH-MM-SS" or ISO format
function parseTimestamp(timestamp: string): Date {
  // Handle format "2026-01-20_09-27-03" -> "2026-01-20T09:27:03"
  const normalized = timestamp.replace(/_/g, 'T').replace(/-(\d{2})-(\d{2})$/, ':$1:$2');
  return new Date(normalized);
}

function formatRelativeTime(timestamp: string): string {
  const date = parseTimestamp(timestamp);
  if (isNaN(date.getTime())) return '';  // Invalid date

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

function getCurrentStage(build: Build): string | null {
  if (!build.stages || build.stages.length === 0) return null;
  return build.stages[build.stages.length - 1].name;
}

// Historical stage item (read-only, no click handler)
function HistoricalStageItem({ stage }: { stage: BuildTargetStageStatus }) {
  const time = stage.elapsedSeconds ? formatTime(stage.elapsedSeconds) : '';

  return (
    <div className="stage-item historical">
      <StatusIcon status={stage.status} size={12} />
      <span className="stage-name">{stage.displayName || stage.name}</span>
      {time && <span className="stage-time">{time}</span>}
    </div>
  );
}

function StageItem({
  stage,
  isSelected,
  onSelect,
}: {
  stage: BuildStage;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const time = formatTime(stage.elapsedSeconds);

  return (
    <button
      className={`stage-item ${isSelected ? 'selected' : ''}`}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
    >
      <StatusIcon status={stage.status} size={12} />
      <span className="stage-name">{stripRichText(stage.name)}</span>
      {time && <span className="stage-time">{time}</span>}
      <div className="stage-stats">
        {stage.warnings > 0 && (
          <span className="stat warning">{stage.warnings}</span>
        )}
        {stage.errors > 0 && (
          <span className="stat error">{stage.errors}</span>
        )}
      </div>
    </button>
  );
}

export function BuildTargetItem({
  target,
  build,
  isChecked,
  isSelected,
  isExpanded,
  selectedStageIds,
  onToggle,
  onToggleExpand,
  onToggleStage,
}: BuildTargetItemProps) {
  const hasActiveStages = build?.stages && build.stages.length > 0;
  const hasHistoricalStages = !build && target.lastBuild?.stages && target.lastBuild.stages.length > 0;
  const hasStages = hasActiveStages || hasHistoricalStages;
  const currentStage = build ? getCurrentStage(build) : null;
  const timeStr = build ? formatTime(build.elapsedSeconds) : '';

  const handleExpandClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (hasStages) {
      onToggleExpand();
    }
  };

  return (
    <div className={`build-target-item ${isExpanded ? 'expanded' : ''} ${isSelected ? 'selected' : ''}`}>
      <div className="build-target-header">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isChecked}
          onChange={onToggle}
          onClick={(e) => e.stopPropagation()}
        />

        {/* Status icon - show active build status, or last build status if no active build */}
        {build ? (
          <div className="build-status">
            <StatusIcon status={build.status} size={16} />
          </div>
        ) : target.lastBuild ? (
          <div className="build-status last-build">
            <StatusIcon status={target.lastBuild.status} size={16} />
          </div>
        ) : null}

        {/* Target info */}
        <div className="build-target-info" onClick={handleExpandClick}>
          <span className="target-name">{target.name}</span>
          {build ? (
            <span className="build-meta">
              {currentStage && <span className="build-stage">{stripRichText(currentStage)}</span>}
              {currentStage && timeStr && <span className="meta-sep">·</span>}
              {timeStr && <span className="build-time">{timeStr}</span>}
            </span>
          ) : target.lastBuild ? (
            <span className="build-meta last-build-meta">
              <span className="last-build-time">{formatRelativeTime(target.lastBuild.timestamp)}</span>
            </span>
          ) : (
            <span className="target-entry">{target.entry}</span>
          )}
        </div>

        {/* Indicators - show for active build or last build */}
        {build ? (
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
        ) : target.lastBuild && (target.lastBuild.warnings > 0 || target.lastBuild.errors > 0) ? (
          <div className="build-indicators last-build-indicators">
            {target.lastBuild.warnings > 0 && (
              <span className="indicator warning" title={`${target.lastBuild.warnings} warnings`}>
                {target.lastBuild.warnings}
              </span>
            )}
            {target.lastBuild.errors > 0 && (
              <span className="indicator error" title={`${target.lastBuild.errors} errors`}>
                {target.lastBuild.errors}
              </span>
            )}
          </div>
        ) : null}

        {/* Expand chevron */}
        {hasStages && (
          <button className="expand-button" onClick={handleExpandClick}>
            <div className={`build-chevron ${isExpanded ? 'rotated' : ''}`}>
              <svg viewBox="0 0 16 16" fill="currentColor">
                <path d="M6 4l4 4-4 4" />
              </svg>
            </div>
          </button>
        )}
      </div>

      {/* Stages list - show active stages or historical stages */}
      {isExpanded && hasActiveStages && (
        <div className="build-stages">
          {build!.stages!.map((stage) => (
            <StageItem
              key={stage.stageId}
              stage={stage}
              isSelected={selectedStageIds.includes(stage.stageId)}
              onSelect={() => onToggleStage(stage.stageId)}
            />
          ))}
        </div>
      )}
      {isExpanded && hasHistoricalStages && (
        <div className="build-stages historical-stages">
          {target.lastBuild!.stages!.map((stage, idx) => (
            <HistoricalStageItem key={`${stage.name}-${idx}`} stage={stage} />
          ))}
        </div>
      )}
    </div>
  );
}
