/**
 * ManufacturingWizard - Full-screen modal wizard for exporting manufacturing files.
 * Three-step accordion flow: Select Builds -> Build & Review -> Export
 */

import { useCallback, useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useStore } from '../../store';
import { sendAction, sendActionWithResponse } from '../../api/websocket';
import { postMessage } from '../../api/vscodeApi';
import type { Project, BOMData } from '../../types/build';
import type { BuildOutputs, ManufacturingBuild, CostEstimate } from './types';
import { WizardStep } from './WizardStep';
import { SelectBuildsStep } from './SelectBuildsStep';
import { BuildReviewStep } from './BuildReviewStep';
import { ExportStep } from './ExportStep';
import './ManufacturingWizard.css';

interface ManufacturingWizardProps {
  project: Project;
}

export function ManufacturingWizard({ project }: ManufacturingWizardProps) {
  const wizard = useStore((s) => s.manufacturingWizard);
  const queuedBuilds = useStore((s) => s.queuedBuilds);
  const closeWizard = useStore((s) => s.closeManufacturingWizard);
  const setStep = useStore((s) => s.setManufacturingStep);
  const toggleBuild = useStore((s) => s.toggleManufacturingBuild);
  const updateBuild = useStore((s) => s.updateManufacturingBuild);
  const setGitStatus = useStore((s) => s.setManufacturingGitStatus);
  const dismissWarning = useStore((s) => s.dismissUncommittedWarning);
  const setExportDirectory = useStore((s) => s.setManufacturingExportDirectory);
  const toggleFileType = useStore((s) => s.toggleManufacturingFileType);
  const setCostEstimate = useStore((s) => s.setManufacturingCostEstimate);
  const setQuantity = useStore((s) => s.setManufacturingQuantity);
  const setLoading = useStore((s) => s.setManufacturingLoading);
  const setExportError = useStore((s) => s.setManufacturingExportError);

  // Local state for build outputs and BOM data
  const [buildOutputs, setBuildOutputs] = useState<Record<string, BuildOutputs>>({});
  const [bomDataByTarget, setBomDataByTarget] = useState<Record<string, BOMData | null>>({});
  const [isLoadingBomByTarget, setIsLoadingBomByTarget] = useState<Record<string, boolean>>({});

  // Check git status on mount
  useEffect(() => {
    if (!wizard?.isOpen) return;

    const checkGitStatus = async () => {
      setLoading('gitStatus', true);
      try {
        const response = await sendActionWithResponse('getManufacturingGitStatus', {
          projectRoot: project.root,
        });
        if (response.result?.success) {
          const result = response.result as { success: boolean; hasUncommittedChanges?: boolean; changedFiles?: string[] };
          setGitStatus(
            result.hasUncommittedChanges ?? false,
            result.changedFiles ?? []
          );
        } else {
          setGitStatus(false, []);
        }
      } catch {
        setGitStatus(false, []);
      }
    };

    checkGitStatus();
  }, [wizard?.isOpen, project.root, setGitStatus, setLoading]);

  // Listen for browse directory result from VS Code
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = event.data;
      if (message?.type === 'browseExportDirectoryResult' && message.path) {
        setExportDirectory(message.path);
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [setExportDirectory]);

  // Sync build status from queuedBuilds
  useEffect(() => {
    if (!wizard?.selectedBuilds) return;

    for (const build of wizard.selectedBuilds) {
      const queuedBuild = queuedBuilds.find(
        (qb) =>
          qb.projectRoot === build.projectRoot &&
          qb.target === build.targetName
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
          // Fetch build outputs when build completes
          fetchBuildOutputs(build.targetName);
        } else if (queuedBuild.status === 'failed' && build.status !== 'failed') {
          newStatus = 'failed';
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
  }, [queuedBuilds, wizard?.selectedBuilds, updateBuild]);

  const fetchBuildOutputs = useCallback(async (targetName: string) => {
    try {
      const response = await sendActionWithResponse('getManufacturingOutputs', {
        projectRoot: project.root,
        target: targetName,
      });
      if (response.result?.success) {
        const result = response.result as { success: boolean; outputs: BuildOutputs };
        setBuildOutputs((prev: Record<string, BuildOutputs>) => ({
          ...prev,
          [targetName]: result.outputs,
        }));
        // Also fetch BOM data
        fetchBomData(targetName);
      }
    } catch (error) {
      console.error('Failed to fetch build outputs:', error);
    }
  }, [project.root]);

  const fetchBomData = useCallback(async (targetName: string) => {
    setIsLoadingBomByTarget((prev: Record<string, boolean>) => ({ ...prev, [targetName]: true }));
    try {
      const response = await sendActionWithResponse('refreshBOM', {
        projectRoot: project.root,
        target: targetName,
      });
      if (response.result?.success) {
        const result = response.result as { success: boolean; bom?: BOMData };
        if (result.bom) {
          setBomDataByTarget((prev: Record<string, BOMData | null>) => ({
            ...prev,
            [targetName]: result.bom ?? null,
          }));
        }
      }
    } catch (error) {
      console.error('Failed to fetch BOM:', error);
    } finally {
      setIsLoadingBomByTarget((prev: Record<string, boolean>) => ({ ...prev, [targetName]: false }));
    }
  }, [project.root]);

  const handleStartBuilds = useCallback(() => {
    if (!wizard?.selectedBuilds) return;

    for (const build of wizard.selectedBuilds) {
      if (build.status === 'pending') {
        sendAction('build', {
          projectRoot: build.projectRoot,
          targets: [build.targetName],
          frozen: true, // Use frozen builds for manufacturing
        });
        updateBuild(build.targetName, { status: 'building' });
      }
    }
  }, [wizard?.selectedBuilds, updateBuild]);

  const handleConfirmBuild = useCallback((targetName: string) => {
    updateBuild(targetName, { status: 'confirmed' });
  }, [updateBuild]);

  const handleRetryBuild = useCallback((targetName: string) => {
    updateBuild(targetName, { status: 'pending', error: null });
    sendAction('build', {
      projectRoot: project.root,
      targets: [targetName],
      frozen: true,
    });
    updateBuild(targetName, { status: 'building' });
  }, [project.root, updateBuild]);

  const handleCommitNow = useCallback(() => {
    // Open VS Code's source control view or run git commit
    postMessage({ type: 'openSourceControl' });
  }, []);

  const handleRefreshCost = useCallback(async () => {
    if (!wizard?.selectedBuilds) return;

    setLoading('cost', true);
    try {
      // Gather BOM data from confirmed builds
      const confirmedTargets = wizard.selectedBuilds
        .filter((b: ManufacturingBuild) => b.status === 'confirmed')
        .map((b: ManufacturingBuild) => b.targetName);

      if (confirmedTargets.length === 0) {
        setCostEstimate(null);
        return;
      }

      const response = await sendActionWithResponse('estimateManufacturingCost', {
        projectRoot: project.root,
        targets: confirmedTargets,
        quantity: wizard.quantity,
      });

      if (response.result?.success) {
        const result = response.result as { success: boolean; estimate: CostEstimate };
        setCostEstimate(result.estimate);
      } else {
        setCostEstimate(null);
      }
    } catch {
      setCostEstimate(null);
    }
  }, [wizard?.selectedBuilds, wizard?.quantity, project.root, setLoading, setCostEstimate]);

  const handleExport = useCallback(async () => {
    if (!wizard) return;

    setLoading('exporting', true);
    setExportError(null);

    try {
      const response = await sendActionWithResponse('exportManufacturingFiles', {
        projectRoot: project.root,
        targets: wizard.selectedBuilds
          .filter((b: ManufacturingBuild) => b.status === 'confirmed')
          .map((b: ManufacturingBuild) => b.targetName),
        directory: wizard.exportDirectory,
        fileTypes: wizard.selectedFileTypes,
      });

      if (response.result?.success) {
        const result = response.result as { success: boolean; files?: string[]; error?: string };
        // Show success message and close wizard
        postMessage({
          type: 'showInfo',
          message: `Successfully exported ${result.files?.length ?? 0} files`,
        });
        closeWizard();
      } else {
        const result = response.result as { success: boolean; error?: string } | undefined;
        setExportError(result?.error ?? 'Export failed');
      }
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Export failed');
    }
  }, [wizard, project.root, closeWizard, setLoading, setExportError]);

  const handlePurchase = useCallback(() => {
    // Open purchase URL (placeholder for now)
    window.open('https://atopile.io/purchase', '_blank', 'noopener,noreferrer');
  }, []);

  if (!wizard?.isOpen) return null;

  const { currentStep, selectedBuilds } = wizard;

  // Generate step summaries
  const step1Summary =
    selectedBuilds.length > 0
      ? `${selectedBuilds.length} build${selectedBuilds.length !== 1 ? 's' : ''} selected`
      : undefined;

  const confirmedCount = selectedBuilds.filter((b: ManufacturingBuild) => b.status === 'confirmed').length;
  const step2Summary =
    confirmedCount > 0
      ? `${confirmedCount} of ${selectedBuilds.length} confirmed`
      : undefined;

  return (
    <div className="manufacturing-wizard-overlay">
      <div className="manufacturing-wizard">
        <div className="wizard-header">
          <h2 className="wizard-title">Export Manufacturing Files</h2>
          <span className="wizard-project">{project.name}</span>
          <button className="wizard-close" onClick={closeWizard}>
            <X size={20} />
          </button>
        </div>

        <div className="wizard-content">
          <WizardStep
            number={1}
            title="Select Builds"
            isActive={currentStep === 1}
            isComplete={currentStep > 1}
            summary={step1Summary}
            onExpand={() => setStep(1)}
          >
            <SelectBuildsStep
              targets={project.targets}
              selectedBuilds={selectedBuilds}
              hasUncommittedChanges={wizard.hasUncommittedChanges}
              uncommittedWarningDismissed={wizard.uncommittedWarningDismissed}
              changedFiles={wizard.changedFiles}
              isLoadingGitStatus={wizard.isLoadingGitStatus}
              onToggleBuild={toggleBuild}
              onDismissWarning={dismissWarning}
              onCommitNow={handleCommitNow}
              onNext={() => setStep(2)}
            />
          </WizardStep>

          <WizardStep
            number={2}
            title="Build & Review"
            isActive={currentStep === 2}
            isComplete={currentStep > 2}
            summary={step2Summary}
            onExpand={() => setStep(2)}
            disabled={selectedBuilds.length === 0}
          >
            <BuildReviewStep
              builds={selectedBuilds}
              buildOutputs={buildOutputs}
              bomDataByTarget={bomDataByTarget}
              isLoadingBomByTarget={isLoadingBomByTarget}
              onConfirmBuild={handleConfirmBuild}
              onRetryBuild={handleRetryBuild}
              onStartBuilds={handleStartBuilds}
              onNext={() => {
                setStep(3);
                handleRefreshCost();
              }}
              onBack={() => setStep(1)}
            />
          </WizardStep>

          <WizardStep
            number={3}
            title="Export"
            isActive={currentStep === 3}
            isComplete={false}
            onExpand={() => setStep(3)}
            disabled={confirmedCount === 0}
          >
            <ExportStep
              selectedFileTypes={wizard.selectedFileTypes}
              exportDirectory={wizard.exportDirectory}
              costEstimate={wizard.costEstimate}
              quantity={wizard.quantity}
              isLoadingCost={wizard.isLoadingCost}
              isExporting={wizard.isExporting}
              exportError={wizard.exportError}
              onToggleFileType={toggleFileType}
              onDirectoryChange={setExportDirectory}
              onQuantityChange={setQuantity}
              onRefreshCost={handleRefreshCost}
              onExport={handleExport}
              onPurchase={handlePurchase}
              onBack={() => setStep(2)}
            />
          </WizardStep>
        </div>
      </div>
    </div>
  );
}
