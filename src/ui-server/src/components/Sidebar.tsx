/**
 * Sidebar component - Main panel with all sections.
 * Uses unified panel sizing system for consistent expand/collapse behavior.
 */

import { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import { CollapsibleSection } from './CollapsibleSection';
import { ActiveProjectPanel } from './ActiveProjectPanel';
import { StandardLibraryPanel } from './StandardLibraryPanel';
import { VariablesPanel } from './VariablesPanel';
import { BOMPanel } from './BOMPanel';
import { PackageDetailPanel } from './PackageDetailPanel';
import { StructurePanel } from './StructurePanel';
import { PackagesPanel } from './PackagesPanel';
import { PartsSearchPanel } from './PartsSearchPanel';
import { PartsDetailPanel } from './PartsDetailPanel';
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
  type SelectedPart,
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
  const isConnected = useStore((s) => s.isConnected);
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
  const [selectedPart, setSelectedPart] = useState<SelectedPart | null>(null);

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

  // Keep selected package in sync with refreshed package list (e.g., after install/uninstall)
  useEffect(() => {
    if (!selectedPackage || !packages) return;
    const match = packages.find((pkg) => pkg.identifier === selectedPackage.fullName);
    if (!match) return;

    const depsForProject = selectedProjectRoot
      ? projectDependencies?.[selectedProjectRoot] || []
      : [];
    const depInfo = selectedProjectRoot
      ? depsForProject.find((dep) => dep.identifier === selectedPackage.fullName)
      : undefined;
    const installedForProject = selectedProjectRoot ? Boolean(depInfo) : match.installed;
    const versionForProject = selectedProjectRoot
      ? depInfo?.version
      : match.version ?? selectedPackage.version;

    setSelectedPackage((prev) => {
      if (!prev || prev.fullName !== selectedPackage.fullName) return prev;
      const next = {
        ...prev,
        installed: installedForProject,
        version: versionForProject ?? prev.version,
        latestVersion: match.latestVersion ?? prev.latestVersion,
        description: match.description || match.summary || prev.description,
        homepage: match.homepage ?? prev.homepage,
        repository: match.repository ?? prev.repository,
      };
      const changed =
        next.installed !== prev.installed ||
        next.version !== prev.version ||
        next.latestVersion !== prev.latestVersion ||
        next.description !== prev.description ||
        next.homepage !== prev.homepage ||
        next.repository !== prev.repository;
      return changed ? next : prev;
    });
  }, [packages, selectedPackage, selectedProjectRoot, projectDependencies]);

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
    setSelectedPart,
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

  const handlePartClose = useCallback(() => {
    setSelectedPart(null);
  }, []);

  const handleOpenPartDetail = useCallback((part: SelectedPart) => {
    setSelectedPackage(null);
    action('clearPackageDetails');
    setSelectedPart(part);
  }, []);

  const handlePackageInstall = useCallback(async (version?: string) => {
    if (!selectedPackage) return;
    const projectRoot = selectedProjectRoot || sidebarProjects?.[0]?.root;
    if (!projectRoot) return;

    const packageId = selectedPackage.fullName;
    const store = useStore.getState();
    const depsForProject = projectDependencies?.[projectRoot] || [];
    const depInfo = depsForProject.find((dep) => dep.identifier === packageId);
    const installedVersion = depInfo?.version;
    const isDirect = depInfo?.isDirect === true;
    const isInstalled = Boolean(depInfo);

    // Set installing state immediately for UI feedback
    store.addInstallingPackage(packageId);

    try {
      let response;
      if (version && isInstalled && installedVersion && version !== installedVersion) {
        if (!isDirect) {
          const via = depInfo?.via?.length ? `Required by: ${depInfo.via.join(', ')}` : '';
          store.setInstallError(
            packageId,
            `Cannot change version for a transitive dependency. ${via}`.trim()
          );
          return;
        }
        response = await sendActionWithResponse('changeDependencyVersion', {
          packageId,
          projectRoot,
          version,
        });
      } else {
        response = await sendActionWithResponse('installPackage', {
          packageId,
          projectRoot,
          version,
        });
      }

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
  }, [selectedPackage, selectedProjectRoot, sidebarProjects, projectDependencies]);

  const handlePackageUninstall = useCallback(async () => {
    if (!selectedPackage) return;
    const projectRoot = selectedProjectRoot || sidebarProjects?.[0]?.root;
    if (!projectRoot) return;

    const packageId = selectedPackage.fullName;
    const store = useStore.getState();

    store.addInstallingPackage(packageId);

    try {
      const response = await sendActionWithResponse('removePackage', {
        packageId,
        projectRoot,
      });

      if (!response.result?.success) {
        store.setInstallError(packageId, response.result?.error || 'Uninstall failed');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Uninstall failed';
      store.setInstallError(packageId, message);
    }
  }, [selectedPackage, selectedProjectRoot, sidebarProjects]);

  // Loading state
  if (!state) {
    return <div className="sidebar loading">Loading...</div>;
  }

  return (
    <div className={`unified-layout ${selectedPackage || selectedPart ? 'package-detail-open' : ''}`}>
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
                const errorMsg = response.result?.error || 'Failed to add build';
                throw new Error(errorMsg);
              }
              action('refreshProjects');
            }}
            onGenerateManufacturingData={handleGenerateManufacturingData}
            queuedBuilds={queuedBuilds}
            onCancelBuild={handlers.handleCancelQueuedBuild}
          />
        </CollapsibleSection>

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

        {/* Parts Section */}
        <CollapsibleSection
          id="parts"
          title="Parts"
          collapsed={panels.isCollapsed('parts')}
          onToggle={() => panels.togglePanel('parts')}
          height={panels.calculatedHeights['parts']}
          onResizeStart={(e) => panels.handleResizeStart('parts', e)}
        >
          <PartsSearchPanel
            selectedProjectRoot={selectedProjectRoot}
            onOpenPartDetail={handleOpenPartDetail}
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
      {selectedPart ? (
        <div className="detail-panel-container">
          <PartsDetailPanel
            part={selectedPart}
            projectRoot={selectedProjectRoot}
            onClose={handlePartClose}
          />
        </div>
      ) : selectedPackage && (
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
            onUninstall={handlePackageUninstall}
          />
        </div>
      )}

      {/* Disconnected overlay - covers sidebar when backend is down */}
      {!isConnected && (
        <div className="disconnected-overlay">
          <div className="disconnected-content">
            <svg className="disconnected-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 1l22 22" />
              <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
              <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
              <path d="M10.71 5.05A16 16 0 0 1 22.56 9" />
              <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
              <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
              <line x1="12" y1="20" x2="12.01" y2="20" />
            </svg>
            <div className="disconnected-title">Backend Disconnected</div>
            <div className="disconnected-message">
              <p>Run <code>ato dev clear-logs</code> in terminal</p>
              <p>Run <code>Restart Extension Host</code> in VS Code command palette</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
