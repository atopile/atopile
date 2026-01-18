/**
 * Build tabs component showing horizontal tabs for each build target.
 */
import type { Build } from '../types/build';
import { StatusIcon } from './StatusBadge';
import { useBuildStore } from '../stores/buildStore';

interface BuildTabsProps {
  builds: Build[];
}

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toFixed(0)}s`;
}

export function BuildTabs({ builds }: BuildTabsProps) {
  const { selectedBuild, selectBuild } = useBuildStore();

  return (
    <div className="flex items-center gap-1 px-2 py-1 overflow-x-auto">
      {builds.map((build) => {
        const isSelected = selectedBuild === build.display_name;
        return (
          <button
            key={build.display_name}
            onClick={() => selectBuild(build.display_name)}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded text-sm whitespace-nowrap transition-colors
              ${isSelected
                ? 'bg-accent/20 border border-accent/50 text-text-primary'
                : 'text-text-secondary hover:bg-panel-border/50 hover:text-text-primary'
              }
            `}
          >
            <StatusIcon status={build.status} />
            <span className="font-medium">{build.display_name}</span>
            <span className="text-xs text-text-muted">{formatTime(build.elapsed_seconds)}</span>
            {build.warnings > 0 && (
              <span className="text-xs text-warning">{build.warnings}W</span>
            )}
            {build.errors > 0 && (
              <span className="text-xs text-error">{build.errors}E</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
