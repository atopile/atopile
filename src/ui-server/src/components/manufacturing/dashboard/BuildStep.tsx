/**
 * BuildStep — Build trigger, progress, and artifact verification.
 * Three-panel layout: left (40%) build stages, right-top tips text,
 * right-bottom tips image placeholder.
 *
 * Left column: muster targets fetched from getMusterTargets, grouped by
 * category. Before build → checkboxes for selection. During/after build →
 * spinner / status icons driven by queuedBuilds stage data.
 *
 * Right column: tips & tricks (always visible).
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
import type { BuildOutputs, MusterTargetInfo } from '../types';
import { CATEGORY_CONFIG, DEFAULT_BUILD_TARGETS } from '../types';
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

export function BuildStep() {
  const dashboard = useStore((s) => s.manufacturingDashboard);
  const setDashboardBuildStatus = useStore((s) => s.setDashboardBuildStatus);
  const setDashboardOutputs = useStore((s) => s.setDashboardOutputs);
  const setDashboardArtifactVerification = useStore((s) => s.setDashboardArtifactVerification);
  const setDashboardStep = useStore((s) => s.setDashboardStep);
  const setDashboardReviewPage = useStore((s) => s.setDashboardReviewPage);
  const toggleDashboardBuildTarget = useStore((s) => s.toggleDashboardBuildTarget);
  const setDashboardBuildTargets = useStore((s) => s.setDashboardBuildTargets);
  const setAvailableBuildTargets = useStore((s) => s.setAvailableBuildTargets);
  const queuedBuilds = useStore((s) => s.queuedBuilds);

  const projectRoot = dashboard?.projectRoot ?? '';
  const targetName = dashboard?.targetName ?? '';
  const buildStatus = dashboard?.buildStatus ?? 'pending';
  const gitStatus = dashboard?.gitStatus;
  const outputs = dashboard?.outputs ?? null;
  const selectedBuildTargets = dashboard?.selectedBuildTargets ?? [...DEFAULT_BUILD_TARGETS];
  const availableBuildTargets = dashboard?.availableBuildTargets ?? [];

  // Track the buildId we're watching so we don't react to stale completed builds
  const trackedBuildIdRef = useRef<string | null>(null);

  // Fetch muster targets once dashboard is open, retrying until WS is ready
  useEffect(() => {
    if (!dashboard) return;
    let cancelled = false;

    function fetchTargets() {
      sendActionWithResponse('getMusterTargets', {}).then((res) => {
        if (cancelled) return;
        const r = res?.result as Record<string, unknown> | undefined;
        if (r?.success && Array.isArray(r.targets)) {
          setAvailableBuildTargets(r.targets as MusterTargetInfo[]);
        }
      }).catch(() => {
        if (!cancelled) setTimeout(fetchTargets, 1000);
      });
    }

    fetchTargets();
    return () => { cancelled = true; };
  }, [dashboard?.projectRoot, setAvailableBuildTargets]);

  // Find the matching build from queuedBuilds (same matching as sidebar)
  const activeBuild = queuedBuilds.find(
    (b) => b.projectRoot === projectRoot && b.target === targetName
  );

  // Sync dashboard buildStatus from queuedBuilds (same as sidebar)
  useEffect(() => {
    if (!activeBuild || !dashboard) return;
    const qbStatus = activeBuild.status;
    const buildId = activeBuild.buildId ?? null;

    if (qbStatus === 'building') {
      trackedBuildIdRef.current = buildId;
      if (buildStatus !== 'building') {
        setDashboardBuildStatus('building');
      }
    } else if (
      (qbStatus === 'success' || qbStatus === 'warning') &&
      buildStatus === 'building' &&
      trackedBuildIdRef.current !== null &&
      buildId === trackedBuildIdRef.current
    ) {
      trackedBuildIdRef.current = null;
      setDashboardBuildStatus('ready');
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
    const nonRequiredTargets = selectedBuildTargets.filter((t) => {
      const info = availableBuildTargets.find((a) => a.name === t);
      return info && info.category !== 'required';
    });
    sendAction('build', {
      projectRoot,
      targets: [targetName],
      includeTargets: nonRequiredTargets.length > 0 ? nonRequiredTargets : ['default'],
      frozen: true,
    });
  }, [projectRoot, targetName, setDashboardBuildStatus, selectedBuildTargets, availableBuildTargets]);

  const handleOpenSourceControl = useCallback(() => {
    postToExtension({ type: 'openSourceControl' });
  }, []);

  // Tips
  const tips = tipsData as TipItem[];
  const [tipIndex, setTipIndex] = useState(() => Math.floor(Math.random() * tips.length));
  const tip = tips[tipIndex];
  const handleNextTip = useCallback(() => {
    setTipIndex((i) => (i + 1) % tips.length);
  }, [tips.length]);

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

  // Group available targets by category
  const targetsByCategory = useMemo(() => {
    const grouped: Record<string, MusterTargetInfo[]> = {};
    for (const t of availableBuildTargets) {
      const cat = t.category ?? 'other';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(t);
    }
    return grouped;
  }, [availableBuildTargets]);

  const sortedCategories = useMemo(() => {
    return Object.keys(targetsByCategory).sort((a, b) => {
      const orderA = CATEGORY_CONFIG[a]?.order ?? 99;
      const orderB = CATEGORY_CONFIG[b]?.order ?? 99;
      return orderA - orderB;
    });
  }, [targetsByCategory]);

  // All non-required target names for "All" preset
  const allSelectableTargets = useMemo(() => {
    return availableBuildTargets
      .filter((t) => t.category !== 'required')
      .map((t) => t.name);
  }, [availableBuildTargets]);

  const handlePresetDefault = useCallback(() => {
    setDashboardBuildTargets([...DEFAULT_BUILD_TARGETS]);
  }, [setDashboardBuildTargets]);

  const handlePresetAll = useCallback(() => {
    setDashboardBuildTargets([...allSelectableTargets]);
  }, [setDashboardBuildTargets, allSelectableTargets]);

  if (!dashboard) return null;

  const isBuilding = buildStatus === 'building';
  const isFailed = buildStatus === 'failed';
  const isReady = buildStatus === 'ready' || buildStatus === 'confirmed';
  // Build a map from stage id → status from live queuedBuilds data
  const realStages = activeBuild?.stages ?? [];
  const stageStatusMap = useMemo(() => {
    const map: Record<string, { status: StepStatus; elapsed?: string }> = {};
    for (const stage of realStages) {
      const id = stage.stageId || stage.name;
      let status: StepStatus = 'pending';
      switch (stage.status) {
        case 'success': status = 'success'; break;
        case 'running': status = 'running'; break;
        case 'failed': case 'error': status = 'error'; break;
        case 'warning': status = 'warning'; break;
        default: status = 'pending';
      }
      map[id] = {
        status,
        elapsed: stage.elapsedSeconds ? `${stage.elapsedSeconds.toFixed(1)}s` : undefined,
      };
    }
    return map;
  }, [realStages]);

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

  // Determine whether a target is included in the current build
  // (either required, or user-selected)
  const isTargetIncluded = (t: MusterTargetInfo) => {
    if (t.category === 'required') return true;
    return selectedBuildTargets.includes(t.name);
  };

  // Whether we have an active or completed build (show status column)
  const hasBuildActivity = isBuilding || isReady || isFailed;

  // Render one target row — checkbox is always present, status icon + time
  // appear as extra columns on the right during/after a build.
  const renderTargetRow = (t: MusterTargetInfo, isRequired: boolean) => {
    const stageInfo = stageStatusMap[t.name];
    const hasLogs = !!activeBuild?.buildId;
    const included = isTargetIncluded(t);
    const status: StepStatus = stageInfo?.status ?? (isBuilding && included ? 'pending' : 'idle');
    const checkboxDisabled = isRequired || hasBuildActivity;

    return (
      <li
        key={t.name}
        className={`mfg-build-stage-item status-${status}${isRequired ? ' disabled' : ''}${hasLogs ? ' clickable' : ''}`}
        onClick={() => {
          if (hasLogs) {
            useStore.getState().setLogViewerBuildId(activeBuild!.buildId!);
            sendAction('setLogViewCurrentId', {
              buildId: activeBuild!.buildId!,
              stage: t.name,
            });
            postToExtension({ type: 'showBuildLogs' });
          }
        }}
        title={hasLogs ? `View logs for ${t.description || t.name}` : (t.description || t.name)}
      >
        <input
          type="checkbox"
          checked={isRequired || selectedBuildTargets.includes(t.name)}
          disabled={checkboxDisabled}
          onChange={() => { if (!isRequired && !hasBuildActivity) toggleDashboardBuildTarget(t.name); }}
          className="mfg-target-checkbox-input"
        />
        <span>{t.description || t.name}</span>
        <span className="mfg-stage-status-icon">{renderStageIcon(status)}</span>
        <span className="mfg-stage-elapsed">{stageInfo?.elapsed ?? ''}</span>
      </li>
    );
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
        {/* Left column: build targets list + pinned bottom actions */}
        <div className="mfg-build-grid-left">
          <div className="mfg-build-stages-scroll">
            {/* Header with preset buttons */}
            <div className="mfg-target-presets">
              <h3 className="mfg-build-section-title" style={{ margin: 0 }}>Build Targets</h3>
              {!hasBuildActivity && (
                <>
                  <button className="mfg-btn mfg-btn-tiny" onClick={handlePresetDefault}>Default</button>
                  <button className="mfg-btn mfg-btn-tiny" onClick={handlePresetAll}>All</button>
                </>
              )}
            </div>

            {/* Target list grouped by category */}
            {availableBuildTargets.length > 0 ? (
              sortedCategories.map((cat) => {
                const catConfig = CATEGORY_CONFIG[cat];
                const targets = targetsByCategory[cat];
                if (!catConfig || !targets) return null;
                const isRequired = catConfig.alwaysIncluded;
                if (targets.length === 0) return null;

                return (
                  <div key={cat} className="mfg-target-category">
                    <div className="mfg-target-category-title">{catConfig.label}</div>
                    <ul className="mfg-build-stages">
                      {targets.map((t) => renderTargetRow(t, isRequired))}
                    </ul>
                  </div>
                );
              })
            ) : (
              <ul className="mfg-build-stages">
                {isBuilding ? (
                  <li className="mfg-build-stage-item status-pending">
                    <Loader2 size={14} className="spinning" style={{ opacity: 0.4 }} />
                    <span>Starting build...</span>
                  </li>
                ) : (
                  <li className="mfg-build-stage-item status-idle">
                    <Circle size={14} style={{ opacity: 0.3 }} />
                    <span>Loading targets...</span>
                  </li>
                )}
              </ul>
            )}
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

        {/* Right column: tips & tricks (always visible) */}
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
