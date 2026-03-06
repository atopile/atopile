import { Check, Loader2, Package2, Square, XCircle } from 'lucide-react';
import type { AgentPackageWorker } from '../state/types';

interface PackageWorkersPanelProps {
  workers: AgentPackageWorker[];
}

function formatWorkerStatus(worker: AgentPackageWorker): string {
  if (worker.status === 'running' && worker.stopRequested) return 'Stopping';
  if (worker.status === 'running') return 'Running';
  if (worker.status === 'completed') return 'Completed';
  if (worker.status === 'stopped') return 'Stopped';
  return 'Failed';
}

function summarizeWorker(worker: AgentPackageWorker): string {
  if (worker.error) return worker.error;
  if (worker.activitySummary) return worker.activitySummary;
  if (worker.resultSummary) return worker.resultSummary;
  return worker.goal;
}

export function PackageWorkersPanel({ workers }: PackageWorkersPanelProps) {
  if (workers.length === 0) return null;

  return (
    <div className="agent-package-workers-panel">
      <div className="agent-package-workers-head">
        <span className="agent-package-workers-title">Package workers</span>
        <span className="agent-package-workers-meta">{workers.length}</span>
      </div>
      <div className="agent-package-workers-list">
        {workers.map((worker) => (
          <div key={worker.workerId} className={`agent-package-worker-card ${worker.status}`}>
            <div className="agent-package-worker-row">
              <div className="agent-package-worker-label">
                <Package2 size={12} />
                <span className="agent-package-worker-name">{worker.packageName}</span>
              </div>
              <span className={`agent-package-worker-status ${worker.status}`}>
                {worker.status === 'running' && <Loader2 size={11} className="agent-tool-spin" />}
                {worker.status === 'completed' && <Check size={11} />}
                {worker.status === 'stopped' && <Square size={10} />}
                {worker.status === 'failed' && <XCircle size={11} />}
                {formatWorkerStatus(worker)}
              </span>
            </div>
            <div className="agent-package-worker-path">{worker.packageProjectPath}</div>
            <div className="agent-package-worker-summary">{summarizeWorker(worker)}</div>
            <div className="agent-package-worker-meta-row">
              <span>{worker.changedFiles.length} files</span>
              <span>{worker.buildSummaries.length} builds</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
