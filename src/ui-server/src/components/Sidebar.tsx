/**
 * Sidebar component - Main panel with all sections.
 * Uses unified panel sizing system for consistent expand/collapse behavior.
 */

import { useState, useRef, useMemo, useCallback } from 'react';
import { CollapsibleSection } from './CollapsibleSection';
import { ActiveProjectPanel } from './ActiveProjectPanel';
import { StandardLibraryPanel } from './StandardLibraryPanel';
import { VariablesPanel } from './VariablesPanel';
import { BOMPanel } from './BOMPanel';
import { PackageDetailPanel } from './PackageDetailPanel';
import { StructurePanel } from './StructurePanel';
import { PackagesPanel } from './PackagesPanel';
import { sendAction, sendActionWithResponse } from '../api/websocket';
import { useStore } from '../store';
import { usePanelSizing } from '../hooks/usePanelSizing';
import {
  SidebarHeader,
  useSidebarData,
  useSidebarEffects,
  useSidebarHandlers,
  type Selection,
  type SelectedPackage,
} from './sidebar-modules';
import './Sidebar.css';
import '../styles.css';
import type { VariableNode } from '../types/build';

// Send action to backend via WebSocket (no VS Code dependency)
const action = (name: string, data?: Record<string, unknown>) => {
  if (name === 'openUrl' && data && 'url' in data) {
    const url = (data as { url?: string }).url;
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
  }
  sendAction(name, data);
};

// Helper to count variables recursively (defined outside component to avoid recreation)
function countVariables(nodes: VariableNode[] | undefined): number {
  if (!nodes) return 0;
  let count = 0;
  for (const n of nodes) {
    count += n.variables?.length || 0;
    if (n.children) count += countVariables(n.children);
  }
  return count;
}

export function Sidebar() {
  // Granular selectors - only re-render when specific state changes
  const projects = useStore((s) => s.projects);
  const selectedProjectRoot = useStore((s) => s.selectedProjectRoot) ?? null;
  const selectedTargetNames = useStore((s) => s.selectedTargetNames) ?? [];
  const isLoadingProjects = useStore((s) => s.isLoadingProjects);
  const isLoadingPackages = useStore((s) => s.isLoadingPackages);
  const packagesError = useStore((s) => s.packagesError);
  const installingPackageIds = useStore((s) => s.installingPackageIds);
  const installError = useStore((s) => s.installError);
  const stdlibItems = useStore((s) => s.stdlibItems);
  const isLoadingStdlib = useStore((s) => s.isLoadingStdlib);
  const currentVariablesData = useStore((s) => s.currentVariablesData);
  const isLoadingVariables = useStore((s) => s.isLoadingVariables);
  const variablesError = useStore((s) => s.variablesError);
  const bomData = useStore((s) => s.bomData);
  const isLoadingBom = useStore((s) => s.isLoadingBom);
  const bomError = useStore((s) => s.bomError);
  const selectedPackageDetails = useStore((s) => s.selectedPackageDetails);
  const isLoadingPackageDetails = useStore((s) => s.isLoadingPackageDetails);
  const packageDetailsError = useStore((s) => s.packageDetailsError);
  const projectModules = useStore((s) => s.projectModules);
  const projectDependencies = useStore((s) => s.projectDependencies);
  const atopile = useStore((s) => s.atopile);
  const activeEditorFile = useStore((s) => s.activeEditorFile);
  const lastAtoFile = useStore((s) => s.lastAtoFile);
  const packages = useStore((s) => s.packages);

  // Reconstruct state object for hooks that still need it
  // TODO: Refactor useSidebarData/useSidebarHandlers to use granular selectors
  const state = useStore((s) => s);

  const selectedTargetName = useMemo(() => {
    if (!selectedProjectRoot) return null;
    if (selectedTargetNames.length > 0) return selectedTargetNames[0];
    const project = projects?.find((p) => p.root === selectedProjectRoot);
    return project?.targets?.[0]?.name ?? null;
  }, [selectedProjectRoot, selectedTargetNames, projects]);

  // Local UI state
  const [, setSelection] = useState<Selection>({ type: 'none' });
  const [selectedPackage, setSelectedPackage] = useState<SelectedPackage | null>(null);

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);

  // Memoized computed values (previously inline in JSX)
  const variableCount = useMemo(
    () => countVariables(currentVariablesData?.nodes),
    [currentVariablesData]
  );

  const bomWarningCount = useMemo(() => {
    if (!bomData?.components) return 0;
    return bomData.components.filter(c => c.stock !== null && c.stock === 0).length;
  }, [bomData]);

  // Use data transformation hook
  const {
    projects: sidebarProjects,
    projectCount,
    packageCount,
    queuedBuilds,
  } = useSidebarData({ state });

  // Unified panel sizing - all panels start collapsed, auto-expand on events
  const panels = usePanelSizing({
    containerRef,
    hasProjectSelected: !!selectedProjectRoot,
  });

  // Use effects hook for side effects (data fetching, etc.)
  useSidebarEffects({
    selectedProjectRoot,
    selectedTargetName,
    panels,
    action,
  });

  // Use handlers hook for event handlers
  const handlers = useSidebarHandlers({
    projects: sidebarProjects,
    state,
    setSelection,
    setSelectedPackage,
    action,
  });

  // Memoized callbacks for event handlers (avoid new function references each render)
  const handleBuildTarget = useCallback((projectRoot: string, targetName: string) => {
    action('build', { projectRoot, targets: [targetName] });
  }, []);

  const handleBuildAllTargets = useCallback((projectRoot: string, projectName: string) => {
    action('build', { level: 'project', id: projectRoot, label: projectName, targets: [] });
  }, []);

  // Generate manufacturing data - triggers a build which includes manufacturing outputs
  const handleGenerateManufacturingData = useCallback((projectRoot: string, targetName: string) => {
    // Manufacturing data is generated as part of the build process
    // The build outputs include gerbers, BOM, and pick-and-place files
    action('build', { projectRoot, targets: [targetName] });
  }, []);

  const handleOpenOutput = useCallback(async (
    output: 'openKiCad' | 'open3D' | 'openLayout',
    projectRoot: string,
    targetName: string
  ) => {
    const outputNames: Record<string, string> = {
      openKiCad: 'KiCad',
      open3D: '3D view',
      openLayout: 'Layout',
    };
    const outputName = outputNames[output] || output;

    try {
      const response = await sendActionWithResponse(output, {
        projectId: projectRoot,
        targetName,
      });
      if (!response.result?.success) {
        const error =
          typeof response.result?.error === 'string'
            ? response.result.error
            : `Failed to open ${outputName}.`;
        action('uiLog', {
          level: 'warning',
          message: error,
        });
        return;
      }
    } catch (error) {
      console.warn('Failed to open output', error);
      action('uiLog', {
        level: 'error',
        message: `Failed to open ${outputName}: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  }, []);

  const handleRefreshStdlib = useCallback(() => {
    action('refreshStdlib');
  }, []);

  const handleGoToSource = useCallback((path: string, line?: number) => {
    action('openFile', { file: path, line });
  }, []);

  const handlePackageClose = useCallback(() => {
    setSelectedPackage(null);
    action('clearPackageDetails');
  }, []);

  const handlePackageInstall = useCallback(async (version?: string) => {
    if (!selectedPackage) return;
    const projectRoot = selectedProjectRoot || sidebarProjects?.[0]?.root;
    if (!projectRoot) return;

    const packageId = selectedPackage.fullName;
    const store = useStore.getState();

    // Set installing state immediately for UI feedback
    store.addInstallingPackage(packageId);

    try {
      const response = await sendActionWithResponse('installPackage', {
        packageId,
        projectRoot,
        version
      });

      // The backend returns success immediately, but install runs async.
      // The installing state will be cleared when we receive the
      // project_dependencies_changed event (on success) or packages_changed
      // event with error (on failure).
      if (!response.result?.success) {
        store.setInstallError(packageId, response.result?.error || 'Install failed');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Install failed';
      store.setInstallError(packageId, message);
    }
  }, [selectedPackage, selectedProjectRoot, sidebarProjects]);

  // Loading state
  if (!state) {
    return <div className="sidebar loading">Loading...</div>;
  }

  return (
    <div className={`unified-layout ${selectedPackage ? 'package-detail-open' : ''}`}>
      {/* Header with settings */}
      <SidebarHeader
        atopile={atopile}
      />

      <div className="panel-sections" ref={containerRef}>
        {/* Projects Section */}
        <CollapsibleSection
          id="projects"
          title="Projects"
          badge={projectCount}
          loading={isLoadingProjects}
          collapsed={panels.isCollapsed('projects')}
          onToggle={() => panels.togglePanel('projects')}
          height={panels.calculatedHeights['projects']}
          onResizeStart={(e) => panels.handleResizeStart('projects', e)}
        >
          <ActiveProjectPanel
            projects={projects || []}
            selectedProjectRoot={selectedProjectRoot}
            selectedTargetName={selectedTargetName}
            projectModules={selectedProjectRoot ? projectModules?.[selectedProjectRoot] : undefined}
            onSelectProject={handlers.handleSelectProject}
            onSelectTarget={handlers.handleSelectTarget}
            onBuildTarget={handleBuildTarget}
            onBuildAllTargets={handleBuildAllTargets}
            onOpenKiCad={(projectRoot, targetName) => handleOpenOutput('openKiCad', projectRoot, targetName)}
            onOpen3D={(projectRoot, targetName) => handleOpenOutput('open3D', projectRoot, targetName)}
            onOpenLayout={(projectRoot, targetName) => handleOpenOutput('openLayout', projectRoot, targetName)}
            onCreateProject={handlers.handleCreateProject}
            onCreateTarget={async (projectRoot, data) => {
              const response = await sendActionWithResponse('addBuildTarget', {
                project_root: projectRoot,
                name: data.name,
                entry: data.entry,
              });
              if (!response.result?.success) {
                const errorMsg = response.result?.error || 'Failed to add target';
                throw new Error(errorMsg);
              }
              action('refreshProjects');
            }}
            onGenerateManufacturingData={handleGenerateManufacturingData}
            queuedBuilds={queuedBuilds}
            onCancelBuild={handlers.handleCancelQueuedBuild}
          />
        </CollapsibleSection>

        {/* Structure Section */}
        <CollapsibleSection
          id="structure"
          title="Structure"
          collapsed={panels.isCollapsed('structure')}
          onToggle={() => panels.togglePanel('structure')}
          height={panels.calculatedHeights['structure']}
          onResizeStart={(e) => panels.handleResizeStart('structure', e)}
        >
          <StructurePanel
            activeFilePath={activeEditorFile}
            lastAtoFile={lastAtoFile}
            projects={projects || []}
            onRefreshStructure={handlers.handleStructureRefresh}
          />
        </CollapsibleSection>

        {/* Build Queue is now integrated into Projects panel above */}

        {/* Packages Section */}
        <CollapsibleSection
          id="packages"
          title="Packages"
          badge={packageCount}
          loading={isLoadingPackages}
          warningMessage={packagesError || null}
          collapsed={panels.isCollapsed('packages')}
          onToggle={() => panels.togglePanel('packages')}
          height={panels.calculatedHeights['packages']}
          onResizeStart={(e) => panels.handleResizeStart('packages', e)}
        >
          <PackagesPanel
            packages={packages || []}
            installedDependencies={selectedProjectRoot ? (projectDependencies?.[selectedProjectRoot] || []) : []}
            selectedProjectRoot={selectedProjectRoot}
            installError={installError}
            onOpenPackageDetail={handlers.handleOpenPackageDetail}
          />
        </CollapsibleSection>

        {/* Standard Library Section */}
        <CollapsibleSection
          id="stdlib"
          title="Standard Library"
          badge={stdlibItems?.length || 0}
          collapsed={panels.isCollapsed('stdlib')}
          onToggle={() => panels.togglePanel('stdlib')}
          height={panels.calculatedHeights['stdlib']}
          onResizeStart={(e) => panels.handleResizeStart('stdlib', e)}
        >
          <StandardLibraryPanel
            items={stdlibItems}
            isLoading={isLoadingStdlib}
            onRefresh={handleRefreshStdlib}
          />
        </CollapsibleSection>

        {/* Variables Section */}
        <CollapsibleSection
          id="variables"
          title="Variables"
          badge={variableCount}
          collapsed={panels.isCollapsed('variables')}
          onToggle={() => panels.togglePanel('variables')}
          height={panels.calculatedHeights['variables']}
          onResizeStart={(e) => panels.handleResizeStart('variables', e)}
        >
          <VariablesPanel
            variablesData={currentVariablesData}
            isLoading={isLoadingVariables}
            error={variablesError}
            selectedTargetName={selectedTargetName}
            hasActiveProject={!!selectedProjectRoot}
          />
        </CollapsibleSection>

        {/* BOM Section */}
        <CollapsibleSection
          id="bom"
          title="BOM"
          badge={bomData?.components?.length ?? 0}
          warningCount={bomWarningCount}
          collapsed={panels.isCollapsed('bom')}
          onToggle={() => panels.togglePanel('bom')}
          height={panels.calculatedHeights['bom']}
          onResizeStart={(e) => panels.handleResizeStart('bom', e)}
        >
          <BOMPanel
            bomData={bomData}
            isLoading={isLoadingBom}
            error={bomError}
            selectedProjectRoot={selectedProjectRoot}
            selectedTargetNames={selectedTargetNames}
            onGoToSource={handleGoToSource}
          />
        </CollapsibleSection>
      </div>

      {/* Detail Panel (slides in when package selected) */}
      {selectedPackage && (
        <div className="detail-panel-container">
          <PackageDetailPanel
            package={selectedPackage}
            packageDetails={selectedPackageDetails || null}
            isLoading={isLoadingPackageDetails || false}
            isInstalling={installingPackageIds?.includes(selectedPackage.fullName) || false}
            installError={installError || null}
            error={packageDetailsError || null}
            onClose={handlePackageClose}
            onInstall={handlePackageInstall}
          />
        </div>
      )}
    </div>
  );
}
