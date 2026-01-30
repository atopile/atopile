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
import { FileExplorerPanel } from './FileExplorerPanel';
import { sendAction, sendActionWithResponse } from '../api/websocket';
import { postMessage, isVsCodeWebview } from '../api/vscodeApi';
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

export function Sidebar() {
  // Granular selectors - only re-render when specific state changes
  const isConnected = useStore((s) => s.isConnected);
  const projects = useStore((s) => s.projects);
  const selectedProjectRoot = useStore((s) => s.selectedProjectRoot) ?? null;
  const selectedTargetNames = useStore((s) => s.selectedTargetNames) ?? [];
  const isLoadingProjects = useStore((s) => s.isLoadingProjects);
  const isLoadingPackages = useStore((s) => s.isLoadingPackages);
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
  const [activeTab, setActiveTab] = useState<'files' | 'structure' | 'packages' | 'parts' | 'stdlib' | 'parameters' | 'bom'>('files');

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const tabBarRef = useRef<HTMLDivElement>(null);

  // Track tab bar width to shorten labels when needed
  const [tabBarWidth, setTabBarWidth] = useState(0);

  useEffect(() => {
    const tabBar = tabBarRef.current;
    if (!tabBar) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setTabBarWidth(entry.contentRect.width);
      }
    });

    observer.observe(tabBar);
    return () => observer.disconnect();
  }, []);

  // Determine which labels to shorten based on available width
  // Shortening order (deterministic): Standard Library -> Parameters -> Structure -> Packages
  // Files, Parts, BOM always stay the same
  const getTabLabels = useCallback((width: number) => {
    // Thresholds tuned to allow tabs to get close together before shortening
    if (width < 340) {
      // Most compact: all shortened
      return {
        files: 'Files',
        packages: 'Pkgs',
        parts: 'Parts',
        stdlib: 'Lib',
        structure: 'Struct',
        parameters: 'Params',
        bom: 'BOM',
      };
    } else if (width < 380) {
      // Shorten: Standard Library, Parameters, Structure
      return {
        files: 'Files',
        packages: 'Pkgs',
        parts: 'Parts',
        stdlib: 'Lib',
        structure: 'Struct',
        parameters: 'Params',
        bom: 'BOM',
      };
    } else if (width < 420) {
      // Shorten: Standard Library, Parameters, Structure
      return {
        files: 'Files',
        packages: 'Packages',
        parts: 'Parts',
        stdlib: 'Lib',
        structure: 'Struct',
        parameters: 'Params',
        bom: 'BOM',
      };
    } else if (width < 480) {
      // Shorten: Standard Library, Parameters
      return {
        files: 'Files',
        packages: 'Packages',
        parts: 'Parts',
        stdlib: 'Lib',
        structure: 'Structure',
        parameters: 'Params',
        bom: 'BOM',
      };
    } else if (width < 560) {
      // Shorten: Standard Library only
      return {
        files: 'Files',
        packages: 'Packages',
        parts: 'Parts',
        stdlib: 'Lib',
        structure: 'Structure',
        parameters: 'Parameters',
        bom: 'BOM',
      };
    }
    // Full labels
    return {
      files: 'Files',
      packages: 'Packages',
      parts: 'Parts',
      stdlib: 'Standard Library',
      structure: 'Structure',
      parameters: 'Parameters',
      bom: 'BOM',
    };
  }, []);

  const tabLabels = useMemo(() => getTabLabels(tabBarWidth), [getTabLabels, tabBarWidth]);

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
    panels.collapseAllExceptProjects();
    action('build', { projectRoot, targets: [targetName] });
  }, [panels]);

  const handleBuildAllTargets = useCallback((projectRoot: string, projectName: string) => {
    panels.collapseAllExceptProjects();
    action('build', { level: 'project', id: projectRoot, label: projectName, targets: [] });
  }, [panels]);

  // Generate manufacturing data - triggers a build which includes manufacturing outputs
  const handleGenerateManufacturingData = useCallback((projectRoot: string, targetName: string) => {
    // Manufacturing data is generated as part of the build process
    // The build outputs include gerbers, BOM, and pick-and-place files
    panels.collapseAllExceptProjects();
    action('build', { projectRoot, targets: [targetName] });
  }, [panels]);

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
              // Select the newly created target
              useStore.getState().setSelectedTargets([data.name]);
            }}
            onGenerateManufacturingData={handleGenerateManufacturingData}
            queuedBuilds={queuedBuilds}
            onCancelBuild={handlers.handleCancelQueuedBuild}
          />
        </CollapsibleSection>

        {/* Tabbed Panels Section */}
        <div className="tabbed-panels">
          <div className="tab-bar" ref={tabBarRef}>
            <button
              className={`tab-button ${activeTab === 'files' ? 'active' : ''}`}
              onClick={() => setActiveTab('files')}
              title="Files"
            >
              {tabLabels.files}
            </button>
            <button
              className={`tab-button ${activeTab === 'packages' ? 'active' : ''}`}
              onClick={() => setActiveTab('packages')}
              title="Packages"
            >
              {tabLabels.packages}
              {isLoadingPackages && <span className="tab-loading" />}
            </button>
            <button
              className={`tab-button ${activeTab === 'parts' ? 'active' : ''}`}
              onClick={() => setActiveTab('parts')}
              title="Parts"
            >
              {tabLabels.parts}
            </button>
            <button
              className={`tab-button ${activeTab === 'stdlib' ? 'active' : ''}`}
              onClick={() => setActiveTab('stdlib')}
              title="Standard Library"
            >
              {tabLabels.stdlib}
            </button>
            <button
              className={`tab-button ${activeTab === 'structure' ? 'active' : ''}`}
              onClick={() => setActiveTab('structure')}
              title="Structure"
            >
              {tabLabels.structure}
            </button>
            <button
              className={`tab-button ${activeTab === 'parameters' ? 'active' : ''}`}
              onClick={() => setActiveTab('parameters')}
              title="Parameters"
            >
              {tabLabels.parameters}
            </button>
            <button
              className={`tab-button ${activeTab === 'bom' ? 'active' : ''}`}
              onClick={() => setActiveTab('bom')}
              title="Bill of Materials"
            >
              {tabLabels.bom}
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'files' && (
              <FileExplorerPanel
                projectRoot={selectedProjectRoot}
              />
            )}
            {activeTab === 'packages' && (
              <PackagesPanel
                packages={packages || []}
                installedDependencies={selectedProjectRoot ? (projectDependencies?.[selectedProjectRoot] || []) : []}
                selectedProjectRoot={selectedProjectRoot}
                installError={installError}
                onOpenPackageDetail={handlers.handleOpenPackageDetail}
              />
            )}
            {activeTab === 'parts' && (
              <PartsSearchPanel
                selectedProjectRoot={selectedProjectRoot}
                onOpenPartDetail={handlers.handleOpenPartDetail}
              />
            )}
            {activeTab === 'stdlib' && (
              <StandardLibraryPanel
                items={stdlibItems}
                isLoading={isLoadingStdlib}
                onRefresh={handleRefreshStdlib}
              />
            )}
            {activeTab === 'structure' && (
              <StructurePanel
                activeFilePath={activeEditorFile}
                lastAtoFile={lastAtoFile}
                projects={projects || []}
                onRefreshStructure={handlers.handleStructureRefresh}
              />
            )}
            {activeTab === 'parameters' && (
              <VariablesPanel
                variablesData={currentVariablesData}
                isLoading={isLoadingVariables}
                error={variablesError}
                selectedTargetName={selectedTargetName}
                hasActiveProject={!!selectedProjectRoot}
              />
            )}
            {activeTab === 'bom' && (
              <BOMPanel
                bomData={bomData}
                isLoading={isLoadingBom}
                error={bomError}
                selectedProjectRoot={selectedProjectRoot}
                selectedTargetNames={selectedTargetNames}
                onGoToSource={handleGoToSource}
              />
            )}
          </div>
        </div>
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
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <div className="disconnected-title">Internal Server Error</div>
            <div className="disconnected-message">
              {isVsCodeWebview() && (
                <button
                  className="disconnected-menu-button"
                  onClick={() => postMessage({ type: 'showBackendMenu' })}
                >
                  Open Troubleshooting Menu
                </button>
              )}
              <p className="disconnected-discord">
                Need help? <a href="https://discord.gg/CRe5xaDBr3" target="_blank" rel="noopener noreferrer">Join our Discord</a>
              </p>
              <div className="disconnected-troubleshooting">
                <p className="disconnected-troubleshooting-header">Troubleshooting Steps</p>
                <p>Use <code>Clear Logs</code> from the menu above</p>
                <p>Use <code>Restart Extension Host</code> from the menu above</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
