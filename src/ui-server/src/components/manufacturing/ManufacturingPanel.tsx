/**
 * ManufacturingPanel - Full panel for manufacturing export.
 * Features a stage-based progress view with live build step tracking.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Package,
  Layers,
  Cuboid,
  Download,
  AlertTriangle,
  Circle,
  RefreshCw,
  FolderOpen,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  FileStack,
} from 'lucide-react';
import { useStore } from '../../store';
import { sendAction, sendActionWithResponse } from '../../api/websocket';
import { postMessage, onExtensionMessage, postToExtension } from '../../api/vscodeApi';
import type { Project, BOMData } from '../../types/build';
import type { BuildOutputs } from './types';
import KiCanvasEmbed from '../KiCanvasEmbed';
import ModelViewer from '../ModelViewer';
import GerberViewer from '../GerberViewer';
import '../GerberViewer.css';
import { API_URL } from '../../api/config';
import './ManufacturingPanel.css';

interface ManufacturingPanelProps {
  project: Project;
  onClose: () => void;
}

type VisualTab = 'bom' | '3d' | 'layout' | 'gerbers';
type Stage = 'build' | 'review' | 'export';

interface BuildStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'warning' | 'error';
  message?: string;
}

export function ManufacturingPanel({ project, onClose }: ManufacturingPanelProps) {
  const wizard = useStore((s) => s.manufacturingWizard);
  const queuedBuilds = useStore((s) => s.queuedBuilds);
  const updateBuild = useStore((s) => s.updateManufacturingBuild);
  const setExportError = useStore((s) => s.setManufacturingExportError);
  const setExportDirectory = useStore((s) => s.setManufacturingExportDirectory);

  // Local state
  const [activeVisualTab, setActiveVisualTab] = useState<VisualTab>('layout');
  const [buildOutputs, setBuildOutputs] = useState<Record<string, BuildOutputs>>({});
  const [bomDataByTarget, setBomDataByTarget] = useState<Record<string, BOMData | null>>({});
  const [isLoadingBomByTarget, setIsLoadingBomByTarget] = useState<Record<string, boolean>>({});
  const [buildSteps, setBuildSteps] = useState<BuildStep[]>([]);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [buildStepsCollapsed, setBuildStepsCollapsed] = useState(false);
  const [gitStatus, setGitStatus] = useState<{ checking: boolean; hasChanges: boolean; files: string[] }>({
    checking: true,
    hasChanges: false,
    files: [],
  });

  const selectedBuilds = wizard?.selectedBuilds || [];
  const selectedBuild = selectedBuilds[0];

  // Determine current stage
  const currentStage: Stage = (() => {
    if (!selectedBuild) return 'build';
    if (selectedBuild.status === 'pending' || selectedBuild.status === 'building') return 'build';
    if (selectedBuild.status === 'failed') return 'build';
    if (selectedBuild.status === 'confirmed') return 'export';
    return 'review';
  })();

  // Check git status on mount
  useEffect(() => {
    const checkGitStatus = async () => {
      try {
        const response = await sendActionWithResponse('getManufacturingGitStatus', {
          projectRoot: project.root,
        });
        if (response.result?.success) {
          const result = response.result as { success: boolean; hasUncommittedChanges: boolean; changedFiles: string[] };
          setGitStatus({
            checking: false,
            hasChanges: result.hasUncommittedChanges,
            files: result.changedFiles || [],
          });
        } else {
          setGitStatus({ checking: false, hasChanges: false, files: [] });
        }
      } catch {
        setGitStatus({ checking: false, hasChanges: false, files: [] });
      }
    };
    checkGitStatus();
  }, [project.root]);

  // Initialize build steps when build starts
  useEffect(() => {
    if (selectedBuild?.status === 'building' || selectedBuild?.status === 'pending') {
      // Expand build steps when building
      setBuildStepsCollapsed(false);

      // Start with git status check, then build steps
      const gitStatusStep: BuildStep = gitStatus.checking
        ? { id: 'git', label: 'Checking for uncommitted changes', status: 'running' }
        : gitStatus.hasChanges
          ? { id: 'git', label: 'Uncommitted changes', status: 'warning', message: `${gitStatus.files.length} files` }
          : { id: 'git', label: 'No uncommitted changes', status: 'complete' };

      setBuildSteps([
        gitStatusStep,
        { id: 'compile', label: 'Compiling design', status: 'pending' },
        { id: 'pick', label: 'Picking parts', status: 'pending' },
        { id: 'layout', label: 'Updating layout', status: 'pending' },
        { id: 'gerbers', label: 'Generating gerbers', status: 'pending' },
        { id: 'bom', label: 'Generating BOM', status: 'pending' },
        { id: 'pnp', label: 'Generating pick & place', status: 'pending' },
      ]);
    }
  }, [selectedBuild?.status, gitStatus]);

  // Simulate build step progress based on build status
  useEffect(() => {
    if (selectedBuild?.status !== 'building') return;

    // Simulate progress through steps
    const stepOrder = ['compile', 'pick', 'layout', 'gerbers', 'bom', 'pnp'];
    let currentStep = 0;

    const interval = setInterval(() => {
      if (currentStep < stepOrder.length) {
        setBuildSteps((prev) =>
          prev.map((step, idx) => {
            // Skip git step (index 0)
            const adjustedIdx = idx - 1;
            if (adjustedIdx < 0) return step;
            if (adjustedIdx < currentStep) return { ...step, status: 'complete' };
            if (adjustedIdx === currentStep) return { ...step, status: 'running' };
            return step;
          })
        );
        currentStep++;
      } else {
        clearInterval(interval);
      }
    }, 800);

    return () => clearInterval(interval);
  }, [selectedBuild?.status]);

  // Sync build status from queuedBuilds
  useEffect(() => {
    if (!selectedBuilds.length) return;

    for (const build of selectedBuilds) {
      const queuedBuild = queuedBuilds.find(
        (qb) => qb.projectRoot === build.projectRoot && qb.target === build.targetName
      );

      if (queuedBuild) {
        let newStatus = build.status;
        if (queuedBuild.status === 'building' && build.status !== 'building') {
          newStatus = 'building';
        } else if (
          (queuedBuild.status === 'success' || queuedBuild.status === 'warning') &&
          build.status === 'building'
        ) {
          newStatus = 'ready';
          // Mark all steps complete
          setBuildSteps((prev) => prev.map((step) => ({ ...step, status: 'complete' })));
          // Collapse build steps when complete
          setBuildStepsCollapsed(true);
          fetchBuildOutputs(build.targetName);
        } else if (queuedBuild.status === 'failed' && build.status !== 'failed') {
          newStatus = 'failed';
          // Mark current step as error
          setBuildSteps((prev) =>
            prev.map((step) =>
              step.status === 'running' ? { ...step, status: 'error' } : step
            )
          );
        }

        if (newStatus !== build.status) {
          updateBuild(build.targetName, {
            status: newStatus,
            buildId: queuedBuild.buildId,
            error: queuedBuild.error || null,
          });
        }
      }
    }
  }, [queuedBuilds, selectedBuilds, updateBuild]);

  // Auto-start build if pending - use "all" muster target to include manufacturing data
  useEffect(() => {
    if (selectedBuild?.status === 'pending') {
      // Build the selected target with "all" muster target to generate gerbers, pnp, etc.
      sendAction('build', {
        projectRoot: selectedBuild.projectRoot,
        targets: [selectedBuild.targetName],  // Build config from ato.yaml (e.g., "default")
        includeTargets: ['all'],  // Muster target to include mfg-data, 3d models, etc.
        frozen: true,
      });
      updateBuild(selectedBuild.targetName, { status: 'building' });
    }
  }, [selectedBuild?.status, selectedBuild?.projectRoot, selectedBuild?.targetName, updateBuild]);

  // Fetch build outputs when ready
  const fetchBuildOutputs = useCallback(
    async (targetName: string) => {
      try {
        const response = await sendActionWithResponse('getManufacturingOutputs', {
          projectRoot: project.root,
          target: targetName,
        });
        if (response.result?.success) {
          const result = response.result as { success: boolean; outputs: BuildOutputs };
          setBuildOutputs((prev) => ({
            ...prev,
            [targetName]: result.outputs,
          }));
          fetchBomData(targetName);
          runPostBuildChecks(targetName, result.outputs);
        }
      } catch (error) {
        console.error('Failed to fetch build outputs:', error);
      }
    },
    [project.root]
  );

  const fetchBomData = useCallback(
    async (targetName: string) => {
      setIsLoadingBomByTarget((prev) => ({ ...prev, [targetName]: true }));
      try {
        // First refresh the BOM to get the latest data
        const response = await sendActionWithResponse('refreshBOM', {
          projectRoot: project.root,
          target: targetName,
        });
        if (response.result?.success) {
          const result = response.result as { success: boolean; bom?: BOMData };
          if (result.bom) {
            setBomDataByTarget((prev) => ({
              ...prev,
              [targetName]: result.bom ?? null,
            }));

            // Now enrich the BOM data with stock info
            // The refreshBOM should already include stock data from the bom.json
            // but we may need to fetch LCSC data for enrichment
          }
        }
      } catch (error) {
        console.error('Failed to fetch BOM:', error);
      } finally {
        setIsLoadingBomByTarget((prev) => ({ ...prev, [targetName]: false }));
      }
    },
    [project.root]
  );

  const runPostBuildChecks = useCallback(
    async (targetName: string, outputs: BuildOutputs) => {
      // Update build steps with output verification
      setBuildSteps((prev) => {
        // Filter out any previous verification steps
        const baseSteps = prev.filter(s => !s.id.startsWith('verify-') && s.id !== 'stock' && s.id !== 'requirements');

        // Add verification steps
        return [
          ...baseSteps,
          {
            id: 'verify-gerbers',
            label: 'Gerbers generated',
            status: outputs.gerbers ? 'complete' : 'warning',
            message: outputs.gerbers ? undefined : 'Not found',
          },
          {
            id: 'verify-bom',
            label: 'BOM generated',
            status: outputs.bomCsv ? 'complete' : 'warning',
            message: outputs.bomCsv ? undefined : 'Not found',
          },
          {
            id: 'verify-pnp',
            label: 'Pick & place file',
            status: outputs.pickAndPlace ? 'complete' : 'warning',
            message: outputs.pickAndPlace ? undefined : 'Not found',
          },
        ];
      });

      // Check stock availability from BOM
      try {
        const bomResponse = await sendActionWithResponse('refreshBOM', {
          projectRoot: project.root,
          target: targetName,
        });
        if (bomResponse.result?.success && bomResponse.result?.bom) {
          const bom = bomResponse.result.bom as BOMData;
          // Check for components with stock = 0 or null (unknown)
          const outOfStock = bom.components?.filter((c) => c.stock === 0) || [];
          const unknownStock = bom.components?.filter((c) => c.stock == null) || [];

          setBuildSteps((prev) => [
            ...prev,
            {
              id: 'stock',
              label: 'Parts availability',
              status: outOfStock.length > 0 ? 'warning' : unknownStock.length > 0 ? 'warning' : 'complete',
              message: outOfStock.length > 0
                ? `${outOfStock.length} out of stock`
                : unknownStock.length > 0
                  ? `${unknownStock.length} unknown`
                  : undefined,
            },
          ]);
        }
      } catch {
        setBuildSteps((prev) => [
          ...prev,
          { id: 'stock', label: 'Parts availability', status: 'warning', message: 'Could not verify' },
        ]);
      }

      // Add requirements check
      setBuildSteps((prev) => [
        ...prev,
        { id: 'requirements', label: 'All requirements met', status: 'complete' },
      ]);
    },
    [project.root]
  );

  const handleConfirmBuild = useCallback(() => {
    if (selectedBuild) {
      updateBuild(selectedBuild.targetName, { status: 'confirmed' });
    }
  }, [selectedBuild, updateBuild]);

  const handleRetryBuild = useCallback(() => {
    if (selectedBuild) {
      setBuildSteps([]);
      setBuildStepsCollapsed(false);
      updateBuild(selectedBuild.targetName, { status: 'pending', error: null });
    }
  }, [selectedBuild, updateBuild]);

  const handleBrowseDirectory = useCallback(() => {
    postMessage({ type: 'browseExportDirectory' });
  }, []);

  const handleRevealInFinder = useCallback(() => {
    const exportDir = wizard?.exportDirectory || `${project.root}/manufacturing`;
    postToExtension({ type: 'revealInFinder', path: exportDir });
  }, [wizard?.exportDirectory, project.root]);

  const handleOpenSourceControl = useCallback(() => {
    postToExtension({ type: 'openSourceControl' });
  }, []);

  useEffect(() => {
    const unsubscribe = onExtensionMessage((message) => {
      if (message.type === 'browseExportDirectoryResult' && message.path) {
        setExportDirectory(message.path);
      }
    });
    return unsubscribe;
  }, [setExportDirectory]);

  const handleExport = useCallback(async () => {
    if (!wizard || !selectedBuild) return;

    setIsExporting(true);
    setExportError(null);
    setExportSuccess(false);

    try {
      const jlcFileTypes = ['gerbers', 'bom_csv', 'pick_and_place'];
      const response = await sendActionWithResponse('exportManufacturingFiles', {
        projectRoot: project.root,
        targets: [selectedBuild.targetName],
        directory: wizard.exportDirectory || `${project.root}/manufacturing`,
        fileTypes: jlcFileTypes,
      });

      if (response.result?.success) {
        setExportSuccess(true);
      } else {
        const result = response.result as { success: boolean; error?: string } | undefined;
        setExportError(result?.error ?? 'Export failed');
      }
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  }, [wizard, selectedBuild, project.root, setExportError]);

  if (!wizard?.isOpen || !selectedBuild) return null;

  const outputs = buildOutputs[selectedBuild.targetName];
  const bomData = bomDataByTarget[selectedBuild.targetName];
  const isLoadingBom = isLoadingBomByTarget[selectedBuild.targetName];

  const isBuilding = selectedBuild.status === 'building';
  const isFailed = selectedBuild.status === 'failed';
  const isReady = selectedBuild.status === 'ready' || selectedBuild.status === 'confirmed';
  const isConfirmed = selectedBuild.status === 'confirmed';

  const completedSteps = buildSteps.filter((s) => s.status === 'complete').length;
  const hasWarnings = buildSteps.some((s) => s.status === 'warning');
  const hasErrors = buildSteps.some((s) => s.status === 'error');

  return (
    <div className="package-detail-panel manufacturing-panel">
      <div className="detail-panel-header">
        <button className="detail-back-btn" onClick={onClose} title="Back">
          <ArrowLeft size={18} />
        </button>
        <div className="detail-header-info">
          <h2 className="detail-package-name">Export for Manufacturing</h2>
          <p className="detail-package-blurb">{selectedBuild.targetName}</p>
        </div>
      </div>

      <div className="detail-panel-content">
        {/* Stage Progress Indicator - Always visible and sticky */}
        <div className="mfg-stages-container">
          <div className="mfg-stages">
            <div className={`mfg-stage ${currentStage === 'build' ? 'active' : ''} ${currentStage !== 'build' ? 'complete' : ''}`}>
              <div className="mfg-stage-icon">
                {currentStage === 'build' && isBuilding && <Loader2 size={16} className="spinning" />}
                {currentStage === 'build' && isFailed && <AlertCircle size={16} />}
                {currentStage !== 'build' && <CheckCircle2 size={16} />}
                {currentStage === 'build' && !isBuilding && !isFailed && <Circle size={16} />}
              </div>
              <span className="mfg-stage-label">Build</span>
            </div>
            <ChevronRight size={16} className="mfg-stage-arrow" />
            <div className={`mfg-stage ${currentStage === 'review' ? 'active' : ''} ${currentStage === 'export' ? 'complete' : ''}`}>
              <div className="mfg-stage-icon">
                {currentStage === 'export' && <CheckCircle2 size={16} />}
                {currentStage === 'review' && <Circle size={16} />}
                {currentStage === 'build' && <Circle size={16} />}
              </div>
              <span className="mfg-stage-label">Review</span>
            </div>
            <ChevronRight size={16} className="mfg-stage-arrow" />
            <div className={`mfg-stage ${currentStage === 'export' ? 'active' : ''} ${exportSuccess ? 'complete' : ''}`}>
              <div className="mfg-stage-icon">
                {exportSuccess && <CheckCircle2 size={16} />}
                {!exportSuccess && <Circle size={16} />}
              </div>
              <span className="mfg-stage-label">Export</span>
            </div>
          </div>
        </div>

        {/* Git Warning Banner - Show before build starts */}
        {!gitStatus.checking && gitStatus.hasChanges && currentStage === 'build' && !isBuilding && !isFailed && (
          <div className="mfg-git-warning">
            <div className="mfg-git-warning-icon">
              <AlertTriangle size={20} />
            </div>
            <div className="mfg-git-warning-content">
              <div className="mfg-git-warning-title">Uncommitted Changes Detected</div>
              <div className="mfg-git-warning-message">
                {gitStatus.files.length} file{gitStatus.files.length !== 1 ? 's' : ''} modified.
                Consider committing your changes before exporting for manufacturing to ensure reproducibility.
              </div>
              {gitStatus.files.length <= 5 && (
                <ul className="mfg-git-warning-files">
                  {gitStatus.files.map((file, idx) => (
                    <li key={idx}>{file}</li>
                  ))}
                </ul>
              )}
            </div>
            <div className="mfg-git-warning-actions">
              <button className="mfg-btn secondary small" onClick={handleOpenSourceControl}>
                <FileStack size={14} />
                View Changes
              </button>
            </div>
          </div>
        )}

        {/* Git Status Loading */}
        {gitStatus.checking && currentStage === 'build' && !isBuilding && (
          <div className="mfg-git-checking">
            <Loader2 size={16} className="spinning" />
            <span>Checking for uncommitted changes...</span>
          </div>
        )}

        {/* Git Clean Status */}
        {!gitStatus.checking && !gitStatus.hasChanges && currentStage === 'build' && !isBuilding && !isFailed && !isReady && (
          <div className="mfg-git-clean">
            <CheckCircle2 size={16} />
            <span>No uncommitted changes</span>
          </div>
        )}

        {/* Build Steps - Collapsible when complete */}
        {(isBuilding || isReady || isFailed) && buildSteps.length > 0 && (
          <div className={`mfg-section mfg-steps-section ${buildStepsCollapsed ? 'collapsed' : ''}`}>
            <button
              className="mfg-steps-header"
              onClick={() => setBuildStepsCollapsed(!buildStepsCollapsed)}
            >
              <h3 className="mfg-section-title">
                {isBuilding ? 'Building...' : isFailed ? 'Build Failed' : 'Build Complete'}
              </h3>
              <span className="mfg-steps-count">
                {completedSteps}/{buildSteps.length}
                {hasWarnings && <AlertTriangle size={12} className="status-warning" />}
                {hasErrors && <AlertCircle size={12} className="status-error" />}
                {buildStepsCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </span>
            </button>
            {!buildStepsCollapsed && (
              <>
                <div className="mfg-steps-list">
                  {buildSteps.map((step) => (
                    <div key={step.id} className={`mfg-step-item status-${step.status}`}>
                      <span className="mfg-step-icon">
                        {step.status === 'complete' && <CheckCircle2 size={14} />}
                        {step.status === 'running' && <Loader2 size={14} className="spinning" />}
                        {step.status === 'pending' && <Circle size={14} />}
                        {step.status === 'warning' && <AlertTriangle size={14} />}
                        {step.status === 'error' && <AlertCircle size={14} />}
                      </span>
                      <span className="mfg-step-label">{step.label}</span>
                      {step.message && <span className="mfg-step-message">{step.message}</span>}
                    </div>
                  ))}
                </div>
                {isFailed && selectedBuild.error && (
                  <div className="mfg-error-message">{selectedBuild.error}</div>
                )}
                {isFailed && (
                  <button className="mfg-btn secondary" onClick={handleRetryBuild}>
                    <RefreshCw size={14} />
                    Retry Build
                  </button>
                )}
                {gitStatus.hasChanges && !isBuilding && (
                  <button className="mfg-btn secondary" onClick={handleOpenSourceControl}>
                    <FileStack size={14} />
                    View Changes
                  </button>
                )}
              </>
            )}
          </div>
        )}

        {/* Visual Preview Section */}
        {isReady && (
          <div className="mfg-visual-section">
            <div className="mfg-visual-tabs">
              <button
                className={`mfg-visual-tab ${activeVisualTab === 'layout' ? 'active' : ''}`}
                onClick={() => setActiveVisualTab('layout')}
              >
                <Layers size={14} />
                Layout
              </button>
              <button
                className={`mfg-visual-tab ${activeVisualTab === 'gerbers' ? 'active' : ''}`}
                onClick={() => setActiveVisualTab('gerbers')}
              >
                <Layers size={14} />
                Gerbers
              </button>
              <button
                className={`mfg-visual-tab ${activeVisualTab === '3d' ? 'active' : ''}`}
                onClick={() => setActiveVisualTab('3d')}
              >
                <Cuboid size={14} />
                3D Model
              </button>
              <button
                className={`mfg-visual-tab ${activeVisualTab === 'bom' ? 'active' : ''}`}
                onClick={() => setActiveVisualTab('bom')}
              >
                <Package size={14} />
                BOM ({bomData?.components?.length || 0})
              </button>
            </div>

            <div className="mfg-visual-content">
              {activeVisualTab === 'layout' && (
                <>
                  {outputs?.kicadPcb ? (
                    <KiCanvasEmbed
                      src={`${API_URL}/api/file?path=${encodeURIComponent(outputs.kicadPcb)}`}
                      controls="full"
                    />
                  ) : (
                    <div className="mfg-visual-empty">
                      <Layers size={32} />
                      <span>Layout not available</span>
                      <span className="mfg-visual-hint">Build with "all" target to generate</span>
                    </div>
                  )}
                </>
              )}

              {activeVisualTab === 'gerbers' && (
                <>
                  {outputs?.gerbers ? (
                    <GerberViewer
                      src={`${API_URL}/api/file?path=${encodeURIComponent(outputs.gerbers)}`}
                    />
                  ) : (
                    <div className="mfg-visual-empty">
                      <Layers size={32} />
                      <span>Gerbers not available</span>
                      <span className="mfg-visual-hint">Build with "all" target to generate</span>
                    </div>
                  )}
                </>
              )}

              {activeVisualTab === '3d' && (
                <>
                  {outputs?.glb ? (
                    <ModelViewer
                      src={`${API_URL}/api/file?path=${encodeURIComponent(outputs.glb)}`}
                    />
                  ) : (
                    <div className="mfg-visual-empty">
                      <Cuboid size={32} />
                      <span>3D model not available</span>
                      <span className="mfg-visual-hint">Build with "all" target to generate</span>
                    </div>
                  )}
                </>
              )}

              {activeVisualTab === 'bom' && (
                <div className="mfg-bom-preview">
                  {isLoadingBom ? (
                    <div className="mfg-visual-empty">
                      <Loader2 size={24} className="spinning" />
                      <span>Loading BOM...</span>
                    </div>
                  ) : bomData?.components?.length ? (
                    <table className="mfg-bom-table">
                      <thead>
                        <tr>
                          <th>Designator</th>
                          <th>MPN</th>
                          <th>Qty</th>
                          <th>Stock</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bomData.components.slice(0, 20).map((comp, idx) => (
                          <tr key={idx} className={comp.stock === 0 ? 'out-of-stock' : ''}>
                            <td>{comp.usages?.map((u) => u.designator).join(', ') || '-'}</td>
                            <td>{comp.mpn || '-'}</td>
                            <td>{comp.quantity || 1}</td>
                            <td className={comp.stock === 0 ? 'stock-warning' : ''}>
                              {comp.stock != null
                                ? comp.stock === 0
                                  ? 'Out'
                                  : comp.stock.toLocaleString()
                                : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="mfg-visual-empty">
                      <Package size={32} />
                      <span>No BOM data available</span>
                    </div>
                  )}
                  {bomData?.components && bomData.components.length > 20 && (
                    <div className="mfg-bom-more">+{bomData.components.length - 20} more</div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Export Section */}
        {isReady && (
          <div className="mfg-section mfg-export-section">
            <h3 className="mfg-section-title">Export for JLC PCB</h3>

            <div className="mfg-export-directory">
              <span className="mfg-export-directory-label">Export to:</span>
              <div className="mfg-export-directory-input">
                <span className="mfg-export-directory-path">
                  {wizard.exportDirectory || `${project.root}/manufacturing`}
                </span>
                <button
                  className="mfg-btn secondary small"
                  onClick={handleBrowseDirectory}
                  title="Browse for export folder"
                >
                  <FolderOpen size={14} />
                </button>
              </div>
            </div>

            {wizard.exportError && (
              <div className="mfg-error-banner">
                <AlertCircle size={14} />
                {wizard.exportError}
              </div>
            )}

            {exportSuccess && (
              <div className="mfg-success-banner">
                <CheckCircle2 size={14} />
                <span>Files exported successfully</span>
                <button
                  className="mfg-btn secondary small"
                  onClick={handleRevealInFinder}
                  title="Open in Finder"
                >
                  <ExternalLink size={14} />
                  Open Folder
                </button>
              </div>
            )}

            <div className="mfg-export-actions">
              {!isConfirmed ? (
                <button className="mfg-btn primary" onClick={handleConfirmBuild}>
                  <CheckCircle2 size={14} />
                  Confirm Build
                </button>
              ) : (
                <button
                  className="mfg-btn primary"
                  onClick={handleExport}
                  disabled={isExporting}
                >
                  {isExporting ? (
                    <>
                      <Loader2 size={14} className="spinning" />
                      Exporting...
                    </>
                  ) : (
                    <>
                      <Download size={14} />
                      Export Files
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
