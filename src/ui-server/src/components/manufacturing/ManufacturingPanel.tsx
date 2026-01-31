/**
 * ManufacturingPanel - Full panel for manufacturing export.
 * Features a stage-based progress view with live build step tracking.
 */

import { useCallback, useEffect, useState, useMemo, useRef } from 'react';
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
  Play,
} from 'lucide-react';
import { useStore } from '../../store';
import { sendAction, sendActionWithResponse } from '../../api/websocket';
import { postMessage, onExtensionMessage, postToExtension, isVsCodeWebview } from '../../api/vscodeApi';
import type { Project, BOMData, LcscPartData } from '../../types/build';
import type { BuildOutputs, BoardSummary, DetailedCostEstimate } from './types';
import ModelViewer from '../ModelViewer';
import GerberViewer from '../GerberViewer';
import '../GerberViewer.css';
import { API_URL } from '../../api/config';
import './ManufacturingPanel.css';

interface ManufacturingPanelProps {
  project: Project;
  onClose: () => void;
}

type VisualTab = 'gerbers' | 'bom' | '3d';
type Stage = 'build' | 'review' | 'export';

interface BuildStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'warning' | 'error';
  message?: string;
}

// Format price with appropriate decimal places for very cheap parts
function formatPrice(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}

// Format stock with K/M abbreviations for large quantities
function formatStock(stock: number): string {
  if (stock >= 1_000_000) return `${(stock / 1_000_000).toFixed(1)}M`;
  if (stock >= 1_000) return `${(stock / 1_000).toFixed(0)}K`;
  return stock.toLocaleString();
}

export function ManufacturingPanel({ project, onClose }: ManufacturingPanelProps) {
  const wizard = useStore((s) => s.manufacturingWizard);
  const queuedBuilds = useStore((s) => s.queuedBuilds);
  const updateBuild = useStore((s) => s.updateManufacturingBuild);
  const setExportError = useStore((s) => s.setManufacturingExportError);
  const setExportDirectory = useStore((s) => s.setManufacturingExportDirectory);

  // Local state
  const [activeVisualTab, setActiveVisualTab] = useState<VisualTab>('gerbers');
  const [reviewSectionCollapsed, setReviewSectionCollapsed] = useState(false);
  const [buildOutputs, setBuildOutputs] = useState<Record<string, BuildOutputs>>({});
  const [bomDataByTarget, setBomDataByTarget] = useState<Record<string, BOMData | null>>({});
  const [isLoadingBomByTarget, setIsLoadingBomByTarget] = useState<Record<string, boolean>>({});
  const [buildSteps, setBuildSteps] = useState<BuildStep[]>([]);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [buildStepsCollapsed, setBuildStepsCollapsed] = useState(false);
  const [awaitingBuildConfirmation, setAwaitingBuildConfirmation] = useState(true);
  const [gitStatus, setGitStatus] = useState<{ checking: boolean; hasChanges: boolean; files: string[] }>({
    checking: true,
    hasChanges: false,
    files: [],
  });

  // LCSC data enrichment state
  const [lcscParts, setLcscParts] = useState<Record<string, LcscPartData | null>>({});
  const [lcscLoadingIds, setLcscLoadingIds] = useState<Set<string>>(new Set());
  const lcscRequestIdRef = useRef(0);

  // Review checklist state - git-like staging
  const [reviewedItems, setReviewedItems] = useState<Set<string>>(new Set());

  // Board summary and detailed cost estimate
  const [boardSummary, setBoardSummary] = useState<BoardSummary | null>(null);
  const [detailedCostEstimate, setDetailedCostEstimate] = useState<DetailedCostEstimate | null>(null);
  const [isLoadingBoardSummary, setIsLoadingBoardSummary] = useState(false);

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

  // Expand build steps when building, collapse when done
  useEffect(() => {
    if (selectedBuild?.status === 'building' || selectedBuild?.status === 'pending') {
      setBuildStepsCollapsed(false);
    }
  }, [selectedBuild?.status]);

  // Sync build steps from real backend stages
  useEffect(() => {
    if (!selectedBuild) return;

    const queuedBuild = queuedBuilds.find(
      (qb) => qb.projectRoot === selectedBuild.projectRoot && qb.target === selectedBuild.targetName
    );

    if (!queuedBuild?.stages || queuedBuild.stages.length === 0) return;

    // Map backend stages to our build step format
    const backendSteps: BuildStep[] = queuedBuild.stages.map((stage) => {
      // Convert stage status to our format
      let status: BuildStep['status'] = 'pending';
      switch (stage.status) {
        case 'success':
          status = 'complete';
          break;
        case 'running':
          status = 'running';
          break;
        case 'failed':
        case 'error':
          status = 'error';
          break;
        case 'warning':
          status = 'warning';
          break;
        default:
          status = 'pending';
      }

      return {
        id: stage.stageId || stage.name,
        label: stage.displayName || stage.name,
        status,
        message: stage.elapsedSeconds ? `${stage.elapsedSeconds.toFixed(1)}s` : undefined,
      };
    });

    // Prepend git status step if we have it
    const gitStatusStep: BuildStep = gitStatus.checking
      ? { id: 'git', label: 'Checking for uncommitted changes', status: 'running' }
      : gitStatus.hasChanges
        ? { id: 'git', label: 'Uncommitted changes', status: 'warning', message: `${gitStatus.files.length} files` }
        : { id: 'git', label: 'No uncommitted changes', status: 'complete' };

    setBuildSteps([gitStatusStep, ...backendSteps]);
  }, [selectedBuild, queuedBuilds, gitStatus]);

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
          // Open problems panel to show build errors
          if (isVsCodeWebview()) {
            postToExtension({ type: 'showProblems' });
          }
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

  // Start build when confirmed
  const handleStartBuild = useCallback(() => {
    if (selectedBuild?.status === 'pending') {
      setAwaitingBuildConfirmation(false);
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
          fetchDetailedCostEstimate(targetName);
          runPostBuildChecks(result.outputs);
        }
      } catch (error) {
        console.error('Failed to fetch build outputs:', error);
      }
    },
    [project.root]
  );

  // Helper to update stock step based on BOM and LCSC data
  const updateStockStep = useCallback((bomComponents: BOMData['components'], lcscPartsData: Record<string, LcscPartData | null>) => {
    if (!bomComponents) return;

    // Enrich components with LCSC data
    const enriched = bomComponents.map((c) => {
      const lcscInfo = c.lcsc ? lcscPartsData[c.lcsc] : null;
      return {
        ...c,
        stock: c.stock ?? lcscInfo?.stock ?? null,
      };
    });

    const outOfStock = enriched.filter((c) => c.stock === 0);
    const unknownStock = enriched.filter((c) => c.stock == null);

    setBuildSteps((prev) => {
      const withoutStock = prev.filter(s => s.id !== 'stock');
      return [
        ...withoutStock,
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
      ];
    });
  }, []);

  // Fetch LCSC stock and price data for components
  const fetchLcscData = useCallback(
    async (lcscIds: string[], targetName: string, bomComponents?: BOMData['components']) => {
      const missing = lcscIds.filter((id) => !(id in lcscParts));
      if (missing.length === 0) {
        // No missing LCSC data, update stock step with existing data
        if (bomComponents) {
          updateStockStep(bomComponents, lcscParts);
        }
        return;
      }

      const requestId = ++lcscRequestIdRef.current;
      setLcscLoadingIds((prev) => {
        const next = new Set(prev);
        for (const id of missing) next.add(id);
        return next;
      });

      // Add a loading stock step
      setBuildSteps((prev) => {
        const withoutStock = prev.filter(s => s.id !== 'stock');
        return [
          ...withoutStock,
          { id: 'stock', label: 'Fetching stock data', status: 'running' },
        ];
      });

      try {
        const response = await sendActionWithResponse('fetchLcscParts', {
          lcscIds: missing,
          projectRoot: project.root,
          target: targetName,
        });

        if (requestId !== lcscRequestIdRef.current) return;

        const result = response.result ?? {};
        const parts = (result as { parts?: Record<string, LcscPartData | null> }).parts || {};
        const allParts = { ...lcscParts, ...parts };
        setLcscParts(allParts);

        // Update the stock step with actual data
        if (bomComponents) {
          updateStockStep(bomComponents, allParts);
        }
      } catch (error) {
        if (requestId !== lcscRequestIdRef.current) return;
        console.warn('Failed to fetch LCSC data', error);
        // Update stock step to show warning
        setBuildSteps((prev) => {
          const withoutStock = prev.filter(s => s.id !== 'stock');
          return [
            ...withoutStock,
            { id: 'stock', label: 'Parts availability', status: 'warning', message: 'Could not verify' },
          ];
        });
      } finally {
        setLcscLoadingIds((prev) => {
          const next = new Set(prev);
          for (const id of missing) next.delete(id);
          return next;
        });
      }
    },
    [lcscParts, project.root, updateStockStep]
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

            // Fetch LCSC data for components missing stock/price info
            const lcscIdsToFetch = result.bom.components
              ?.filter((c) => c.lcsc && (c.unitCost == null || c.stock == null))
              .map((c) => c.lcsc!)
              .filter((id, idx, arr) => arr.indexOf(id) === idx) || [];

            if (lcscIdsToFetch.length > 0) {
              fetchLcscData(lcscIdsToFetch, targetName, result.bom.components);
            } else {
              // No LCSC data to fetch, update stock step with current data
              updateStockStep(result.bom.components, lcscParts);
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch BOM:', error);
      } finally {
        setIsLoadingBomByTarget((prev) => ({ ...prev, [targetName]: false }));
      }
    },
    [project.root, fetchLcscData, updateStockStep, lcscParts]
  );

  // Fetch detailed cost estimate with board summary
  const fetchDetailedCostEstimate = useCallback(
    async (targetName: string) => {
      setIsLoadingBoardSummary(true);
      try {
        const response = await sendActionWithResponse('getDetailedCostEstimate', {
          projectRoot: project.root,
          targets: [targetName],
          quantity: 1,
          assemblyType: 'economic',
        });
        if (response.result?.success) {
          const result = response.result as unknown as DetailedCostEstimate;
          setDetailedCostEstimate(result);
          if (result.boardSummary) {
            setBoardSummary(result.boardSummary);
          }
        }
      } catch (error) {
        console.warn('Failed to fetch detailed cost estimate:', error);
      } finally {
        setIsLoadingBoardSummary(false);
      }
    },
    [project.root]
  );

  const runPostBuildChecks = useCallback(
    (outputs: BuildOutputs) => {
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
          // Stock step will be added/updated by fetchLcscData
          { id: 'stock', label: 'Parts availability', status: 'pending' },
          { id: 'requirements', label: 'All requirements met', status: 'complete' },
        ];
      });
    },
    []
  );

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

  const handleShowProblems = useCallback(() => {
    if (isVsCodeWebview()) {
      postToExtension({ type: 'showProblems' });
    }
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

  // Toggle review item (git-like staging)
  const toggleReviewItem = useCallback((item: string) => {
    setReviewedItems((prev) => {
      const next = new Set(prev);
      if (next.has(item)) {
        next.delete(item);
      } else {
        next.add(item);
      }
      return next;
    });
  }, []);

  if (!wizard?.isOpen || !selectedBuild) return null;

  const outputs = buildOutputs[selectedBuild.targetName];
  const bomData = bomDataByTarget[selectedBuild.targetName];
  const isLoadingBom = isLoadingBomByTarget[selectedBuild.targetName];

  const isBuilding = selectedBuild.status === 'building';
  const isFailed = selectedBuild.status === 'failed';
  const isReady = selectedBuild.status === 'ready' || selectedBuild.status === 'confirmed';

  const completedSteps = buildSteps.filter((s) => s.status === 'complete').length;
  const hasWarnings = buildSteps.some((s) => s.status === 'warning');
  const hasErrors = buildSteps.some((s) => s.status === 'error');

  // Determine the overall build status - worst status wins (error > warning > complete)
  const buildOverallStatus: 'complete' | 'warning' | 'error' = hasErrors
    ? 'error'
    : hasWarnings
      ? 'warning'
      : 'complete';

  // Enrich BOM data with LCSC stock/price info
  const enrichedBomComponents = useMemo(() => {
    if (!bomData?.components) return [];
    return bomData.components.map((component) => {
      const lcscInfo = component.lcsc ? lcscParts[component.lcsc] : null;
      const isLoading = component.lcsc ? lcscLoadingIds.has(component.lcsc) : false;

      // Create enriched component with LCSC data
      return {
        ...component,
        lcscLoading: isLoading,
        unitCost: component.unitCost ?? lcscInfo?.unit_cost ?? null,
        stock: component.stock ?? lcscInfo?.stock ?? null,
        manufacturer: component.manufacturer ?? lcscInfo?.manufacturer ?? null,
        mpn: component.mpn ?? lcscInfo?.mpn ?? null,
      };
    });
  }, [bomData?.components, lcscParts, lcscLoadingIds]);

  // Calculate review items - what needs to be reviewed (gerbers, bom, and 3d)
  const reviewItems = useMemo(() => {
    const items: Array<{ id: string; label: string; available: boolean; reviewed: boolean; warning?: string }> = [
      {
        id: 'gerbers',
        label: 'Gerbers',
        available: !!outputs?.gerbers,
        reviewed: reviewedItems.has('gerbers'),
      },
      {
        id: 'bom',
        label: 'BOM',
        available: enrichedBomComponents.length > 0,
        reviewed: reviewedItems.has('bom'),
        warning: enrichedBomComponents.some((c) => c.stock === 0)
          ? 'Some parts out of stock'
          : enrichedBomComponents.some((c) => c.stock == null)
            ? 'Some parts missing stock info'
            : undefined,
      },
      {
        id: '3d',
        label: '3D Preview',
        available: !!outputs?.glb,
        reviewed: reviewedItems.has('3d'),
      },
    ];
    return items;
  }, [outputs, enrichedBomComponents, reviewedItems]);

  const availableItems = reviewItems.filter((i) => i.available);
  const availableCount = availableItems.length;
  const allItemsReviewed = availableCount > 0 && availableItems.every((i) => i.reviewed);
  const reviewedCount = reviewItems.filter((i) => i.reviewed && i.available).length;

  // Mark current tab as reviewed and advance to next
  const handleMarkAsReviewed = useCallback(() => {
    toggleReviewItem(activeVisualTab);

    // Define review order and advance to next unreviewed item
    const reviewOrder: VisualTab[] = ['gerbers', 'bom', '3d'];
    const currentIndex = reviewOrder.indexOf(activeVisualTab);

    // Find next unreviewed item
    for (let i = currentIndex + 1; i < reviewOrder.length; i++) {
      const nextTab = reviewOrder[i];
      const item = reviewItems.find(r => r.id === nextTab);
      if (item?.available && !item.reviewed) {
        setActiveVisualTab(nextTab);
        return;
      }
    }

    // If all items reviewed, collapse the review section
    const allWillBeReviewed = reviewItems.filter(i => i.available).every(i =>
      i.reviewed || i.id === activeVisualTab
    );
    if (allWillBeReviewed) {
      setReviewSectionCollapsed(true);
    }
  }, [activeVisualTab, toggleReviewItem, reviewItems]);

  // Calculate cost summary - use detailed estimate when available
  const costSummary = useMemo(() => {
    // Use detailed cost estimate from backend when available
    if (detailedCostEstimate) {
      const outOfStock = enrichedBomComponents.filter((c) => c.stock === 0).length;
      return {
        componentsCost: detailedCostEstimate.componentsCost,
        pcbCost: detailedCostEstimate.pcbCost,
        assemblyCost: detailedCostEstimate.assemblyCost,
        totalCost: detailedCostEstimate.totalCost,
        uniqueParts: detailedCostEstimate.componentsBreakdown?.uniqueParts ?? enrichedBomComponents.length,
        totalParts: detailedCostEstimate.componentsBreakdown?.totalParts ?? enrichedBomComponents.reduce((sum, c) => sum + (c.quantity || 1), 0),
        outOfStock,
        // Detailed breakdown
        assemblyBreakdown: detailedCostEstimate.assemblyBreakdown,
        pcbBreakdown: detailedCostEstimate.pcbBreakdown,
      };
    }

    // Fallback to simple calculation
    const componentsCost = enrichedBomComponents.reduce((sum, c) => {
      return sum + (c.unitCost ?? 0) * (c.quantity || 1);
    }, 0);
    const uniqueParts = enrichedBomComponents.length;
    const totalParts = enrichedBomComponents.reduce((sum, c) => sum + (c.quantity || 1), 0);
    const outOfStock = enrichedBomComponents.filter((c) => c.stock === 0).length;

    // Rough PCB cost estimate (placeholder - would need board dimensions)
    const pcbCost = 5.0;
    // Assembly cost estimate
    const assemblyCost = 15.0 + uniqueParts * 2.5;

    return {
      componentsCost,
      pcbCost,
      assemblyCost,
      totalCost: componentsCost + pcbCost + assemblyCost,
      uniqueParts,
      totalParts,
      outOfStock,
      assemblyBreakdown: null,
      pcbBreakdown: null,
    };
  }, [enrichedBomComponents, detailedCostEstimate]);

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
            <div className={`mfg-stage ${currentStage === 'build' ? 'active' : ''} ${currentStage !== 'build' ? buildOverallStatus : ''}`}>
              <div className="mfg-stage-icon">
                {currentStage === 'build' && isBuilding && <Loader2 size={16} className="spinning" />}
                {currentStage === 'build' && isFailed && <AlertCircle size={16} />}
                {currentStage !== 'build' && buildOverallStatus === 'error' && <AlertCircle size={16} />}
                {currentStage !== 'build' && buildOverallStatus === 'warning' && <AlertTriangle size={16} />}
                {currentStage !== 'build' && buildOverallStatus === 'complete' && <CheckCircle2 size={16} />}
                {currentStage === 'build' && !isBuilding && !isFailed && <Circle size={16} />}
              </div>
              <span className="mfg-stage-label">Build</span>
            </div>
            <ChevronRight size={16} className="mfg-stage-arrow" />
            <div className={`mfg-stage ${currentStage === 'review' ? 'active' : ''} ${currentStage === 'export' || allItemsReviewed ? 'complete' : ''}`}>
              <div className="mfg-stage-icon">
                {(currentStage === 'export' || allItemsReviewed) && <CheckCircle2 size={16} />}
                {currentStage === 'review' && !allItemsReviewed && <Circle size={16} />}
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

        {/* Build Confirmation - Show before starting build */}
        {currentStage === 'build' && awaitingBuildConfirmation && !isBuilding && !isFailed && !isReady && !gitStatus.checking && (
          <div className="mfg-build-confirm">
            <div className="mfg-build-confirm-content">
              <h3 className="mfg-build-confirm-title">Ready to Build</h3>
              <p className="mfg-build-confirm-message">
                This will generate manufacturing files including Gerbers, BOM, and pick &amp; place files for <strong>{selectedBuild.targetName}</strong>.
              </p>
            </div>
            <div className="mfg-build-confirm-actions">
              <button className="mfg-btn primary large" onClick={handleStartBuild}>
                <Play size={16} />
                Start Build
              </button>
            </div>
          </div>
        )}

        {/* Build Steps - Collapsible when complete */}
        {(isBuilding || isReady || isFailed) && buildSteps.length > 0 && (
          <div className={`mfg-section mfg-steps-section ${buildStepsCollapsed ? 'collapsed' : ''}`}>
            <button
              className="mfg-section-header"
              onClick={() => setBuildStepsCollapsed(!buildStepsCollapsed)}
            >
              <h3 className="mfg-section-title">
                {isBuilding ? 'Building...' : isFailed ? 'Build Failed' : 'Build Complete'}
              </h3>
              <span className="mfg-section-status">
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
                {isFailed && (
                  <div className="mfg-error-actions">
                    <button className="mfg-btn secondary" onClick={handleShowProblems}>
                      <AlertCircle size={14} />
                      View Errors
                    </button>
                    <button className="mfg-btn secondary" onClick={handleRetryBuild}>
                      <RefreshCw size={14} />
                      Retry Build
                    </button>
                  </div>
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

        {/* Review Section - Collapsible with integrated tabs */}
        {isReady && (
          <div className={`mfg-section mfg-review-section ${reviewSectionCollapsed ? 'collapsed' : ''} ${allItemsReviewed ? 'complete' : ''}`}>
            <button
              className="mfg-section-header"
              onClick={() => setReviewSectionCollapsed(!reviewSectionCollapsed)}
            >
              <h3 className="mfg-section-title">
                {allItemsReviewed ? 'Review Complete' : 'Review'}
              </h3>
              <span className="mfg-section-status">
                {reviewedCount}/{availableCount}
                {allItemsReviewed && <CheckCircle2 size={14} className="status-complete" />}
                {reviewSectionCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </span>
            </button>

            {!reviewSectionCollapsed && (
              <div className="mfg-review-content">
                {/* Tabs with integrated step indicators */}
                <div className="mfg-visual-tabs">
                  <button
                    className={`mfg-visual-tab ${activeVisualTab === 'gerbers' ? 'active' : ''} ${reviewedItems.has('gerbers') ? 'reviewed' : ''}`}
                    onClick={() => setActiveVisualTab('gerbers')}
                  >
                    <span className="mfg-tab-indicator">
                      {reviewedItems.has('gerbers') ? <CheckCircle2 size={16} /> : <span className="mfg-tab-number">1</span>}
                    </span>
                    <Layers size={14} />
                    <span>Gerbers</span>
                  </button>
                  <button
                    className={`mfg-visual-tab ${activeVisualTab === 'bom' ? 'active' : ''} ${reviewedItems.has('bom') ? 'reviewed' : ''}`}
                    onClick={() => setActiveVisualTab('bom')}
                  >
                    <span className="mfg-tab-indicator">
                      {reviewedItems.has('bom') ? <CheckCircle2 size={16} /> : <span className="mfg-tab-number">2</span>}
                    </span>
                    <Package size={14} />
                    <span>BOM ({enrichedBomComponents.length})</span>
                  </button>
                  <button
                    className={`mfg-visual-tab ${activeVisualTab === '3d' ? 'active' : ''} ${reviewedItems.has('3d') ? 'reviewed' : ''}`}
                    onClick={() => setActiveVisualTab('3d')}
                  >
                    <span className="mfg-tab-indicator">
                      {reviewedItems.has('3d') ? <CheckCircle2 size={16} /> : <span className="mfg-tab-number">3</span>}
                    </span>
                    <Cuboid size={14} />
                    <span>3D Preview</span>
                  </button>
                </div>

                <div className="mfg-visual-content">
                  {activeVisualTab === 'gerbers' && (
                    <>
                      {outputs?.gerbers ? (
                        <GerberViewer
                          src={`${API_URL}/api/file?path=${encodeURIComponent(outputs.gerbers)}`}
                          hideControls
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

                  {activeVisualTab === 'bom' && (
                    <div className="mfg-bom-preview">
                      {isLoadingBom ? (
                        <div className="mfg-visual-empty">
                          <Loader2 size={24} className="spinning" />
                          <span>Loading BOM...</span>
                        </div>
                      ) : enrichedBomComponents.length ? (
                        <table className="mfg-bom-table">
                          <thead>
                            <tr>
                              <th>Designator</th>
                              <th>MPN</th>
                              <th>Qty</th>
                              <th>Price</th>
                              <th>Stock</th>
                            </tr>
                          </thead>
                          <tbody>
                            {enrichedBomComponents.slice(0, 20).map((comp, idx) => (
                              <tr key={idx} className={comp.stock === 0 ? 'out-of-stock' : ''}>
                                <td>{comp.usages?.map((u) => u.designator).join(', ') || '-'}</td>
                                <td>{comp.mpn || '-'}</td>
                                <td>{comp.quantity || 1}</td>
                                <td>
                                  {comp.lcscLoading ? (
                                    <RefreshCw size={12} className="spinning" />
                                  ) : comp.unitCost != null ? (
                                    formatPrice(comp.unitCost * (comp.quantity || 1))
                                  ) : (
                                    '-'
                                  )}
                                </td>
                                <td className={comp.stock === 0 ? 'stock-warning' : ''}>
                                  {comp.lcscLoading ? (
                                    <RefreshCw size={12} className="spinning" />
                                  ) : comp.stock != null ? (
                                    comp.stock === 0 ? 'Out' : formatStock(comp.stock)
                                  ) : (
                                    '-'
                                  )}
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
                      {enrichedBomComponents.length > 20 && (
                        <div className="mfg-bom-more">+{enrichedBomComponents.length - 20} more</div>
                      )}
                    </div>
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
                </div>

                {/* Floating review button */}
                {!reviewedItems.has(activeVisualTab) && (
                  <button
                    className="mfg-review-fab"
                    onClick={handleMarkAsReviewed}
                    title={`Mark ${activeVisualTab === 'gerbers' ? 'Gerbers' : activeVisualTab === 'bom' ? 'BOM' : '3D'} as reviewed`}
                  >
                    <CheckCircle2 size={18} />
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Export Section */}
        {isReady && (
          <div className={`mfg-section mfg-export-section ${!exportSuccess ? '' : 'complete'}`}>
            <button
              className="mfg-section-header"
              onClick={() => {}}
              style={{ cursor: 'default' }}
            >
              <h3 className="mfg-section-title">Export</h3>
              <span className="mfg-section-status">
                {exportSuccess && <CheckCircle2 size={14} className="status-complete" />}
              </span>
            </button>

            {!exportSuccess ? (
              <div className="mfg-export-content">
                {/* Board Summary Card */}
                {boardSummary && (
                  <div className="mfg-board-summary">
                    <h4 className="mfg-subsection-title">Board Summary</h4>
                    <div className="mfg-board-summary-grid">
                      {boardSummary.dimensions && (
                        <div className="mfg-board-summary-item">
                          <span className="mfg-board-summary-label">Size</span>
                          <span className="mfg-board-summary-value">
                            {boardSummary.dimensions.widthMm.toFixed(1)} × {boardSummary.dimensions.heightMm.toFixed(1)} mm
                            <span className="mfg-board-summary-note">({boardSummary.dimensions.areaCm2.toFixed(1)} cm²)</span>
                          </span>
                        </div>
                      )}
                      <div className="mfg-board-summary-item">
                        <span className="mfg-board-summary-label">Layers</span>
                        <span className="mfg-board-summary-value">{boardSummary.layerCount}</span>
                      </div>
                      {boardSummary.copperFinish && (
                        <div className="mfg-board-summary-item">
                          <span className="mfg-board-summary-label">Finish</span>
                          <span className="mfg-board-summary-value">{boardSummary.copperFinish}</span>
                        </div>
                      )}
                      <div className="mfg-board-summary-item">
                        <span className="mfg-board-summary-label">Assembly</span>
                        <span className="mfg-board-summary-value">
                          {boardSummary.assembly.isDoubleSided ? 'Double-sided' : 'Single-sided'}
                          <span className="mfg-board-summary-note">
                            ({boardSummary.assembly.topCount} top{boardSummary.assembly.bottomCount > 0 ? `, ${boardSummary.assembly.bottomCount} bottom` : ''})
                          </span>
                        </span>
                      </div>
                      <div className="mfg-board-summary-item">
                        <span className="mfg-board-summary-label">Parts</span>
                        <span className="mfg-board-summary-value">
                          {boardSummary.parts.totalUniqueParts} unique
                          {boardSummary.parts.basicCount > 0 && (
                            <span className="mfg-parts-tag basic">{boardSummary.parts.basicCount} basic</span>
                          )}
                          {boardSummary.parts.extendedCount > 0 && (
                            <span className="mfg-parts-tag extended">{boardSummary.parts.extendedCount} extended</span>
                          )}
                        </span>
                      </div>
                      <div className="mfg-board-summary-item">
                        <span className="mfg-board-summary-label">Solder Joints</span>
                        <span className="mfg-board-summary-value">~{boardSummary.estimatedSolderJoints}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Cost Summary Card */}
                <div className="mfg-cost-summary">
                  <h4 className="mfg-subsection-title">
                    Estimated Cost (1 unit)
                    {isLoadingBoardSummary && <Loader2 size={14} className="spinning" style={{ marginLeft: 8 }} />}
                  </h4>
                  <div className="mfg-cost-grid">
                    <div className="mfg-cost-row">
                      <span className="mfg-cost-label">
                        PCB Fabrication
                        {costSummary.pcbBreakdown && boardSummary && (
                          <span className="mfg-cost-detail">
                            ({boardSummary.layerCount}L, {boardSummary.dimensions ? `${boardSummary.dimensions.areaCm2.toFixed(1)}cm²` : 'size TBD'})
                          </span>
                        )}
                      </span>
                      <span className="mfg-cost-value">${costSummary.pcbCost.toFixed(2)}</span>
                    </div>
                    <div className="mfg-cost-row">
                      <span className="mfg-cost-label">Components ({costSummary.uniqueParts} unique, {costSummary.totalParts} total)</span>
                      <span className="mfg-cost-value">${costSummary.componentsCost.toFixed(2)}</span>
                    </div>
                    <div className="mfg-cost-row">
                      <span className="mfg-cost-label">Assembly</span>
                      <span className="mfg-cost-value">${costSummary.assemblyCost.toFixed(2)}</span>
                    </div>
                    {/* Detailed assembly breakdown */}
                    {costSummary.assemblyBreakdown && (
                      <div className="mfg-cost-breakdown">
                        <div className="mfg-cost-breakdown-row">
                          <span>Setup fee</span>
                          <span>${costSummary.assemblyBreakdown.setupFee.toFixed(2)}</span>
                        </div>
                        <div className="mfg-cost-breakdown-row">
                          <span>Stencil</span>
                          <span>${costSummary.assemblyBreakdown.stencilFee.toFixed(2)}</span>
                        </div>
                        {costSummary.assemblyBreakdown.loadingFees > 0 && (
                          <div className="mfg-cost-breakdown-row">
                            <span>
                              Loading fees
                              <span className="mfg-cost-detail">
                                ({costSummary.assemblyBreakdown.loadingFeePartsCount} extended parts × $3)
                              </span>
                            </span>
                            <span>${costSummary.assemblyBreakdown.loadingFees.toFixed(2)}</span>
                          </div>
                        )}
                        <div className="mfg-cost-breakdown-row">
                          <span>Solder joints</span>
                          <span>${costSummary.assemblyBreakdown.solderJointsCost.toFixed(2)}</span>
                        </div>
                      </div>
                    )}
                    <div className="mfg-cost-row mfg-cost-total">
                      <span className="mfg-cost-label">Estimated Total</span>
                      <span className="mfg-cost-value">${costSummary.totalCost.toFixed(2)}</span>
                    </div>
                  </div>
                  {costSummary.outOfStock > 0 && (
                    <div className="mfg-cost-warning">
                      <AlertTriangle size={14} />
                      {costSummary.outOfStock} component{costSummary.outOfStock > 1 ? 's' : ''} out of stock
                    </div>
                  )}
                  {boardSummary && boardSummary.parts.partsWithLoadingFee > 0 && (
                    <div className="mfg-cost-tip">
                      <span className="mfg-cost-tip-icon">💡</span>
                      <span>
                        Use more <strong>basic parts</strong> to avoid ${boardSummary.parts.partsWithLoadingFee * 3} in loading fees
                      </span>
                    </div>
                  )}
                </div>

                {/* Export Files Card */}
                <div className="mfg-export-card">
                  <h4 className="mfg-subsection-title">Export for JLCPCB</h4>
                  <div className="mfg-export-files">
                    <div className="mfg-export-file">
                      <CheckCircle2 size={14} className={outputs?.gerbers ? 'available' : 'unavailable'} />
                      <span>Gerber Files</span>
                      <span className="mfg-export-ext">.zip</span>
                    </div>
                    <div className="mfg-export-file">
                      <CheckCircle2 size={14} className={outputs?.bomCsv ? 'available' : 'unavailable'} />
                      <span>Bill of Materials</span>
                      <span className="mfg-export-ext">.csv</span>
                    </div>
                    <div className="mfg-export-file">
                      <CheckCircle2 size={14} className={outputs?.pickAndPlace ? 'available' : 'unavailable'} />
                      <span>Pick & Place</span>
                      <span className="mfg-export-ext">.csv</span>
                    </div>
                  </div>

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

                  {/* Review progress indicator */}
                  {!allItemsReviewed && (
                    <div className="mfg-review-reminder">
                      <AlertTriangle size={14} />
                      <span>Review progress: {reviewedCount}/{availableCount} items</span>
                    </div>
                  )}
                  {allItemsReviewed && (
                    <div className="mfg-review-complete">
                      <CheckCircle2 size={14} />
                      <span>All items reviewed</span>
                    </div>
                  )}

                  <div className="mfg-export-actions">
                    <button
                      className="mfg-btn primary large"
                      onClick={handleExport}
                      disabled={isExporting}
                    >
                      {isExporting ? (
                        <>
                          <Loader2 size={16} className="spinning" />
                          Exporting...
                        </>
                      ) : (
                        <>
                          <Download size={16} />
                          Export Files
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              /* Success State */
              <div className="mfg-export-success">
                <div className="mfg-success-icon">
                  <CheckCircle2 size={48} />
                </div>
                <h3 className="mfg-success-title">Ready for Manufacturing!</h3>
                <p className="mfg-success-message">
                  Your files have been exported and are ready to upload to JLCPCB.
                </p>

                <div className="mfg-success-files">
                  <div className="mfg-success-file">
                    <Package size={16} />
                    <span>{selectedBuild.targetName}.gerber.zip</span>
                  </div>
                  <div className="mfg-success-file">
                    <Package size={16} />
                    <span>{selectedBuild.targetName}.bom.csv</span>
                  </div>
                  <div className="mfg-success-file">
                    <Package size={16} />
                    <span>{selectedBuild.targetName}.pnp.csv</span>
                  </div>
                </div>

                <div className="mfg-success-actions">
                  <button
                    className="mfg-btn primary large"
                    onClick={handleRevealInFinder}
                  >
                    <FolderOpen size={16} />
                    Open Export Folder
                  </button>
                  <a
                    href="https://cart.jlcpcb.com/quote"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mfg-btn secondary large"
                  >
                    <ExternalLink size={16} />
                    Go to JLCPCB
                  </a>
                </div>

                <button
                  className="mfg-btn-link"
                  onClick={() => setExportSuccess(false)}
                >
                  ← Back to Export Options
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
