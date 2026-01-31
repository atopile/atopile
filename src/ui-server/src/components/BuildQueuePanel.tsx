/**
 * BuildQueuePanel - Compact panel showing active and queued builds.
 * Displays build status, elapsed time, current stage, and cancel buttons.
 */

import { X, Clock, AlertCircle, CheckCircle2, XCircle, Pause, Circle } from 'lucide-react';
import './BuildQueuePanel.css';

export interface QueuedBuild {
  buildId: string;
  status: 'queued' | 'building' | 'success' | 'failed' | 'cancelled';
  projectRoot: string;
  target: string;
  entry?: string;
  startedAt: number;
  elapsedSeconds?: number;
  stages?: Array<{
    name: string;
    displayName?: string;
    status: string;
    elapsedSeconds?: number;
  }>;
  totalStages?: number | null;
  error?: string;
}

interface BuildQueuePanelProps {
  builds: QueuedBuild[];
  onCancelBuild: (buildId: string) => void;
}

// Format seconds to human readable duration
function formatDuration(seconds: number): string {
  if (seconds < 1) {
    return `${seconds.toFixed(2)}s`;
  }
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`;
  }
  if (seconds < 60) {
    return `${Math.floor(seconds)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins < 60) {
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return `${hours}h ${remainMins}m`;
}

// Extract project name from path
function getProjectName(projectRoot: string): string {
  const parts = projectRoot.split('/');
  return parts[parts.length - 1] || projectRoot;
}

// Get current stage info
function getCurrentStage(build: QueuedBuild): { name: string; elapsed?: number } | null {
  if (!build.stages || build.stages.length === 0) return null;

  // Find running stage first
  const running = build.stages.find(s => s.status === 'running');
  if (running) {
    return {
      name: running.displayName || running.name,
      elapsed: running.elapsedSeconds
    };
  }

  // Otherwise show last completed stage
  const completed = [...build.stages].reverse().find(s =>
    s.status === 'success' || s.status === 'failed' || s.status === 'error'
  );
  if (completed) {
    return { name: completed.displayName || completed.name };
  }

  return null;
}

function BuildQueueItem({ build, onCancel }: { build: QueuedBuild; onCancel: () => void }) {
  const elapsed = build.elapsedSeconds ?? 0;

  // Update elapsed time for building status

  const projectName = getProjectName(build.projectRoot);
  // Show target name, or entry for standalone builds
  const targetName = build.target || build.entry || 'default';
  const currentStage = getCurrentStage(build);

  const statusIcon = {
    queued: <Pause className="status-icon queued" size={12} />,
    building: <Circle className="status-icon building" size={12} />,
    success: <CheckCircle2 className="status-icon success" size={12} />,
    failed: <XCircle className="status-icon failed" size={12} />,
    cancelled: <AlertCircle className="status-icon cancelled" size={12} />,
  }[build.status];

  const isBuilding = build.status === 'building';

  const isActive = build.status === 'queued' || build.status === 'building';

  return (
    <div className={`queue-item ${build.status}`}>
      <div className="queue-item-main">
        {statusIcon}
        <div className="queue-item-info">
          <span className="queue-item-name" title={`${projectName}:${targetName}`}>
            {projectName}
            <span className="queue-item-target">:{targetName}</span>
          </span>
          {currentStage && build.status === 'building' && (
            <span className="queue-item-stage" title={currentStage.name}>
              {currentStage.name}
            </span>
          )}
        </div>
        <div className="queue-item-meta">
          {isActive && (
            <span className="queue-item-time">
              <Clock size={10} />
              {formatDuration(elapsed)}
            </span>
          )}
          {isActive && (
            <button
              className={`queue-item-cancel${isBuilding ? ' building' : ''}`}
              onClick={onCancel}
              title="Cancel build"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>
      {build.error && build.status === 'failed' && (
        <div className="queue-item-error" title={build.error}>
          {build.error.substring(0, 50)}...
        </div>
      )}
    </div>
  );
}

export function BuildQueuePanel({ builds, onCancelBuild }: BuildQueuePanelProps) {
  // STATELESS: Backend provides pre-filtered, pre-sorted queue data
  // Just render what we receive - no frontend logic needed

  if (builds.length === 0) {
    return (
      <div className="queue-empty">
        <span>No active builds</span>
      </div>
    );
  }

  return (
    <div className="build-queue-panel">
      {builds.map(build => (
        <BuildQueueItem
          key={build.buildId}
          build={build}
          onCancel={() => onCancelBuild(build.buildId)}
        />
      ))}
    </div>
  );
}
