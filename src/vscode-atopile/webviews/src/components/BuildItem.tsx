/**
 * Build item component with expanding card design.
 */

import { useState } from 'react';
import type { Build, BuildStage } from '../types/build';
import { StatusIcon } from './StatusIcon';
import './BuildItem.css';

interface BuildItemProps {
  build: Build;
  isSelected: boolean;
  selectedStageName: string | null;
  onSelectBuild: (name: string) => void;
  onSelectStage: (buildName: string, stageName: string) => void;
}

/**
 * Strip rich text markup like [green]text[/green] from stage names.
 */
function stripRichText(text: string): string {
  return text.replace(/\[\/?\w+\]/g, '').replace(/'/g, '');
}

function formatTime(seconds: number, showMs: boolean = false): string {
  if (seconds <= 0) return '';
  if (seconds < 0.001) return showMs ? '<1ms' : '';
  if (seconds < 0.1) return showMs ? `${Math.round(seconds * 1000)}ms` : '';
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
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
  // Show milliseconds for stage times (more granular)
  const time = formatTime(stage.elapsed_seconds, true);

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

export function BuildItem({
  build,
  isSelected,
  selectedStageName,
  onSelectBuild,
  onSelectStage,
}: BuildItemProps) {
  const [expanded, setExpanded] = useState(false);
  const hasStages = build.stages && build.stages.length > 0;
  const currentStage = getCurrentStage(build);
  const timeStr = formatTime(build.elapsed_seconds);

  const handleClick = () => {
    onSelectBuild(build.display_name);
    if (hasStages) {
      setExpanded(!expanded);
    }
  };

  return (
    <div className={`build-item ${expanded ? 'expanded' : ''} ${isSelected ? 'selected' : ''}`}>
      <button className="build-header" onClick={handleClick}>
        <div className="build-status">
          <StatusIcon status={build.status} size={16} />
        </div>

        <div className="build-info">
          <span className="build-name">{build.display_name}</span>
          <span className="build-meta">
            {currentStage && <span className="build-stage">{stripRichText(currentStage)}</span>}
            {currentStage && timeStr && <span className="meta-sep">·</span>}
            {timeStr && <span className="build-time">{timeStr}</span>}
          </span>
        </div>

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

        {hasStages && (
          <div className={`build-chevron ${expanded ? 'rotated' : ''}`}>
            <svg viewBox="0 0 16 16" fill="currentColor">
              <path d="M6 4l4 4-4 4" />
            </svg>
          </div>
        )}
      </button>

      {expanded && hasStages && (
        <div className="build-stages">
          {build.stages!.map((stage) => (
            <StageItem
              key={stage.name}
              stage={stage}
              isSelected={isSelected && selectedStageName === stage.name}
              onSelect={() => onSelectStage(build.display_name, stage.name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
