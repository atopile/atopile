/**
 * Build summary component showing details for the selected build.
 */
import type { Build } from '../types/build';
import { StatusBadge } from './StatusBadge';

interface BuildSummaryProps {
  build: Build;
}

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toFixed(0)}s`;
}

export function BuildSummary({ build }: BuildSummaryProps) {
  return (
    <div className="bg-panel-bg border border-panel-border rounded p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-text-primary">{build.display_name}</h2>
        <StatusBadge status={build.status} showLabel />
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-text-muted">Elapsed:</span>
          <span className="text-text-primary ml-2">{formatTime(build.elapsed_seconds)}</span>
        </div>
        <div>
          <span className="text-text-muted">Return Code:</span>
          <span className={`ml-2 ${build.return_code === 0 ? 'text-success' : build.return_code === null ? 'text-text-muted' : 'text-error'}`}>
            {build.return_code ?? '-'}
          </span>
        </div>
        <div>
          <span className="text-text-muted">Warnings:</span>
          <span className={`ml-2 ${build.warnings > 0 ? 'text-warning' : 'text-text-primary'}`}>
            {build.warnings}
          </span>
        </div>
        <div>
          <span className="text-text-muted">Errors:</span>
          <span className={`ml-2 ${build.errors > 0 ? 'text-error' : 'text-text-primary'}`}>
            {build.errors}
          </span>
        </div>
      </div>

      {build.project_name && (
        <div className="mt-3 text-sm">
          <span className="text-text-muted">Project:</span>
          <span className="text-text-primary ml-2">{build.project_name}</span>
        </div>
      )}

      {build.stages && build.stages.length > 0 && (
        <div className="mt-3 text-sm text-text-muted">
          {build.stages.length} stage{build.stages.length !== 1 ? 's' : ''} completed
        </div>
      )}
    </div>
  );
}
