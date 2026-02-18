/**
 * BuildStep — Build trigger, progress, and artifact verification.
 * Three-panel layout: left (40%) build stages, right-top tips text,
 * right-bottom tips image placeholder.
 *
 * Build stages are driven by the real backend stage data from queuedBuilds,
 * matching the same pattern used by the sidebar ManufacturingPanel.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
  AlertCircle,
  Play,
  RefreshCw,
  Lightbulb,
  ImageIcon,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { useStore } from '../../../store';
import { sendAction, sendActionWithResponse } from '../../../api/websocket';
import { postToExtension } from '../../../api/vscodeApi';
import { API_URL } from '../../../api/config';
import type { BuildOutputs } from '../types';
import { REVIEW_PAGES } from './reviewPages';
import MarkdownRenderer from '../../MarkdownRenderer';
import tipsData from '../../../../../../docs/tips_and_tricks/tips_and_tricks.json';

interface TipItem {
  title: string;
  text: string;
  image: string | null;
  link: string | null;
}

type StepStatus = 'idle' | 'pending' | 'running' | 'success' | 'warning' | 'error';

interface DisplayStep {
  id: string;
  label: string;
  status: StepStatus;
  elapsed?: string;
}

export function BuildStep() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setDashboardBuildStatus = useStore((s) => s.setDashboardBuildStatus);
  const setDashboardOutputs = useStore((s) => s.setDashboardOutputs);
  const setDashboardArtifactVerification = useStore((s) => s.setDashboardArtifactVerification);
  const setDashboardStep = useStore((s) => s.setDashboardStep);
  const setDashboardReviewPage = useStore((s) => s.setDashboardReviewPage);
  const queuedBuilds = useStore((s) => s.queuedBuilds);

  const projectRoot = dashboard?.projectRoot ?? '';
  const targetName = dashboard?.targetName ?? '';
  const buildStatus = dashboard?.buildStatus ?? 'pending';
  const gitStatus = dashboard?.gitStatus;
  const outputs = dashboard?.outputs ?? null;

  // Track the buildId we're watching so we don't react to stale completed builds
  const trackedBuildIdRef = useRef<string | null>(null);

  // Find the matching build from queuedBuilds (same matching as sidebar)
  const activeBuild = queuedBuilds.find(
    (b) => b.projectRoot === projectRoot && b.target === targetName
  );

  // Sync dashboard buildStatus from queuedBuilds (same as sidebar)
  useEffect(() => {
    if (!activeBuild || !dashboard) return;
    const qbStatus = activeBuild.status;
    const buildId = activeBuild.buildId ?? null;

    // When a build is actively building, start tracking it
    if (qbStatus === 'building') {
      trackedBuildIdRef.current = buildId;
      if (buildStatus !== 'building') {
        setDashboardBuildStatus('building');
      }
    } else if (
      (qbStatus === 'success' || qbStatus === 'warning') &&
      buildStatus === 'building' &&
      // Only transition to ready if this is the build we've been tracking
      trackedBuildIdRef.current !== null &&
      buildId === trackedBuildIdRef.current
    ) {
      trackedBuildIdRef.current = null;
      setDashboardBuildStatus('ready');
      // Fetch outputs when build completes
      sendActionWithResponse('getManufacturingOutputs', {
        projectRoot,
        target: targetName,
      }).then((res) => {
        const r = res?.result as Record<string, unknown> | undefined;
        if (r?.success && r.outputs) {
          const o = r.outputs as BuildOutputs;
          setDashboardOutputs(o);
          setDashboardArtifactVerification({
            gerbers: !!o.gerbers,
            bom: !!o.bomCsv || !!o.bomJson,
            pickAndPlace: !!o.pickAndPlace,
            model3d: !!o.glb || !!o.step,
          });
        }
      });
    } else if (
      qbStatus === 'failed' &&
      buildStatus !== 'failed' &&
      (trackedBuildIdRef.current === null || buildId === trackedBuildIdRef.current)
    ) {
      trackedBuildIdRef.current = null;
      setDashboardBuildStatus('failed');
    }
  }, [activeBuild?.status, activeBuild?.buildId, buildStatus, projectRoot, targetName, dashboard,
      setDashboardBuildStatus, setDashboardOutputs, setDashboardArtifactVerification]);

  const handleStartBuild = useCallback(() => {
    setDashboardBuildStatus('building');
    sendAction('build', {
      projectRoot,
      targets: [targetName],
      includeTargets: ['mfg-data'],
      frozen: true,
    });
  }, [projectRoot, targetName, setDashboardBuildStatus]);

  const handleOpenSourceControl = useCallback(() => {
    postToExtension({ type: 'openSourceControl' });
  }, []);


  // Pick a random tip, allow cycling with "Next"
  const tips = tipsData as TipItem[];
  const [tipIndex, setTipIndex] = useState(() => Math.floor(Math.random() * tips.length));
  const tip = tips[tipIndex];
  const handleNextTip = useCallback(() => {
    setTipIndex((i) => (i + 1) % tips.length);
  }, [tips.length]);

  // Resolve image URL: external URLs pass through, local paths use the backend file API
  const tipImageUrl = useMemo(() => {
    if (!tip.image) return null;
    if (tip.image.startsWith('http://') || tip.image.startsWith('https://')) {
      return tip.image;
    }
    if (!projectRoot) return null;
    const absPath = tip.image.startsWith('/')
      ? `${projectRoot}${tip.image}`
      : `${projectRoot}/${tip.image}`;
    return `${API_URL}/api/file?path=${encodeURIComponent(absPath)}`;
  }, [tip.image, projectRoot]);

  if (!dashboard) return null;

  const isBuilding = buildStatus === 'building';
  const isFailed = buildStatus === 'failed';
  const isReady = buildStatus === 'ready' || buildStatus === 'confirmed';

  // Build display steps from real backend stages (same as sidebar)
  const realStages = activeBuild?.stages ?? [];
  const displaySteps: DisplayStep[] = realStages.map((stage) => {
    let status: StepStatus = 'pending';
    switch (stage.status) {
      case 'success': status = 'success'; break;
      case 'running': status = 'running'; break;
      case 'failed': case 'error': status = 'error'; break;
      case 'warning': status = 'warning'; break;
      default: status = 'pending';
    }
    return {
      id: stage.stageId || stage.name,
      label: stage.displayName || stage.name,
      status,
      elapsed: stage.elapsedSeconds ? `${stage.elapsedSeconds.toFixed(1)}s` : undefined,
    };
  });

  // If no real stages yet but we're building, show a single "Building..." placeholder
  const showPlaceholder = isBuilding && displaySteps.length === 0;

  const renderStageIcon = (status: StepStatus) => {
    switch (status) {
      case 'running':
        return <Loader2 size={14} className="spinning" />;
      case 'success':
        return <CheckCircle2 size={14} style={{ color: 'var(--vscode-testing-iconPassed)' }} />;
      case 'warning':
        return <AlertTriangle size={14} style={{ color: 'var(--vscode-editorWarning-foreground)' }} />;
      case 'error':
        return <AlertCircle size={14} style={{ color: 'var(--vscode-errorForeground)' }} />;
      case 'pending':
        return <Loader2 size={14} className="spinning" style={{ opacity: 0.4 }} />;
      default:
        return <Circle size={14} style={{ opacity: 0.3 }} />;
    }
  };

  return (
    <div className="mfg-build-step">
      {/* Git status warning — full width above the grid */}
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

      {/* Three-panel grid */}
      <div className="mfg-build-grid">
        {/* Left column: build stages (scrollable) + pinned bottom actions */}
        <div className="mfg-build-grid-left">
          <div className="mfg-build-stages-scroll">
            <h3 className="mfg-build-section-title">Build Steps</h3>
            <ul className="mfg-build-stages">
              {displaySteps.map((step) => {
                const hasLogs = !!activeBuild?.buildId;
                return (
                  <li
                    key={step.id}
                    className={`mfg-build-stage-item status-${step.status}${hasLogs ? ' clickable' : ''}`}
                    onClick={() => {
                      if (activeBuild?.buildId) {
                        useStore.getState().setLogViewerBuildId(activeBuild.buildId);
                        sendAction('setLogViewCurrentId', {
                          buildId: activeBuild.buildId,
                          stage: step.id,
                        });
                        postToExtension({ type: 'showBuildLogs' });
                      }
                    }}
                    title={hasLogs ? `View logs for ${step.label}` : step.label}
                  >
                    {renderStageIcon(step.status)}
                    <span>{step.label}</span>
                    {step.elapsed && (
                      <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.5 }}>{step.elapsed}</span>
                    )}
                  </li>
                );
              })}
              {showPlaceholder && (
                <li className="mfg-build-stage-item status-pending">
                  <Loader2 size={14} className="spinning" style={{ opacity: 0.4 }} />
                  <span>Starting build...</span>
                </li>
              )}
              {!isBuilding && !isFailed && !isReady && displaySteps.length === 0 && (
                <li className="mfg-build-stage-item status-idle">
                  <Circle size={14} style={{ opacity: 0.3 }} />
                  <span>No build started</span>
                </li>
              )}
            </ul>
          </div>

          {/* Build actions — pinned to bottom */}
          <div className="mfg-build-actions">
            {buildStatus === 'pending' && !outputs && (
              <button className="mfg-btn mfg-btn-primary" onClick={handleStartBuild}>
                <Play size={16} /> Start Build
              </button>
            )}
            {buildStatus === 'pending' && outputs && (
              <>
                <button className="mfg-btn mfg-btn-primary" onClick={() => {
                  setDashboardBuildStatus('ready');
                  setDashboardArtifactVerification({
                    gerbers: !!outputs.gerbers,
                    bom: !!outputs.bomCsv || !!outputs.bomJson,
                    pickAndPlace: !!outputs.pickAndPlace,
                    model3d: !!outputs.glb || !!outputs.step,
                  });
                }}>
                  Use Existing Build
                </button>
                <button className="mfg-btn mfg-btn-secondary" onClick={handleStartBuild}>
                  <RefreshCw size={14} /> Rebuild
                </button>
              </>
            )}
            {isFailed && (
              <button className="mfg-btn mfg-btn-primary" onClick={handleStartBuild}>
                <RefreshCw size={14} /> Retry Build
              </button>
            )}
            {isBuilding && (
              <button className="mfg-btn mfg-btn-secondary" disabled>
                <Loader2 size={14} className="spinning" /> Building...
              </button>
            )}
            {isReady && (
              <>
                <button className="mfg-btn mfg-btn-secondary" onClick={handleStartBuild}>
                  <RefreshCw size={14} /> Rebuild
                </button>
                <button className="mfg-btn mfg-btn-primary" onClick={() => {
                  const firstPage = REVIEW_PAGES.find(
                    (p) => !outputs || p.definition.isAvailable(outputs)
                  );
                  if (firstPage) {
                    setDashboardReviewPage(firstPage.definition.id);
                  } else {
                    setDashboardStep('review');
                  }
                }}>
                  Start Review <ChevronRight size={14} />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Right column: two stacked rows */}
        <div className="mfg-build-grid-right">
          {/* Right-top: tips & tricks text */}
          <div className="mfg-build-grid-cell mfg-build-tips-text">
            <div className="mfg-tips-header">
              <Lightbulb size={16} />
              <span>{tip.title}</span>
              {tip.link && (
                <a
                  href={tip.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mfg-tips-link"
                  title="More info"
                >
                  <ExternalLink size={12} />
                </a>
              )}
              <button
                className="mfg-tips-next-btn"
                onClick={handleNextTip}
                title="Next tip"
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
            <div className="mfg-tips-body">
              <MarkdownRenderer content={tip.text} className="mfg-tips-markdown" />
            </div>
          </div>

          {/* Right-bottom: tips & tricks image */}
          <div className="mfg-build-grid-cell mfg-build-tips-image">
            {tipImageUrl ? (
              <img
                src={tipImageUrl}
                alt={tip.title}
                className="mfg-tips-image"
              />
            ) : (
              <div className="mfg-tips-image-placeholder">
                <ImageIcon size={32} style={{ opacity: 0.3 }} />
                <span style={{ fontSize: 12, opacity: 0.5 }}>No image available</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
