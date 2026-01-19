/**
 * Combined build target item showing checkbox and build status.
 */

import { useState } from 'react';
import type { Build, BuildStage, BuildTarget } from '../types/build';
import { StatusIcon } from './StatusIcon';
import './BuildTargetItem.css';

interface BuildTargetItemProps {
  target: BuildTarget;
  build?: Build;
  isChecked: boolean;
  isSelected: boolean;
  selectedStageName: string | null;
  onToggle: () => void;
  onSelectStage: (stageName: string) => void;
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

function getCurrentStage(build: Build): string | null {
  if (!build.stages || build.stages.length === 0) return null;
  return build.stages[build.stages.length - 1].name;
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
  const time = formatTime(stage.elapsed_seconds);

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
  selectedStageName,
  onToggle,
  onSelectStage,
}: BuildTargetItemProps) {
  const [expanded, setExpanded] = useState(false);
  const hasStages = build?.stages && build.stages.length > 0;
  const currentStage = build ? getCurrentStage(build) : null;
  const timeStr = build ? formatTime(build.elapsed_seconds) : '';

  const handleExpandClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (hasStages) {
      setExpanded(!expanded);
    }
  };

  return (
    <div className={`build-target-item ${expanded ? 'expanded' : ''} ${isSelected ? 'selected' : ''}`}>
      <div className="build-target-header">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isChecked}
          onChange={onToggle}
          onClick={(e) => e.stopPropagation()}
        />

        {/* Status icon (if build exists) */}
        {build && (
          <div className="build-status">
            <StatusIcon status={build.status} size={16} />
          </div>
        )}

        {/* Target info */}
        <div className="build-target-info" onClick={handleExpandClick}>
          <span className="target-name">{target.name}</span>
          {build ? (
            <span className="build-meta">
              {currentStage && <span className="build-stage">{stripRichText(currentStage)}</span>}
              {currentStage && timeStr && <span className="meta-sep">·</span>}
              {timeStr && <span className="build-time">{timeStr}</span>}
            </span>
          ) : (
            <span className="target-entry">{target.entry}</span>
          )}
        </div>

        {/* Indicators */}
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

        {/* Expand chevron */}
        {hasStages && (
          <button className="expand-button" onClick={handleExpandClick}>
            <div className={`build-chevron ${expanded ? 'rotated' : ''}`}>
              <svg viewBox="0 0 16 16" fill="currentColor">
                <path d="M6 4l4 4-4 4" />
              </svg>
            </div>
          </button>
        )}
      </div>

      {/* Stages list */}
      {expanded && hasStages && (
        <div className="build-stages">
          {build!.stages!.map((stage) => (
            <StageItem
              key={stage.name}
              stage={stage}
              isSelected={isSelected && selectedStageName === stage.name}
              onSelect={() => onSelectStage(stage.name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
