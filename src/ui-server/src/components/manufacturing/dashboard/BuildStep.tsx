/**
 * BuildStep — Build trigger, progress, and artifact verification.
 */

import { useCallback } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  Play,
  RefreshCw,
  ChevronRight,
} from 'lucide-react';
import { useStore } from '../../../store';
import { sendAction, sendActionWithResponse } from '../../../api/websocket';
import { postToExtension } from '../../../api/vscodeApi';
import type { BuildOutputs } from '../types';

export function BuildStep() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setDashboardBuildStatus = useStore((s) => s.setDashboardBuildStatus);
  const setDashboardOutputs = useStore((s) => s.setDashboardOutputs);
  const setDashboardArtifactVerification = useStore((s) => s.setDashboardArtifactVerification);
  const setDashboardStep = useStore((s) => s.setDashboardStep);
  const queuedBuilds = useStore((s) => s.queuedBuilds);

  if (!dashboard) return null;

  const { projectRoot, targetName, buildStatus, gitStatus, outputs, artifactVerification } = dashboard;

  const isBuilding = buildStatus === 'building';
  const isFailed = buildStatus === 'failed';
  const isReady = buildStatus === 'ready' || buildStatus === 'confirmed';

  const handleStartBuild = useCallback(() => {
    setDashboardBuildStatus('building');
    sendAction('triggerBuild', {
      projectRoot,
      targetNames: [targetName],
    });
  }, [projectRoot, targetName, setDashboardBuildStatus]);

  const handleOpenSourceControl = useCallback(() => {
    postToExtension({ type: 'openSourceControl' });
  }, []);

  // Watch for build completion via queued builds
  const activeBuild = queuedBuilds.find(
    (b) => b.target === targetName
  );

  // When build finishes, refresh outputs
  const handleRefreshOutputs = useCallback(async () => {
    const res = await sendActionWithResponse('getManufacturingOutputs', {
      projectRoot,
      target: targetName,
    });
    const r = res?.result as Record<string, unknown> | undefined;
    if (r?.success && r.outputs) {
      const o = r.outputs as BuildOutputs;
      setDashboardOutputs(o);
      setDashboardBuildStatus('ready');

      // Verify artifacts
      const verification: Record<string, boolean> = {
        gerbers: !!o.gerbers,
        bom: !!o.bomCsv || !!o.bomJson,
        pickAndPlace: !!o.pickAndPlace,
        model3d: !!o.glb || !!o.step,
      };
      setDashboardArtifactVerification(verification);
    }
  }, [projectRoot, targetName, setDashboardOutputs, setDashboardBuildStatus, setDashboardArtifactVerification]);

  return (
    <div className="mfg-build-step">
      <h2>Build Target</h2>

      {/* Git status warning */}
      {gitStatus?.hasUncommittedChanges && (
        <div className="mfg-git-warning">
          <AlertTriangle size={18} />
          <div>
            <strong>Uncommitted changes detected</strong>
            <p style={{ margin: '4px 0 0', fontSize: '12px' }}>
              You have {gitStatus.changedFiles.length} uncommitted file(s).
              Consider committing before building for manufacturing.
            </p>
            <button
              className="mfg-btn mfg-btn-secondary"
              onClick={handleOpenSourceControl}
              style={{ marginTop: 8 }}
            >
              Open Source Control
            </button>
          </div>
        </div>
      )}

      {/* Pre-build state */}
      {buildStatus === 'pending' && !outputs && (
        <div>
          <p style={{ fontSize: 13, color: 'var(--vscode-descriptionForeground)' }}>
            Build the project to generate manufacturing files.
          </p>
          <div className="mfg-build-actions">
            <button className="mfg-btn mfg-btn-primary" onClick={handleStartBuild}>
              <Play size={16} /> Start Build
            </button>
          </div>
        </div>
      )}

      {/* If outputs already exist but we haven't explicitly built */}
      {buildStatus === 'pending' && outputs && (
        <div>
          <p style={{ fontSize: 13, color: 'var(--vscode-descriptionForeground)' }}>
            Existing build outputs found. You can review them or rebuild.
          </p>
          <div className="mfg-build-actions">
            <button className="mfg-btn mfg-btn-primary" onClick={() => {
              setDashboardBuildStatus('ready');
              const verification: Record<string, boolean> = {
                gerbers: !!outputs.gerbers,
                bom: !!outputs.bomCsv || !!outputs.bomJson,
                pickAndPlace: !!outputs.pickAndPlace,
                model3d: !!outputs.glb || !!outputs.step,
              };
              setDashboardArtifactVerification(verification);
            }}>
              Use Existing Build
            </button>
            <button className="mfg-btn mfg-btn-secondary" onClick={handleStartBuild}>
              <RefreshCw size={14} /> Rebuild
            </button>
          </div>
        </div>
      )}

      {/* Building state */}
      {isBuilding && (
        <div>
          <p style={{ fontSize: 13 }}>
            <Loader2 size={14} className="spinning" style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Building {targetName}...
          </p>
          {activeBuild && (
            <ul className="mfg-build-stages">
              {activeBuild.stages?.map((stage) => (
                <li key={stage.stageId}>
                  {stage.status === 'running' && <Loader2 size={14} className="spinning" />}
                  {stage.status === 'success' && <CheckCircle2 size={14} style={{ color: 'var(--vscode-testing-iconPassed)' }} />}
                  {stage.status === 'error' && <AlertCircle size={14} style={{ color: 'var(--vscode-errorForeground)' }} />}
                  {stage.status === 'pending' && <Circle size={14} />}
                  {stage.name || stage.stageId}
                </li>
              )) ?? <li><Loader2 size={14} className="spinning" /> Waiting for stages...</li>}
            </ul>
          )}
          <button className="mfg-btn mfg-btn-secondary" onClick={handleRefreshOutputs} style={{ marginTop: 8 }}>
            Check for Outputs
          </button>
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <div>
          <p style={{ fontSize: 13, color: 'var(--vscode-errorForeground)' }}>
            <AlertCircle size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Build failed.
          </p>
          <div className="mfg-build-actions">
            <button className="mfg-btn mfg-btn-primary" onClick={handleStartBuild}>
              <RefreshCw size={14} /> Retry Build
            </button>
          </div>
        </div>
      )}

      {/* Ready state — show artifact verification */}
      {isReady && (
        <div>
          <p style={{ fontSize: 13, color: 'var(--vscode-testing-iconPassed)' }}>
            <CheckCircle2 size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Build complete. Artifacts verified:
          </p>
          <div className="mfg-artifacts">
            {Object.entries(artifactVerification).map(([key, available]) => (
              <div key={key} className={`mfg-artifact-item ${available ? 'available' : 'missing'}`}>
                {available ? <CheckCircle2 size={14} /> : <Circle size={14} />}
                <span style={{ textTransform: 'capitalize' }}>{key.replace(/([A-Z])/g, ' $1')}</span>
              </div>
            ))}
          </div>
          <div className="mfg-build-actions">
            <button className="mfg-btn mfg-btn-primary" onClick={() => setDashboardStep('review')}>
              Next: Review <ChevronRight size={14} />
            </button>
            <button className="mfg-btn mfg-btn-secondary" onClick={handleStartBuild}>
              <RefreshCw size={14} /> Rebuild
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
