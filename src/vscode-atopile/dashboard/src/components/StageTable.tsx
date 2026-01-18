/**
 * Stage table component showing build stages with timing and log access.
 */
import type { Build, BuildStage } from '../types/build';
import { StatusIcon } from './StatusBadge';
import { useBuildStore } from '../stores/buildStore';

interface StageTableProps {
  build: Build;
}

function formatTime(seconds: number): string {
  if (seconds < 0.01) {
    return '<0.01s';
  }
  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)}ms`;
  }
  return `${seconds.toFixed(2)}s`;
}

export function StageTable({ build }: StageTableProps) {
  const { selectedStage, selectStage, fetchLog } = useBuildStore();

  const stages = build.stages || [];

  if (stages.length === 0) {
    return (
      <div className="bg-panel-bg border border-panel-border rounded p-4">
        <h3 className="text-sm font-semibold text-text-muted mb-2">Stages</h3>
        <p className="text-text-muted text-sm">
          {build.status === 'building' ? 'Build in progress...' : 'No stage data available'}
        </p>
      </div>
    );
  }

  const handleStageClick = (stage: BuildStage) => {
    selectStage(stage.name);
    // Auto-load the log file if available
    if (stage.log_file) {
      fetchLog(build.name, stage);
    }
  };

  return (
    <div className="bg-panel-bg border border-panel-border rounded overflow-hidden">
      <div className="px-4 py-2 border-b border-panel-border">
        <h3 className="text-sm font-semibold text-text-muted">Stages</h3>
      </div>
      <div className="divide-y divide-panel-border">
        {stages.map((stage, index) => {
          const isSelected = selectedStage === stage.name;
          const hasLogs = !!stage.log_file;

          return (
            <button
              key={`${stage.name}-${index}`}
              onClick={() => handleStageClick(stage)}
              disabled={!hasLogs}
              className={`
                w-full flex items-center gap-3 px-4 py-2 text-left transition-colors
                ${isSelected ? 'bg-accent/10' : 'hover:bg-panel-border/30'}
                ${!hasLogs ? 'opacity-50 cursor-default' : 'cursor-pointer'}
              `}
            >
              <StatusIcon status={stage.status} className="flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-text-primary text-sm truncate block">{stage.name}</span>
              </div>
              <div className="flex items-center gap-3 text-xs">
                {stage.warnings > 0 && (
                  <span className="text-warning">{stage.warnings}W</span>
                )}
                {stage.errors > 0 && (
                  <span className="text-error">{stage.errors}E</span>
                )}
                <span className="w-16 text-right font-mono text-text-primary">{formatTime(stage.elapsed_seconds)}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
