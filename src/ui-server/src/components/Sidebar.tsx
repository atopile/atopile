/**
 * Sidebar component - Main panel with all sections.
 * Uses unified panel sizing system for consistent expand/collapse behavior.
 */

import { useState, useRef, useMemo, useCallback } from 'react';
import { CollapsibleSection } from './CollapsibleSection';
import { ProjectsPanel } from './ProjectsPanel';
import { ProblemsPanel } from './ProblemsPanel';
import { StandardLibraryPanel } from './StandardLibraryPanel';
import { VariablesPanel } from './VariablesPanel';
import { BOMPanel } from './BOMPanel';
import { PackageDetailPanel } from './PackageDetailPanel';
import { BuildQueuePanel } from './BuildQueuePanel';
import { sendAction } from '../api/websocket';
import { useStore } from '../store';
import { usePanelSizing } from '../hooks/usePanelSizing';
import {
  SidebarHeader,
  useSidebarData,
  useSidebarEffects,
  useSidebarHandlers,
  type Selection,
  type SelectedPackage,
  type StageFilter,
} from './sidebar-modules';
import './Sidebar.css';
import '../styles.css';
import type { VariableNode, Problem } from '../types/build';

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
  const projectFiles = useStore((s) => s.projectFiles);
  const projectDependencies = useStore((s) => s.projectDependencies);
  const updatingDependencyIds = useStore((s) => s.updatingDependencyIds);
  const atopile = useStore((s) => s.atopile);
  const developerMode = useStore((s) => s.developerMode);

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
  const [selection, setSelection] = useState<Selection>({ type: 'none' });
  const [selectedPackage, setSelectedPackage] = useState<SelectedPackage | null>(null);
  const [activeStageFilter, setActiveStageFilter] = useState<StageFilter | null>(null);

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

  const projectsForProblems = useMemo(
    () => projects?.map(p => ({ id: p.root, name: p.name, root: p.root })) || [],
    [projects]
  );

  // Use data transformation hook
  const {
    projects: sidebarProjects,
    projectCount,
    packageCount,
    queuedBuilds,
    filteredProblems,
    totalErrors,
    totalWarnings,
  } = useSidebarData({ state, selection, activeStageFilter });

  // Unified panel sizing - all panels start collapsed, auto-expand on events
  const panels = usePanelSizing({
    containerRef,
    hasActiveBuilds: queuedBuilds.length > 0,
    hasProjectSelected: !!selectedProjectRoot,
  });

  // Use effects hook for side effects (data fetching, etc.)
  useSidebarEffects({
    selectedProjectRoot,
    selectedTargetName,
    panels,
  });

  // Use handlers hook for event handlers
  const handlers = useSidebarHandlers({
    projects: sidebarProjects,
    state,
    panels,
    setSelection,
    setSelectedPackage,
    setActiveStageFilter,
    action,
  });

  // Memoized callbacks for event handlers (avoid new function references each render)
  const handleFileClick = useCallback((projectId: string, filePath: string) => {
    const project = sidebarProjects?.find(p => p.id === projectId);
    const projectRoot = project?.root || (projectId.startsWith('/') ? projectId : null);
    if (projectRoot) {
      const fullPath = `${projectRoot}/${filePath}`;
      action('openFile', { file: fullPath });
    }
  }, [sidebarProjects]);

  const handleRemoveDependency = useCallback((projectId: string, identifier: string) => {
    action('removePackage', { projectRoot: projectId, packageId: identifier });
  }, []);

  const handleProblemClick = useCallback((problem: Problem) => {
    if (problem.file) {
      action('openFile', { file: problem.file, line: problem.line, column: problem.column });
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

  const handlePackageInstall = useCallback((version?: string) => {
    if (!selectedPackage) return;
    const projectRoot = selectedProjectRoot || sidebarProjects?.[0]?.root;
    if (projectRoot) {
      action('installPackage', {
        packageId: selectedPackage.fullName,
        projectRoot,
        version
      });
    }
  }, [selectedPackage, selectedProjectRoot, sidebarProjects]);

  const handlePackageBuild = useCallback((entry?: string) => {
    if (!selectedPackage) return;
    const projectRoot = selectedProjectRoot || sidebarProjects?.[0]?.root;
    if (projectRoot) {
      action('buildPackage', {
        packageId: selectedPackage.fullName,
        projectRoot,
        entry
      });
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
        developerMode={developerMode}
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
          <ProjectsPanel
            selection={selection}
            onSelect={handlers.handleSelect}
            onBuild={handlers.handleBuild}
            onCancelBuild={handlers.handleCancelBuild}
            onStageFilter={handlers.handleStageFilter}
            onCreateProject={handlers.handleCreateProject}
            onProjectExpand={handlers.handleProjectExpand}
            onOpenSource={handlers.handleOpenSource}
            onOpenKiCad={handlers.handleOpenKiCad}
            onOpenLayout={handlers.handleOpenLayout}
            onOpen3D={handlers.handleOpen3D}
            onFileClick={handleFileClick}
            onAddBuild={handlers.handleAddBuild}
            onUpdateBuild={handlers.handleUpdateBuild}
            onDeleteBuild={handlers.handleDeleteBuild}
            filterType="projects"
            projects={sidebarProjects}
            projectModules={projectModules || {}}
            projectFiles={projectFiles || {}}
            projectDependencies={projectDependencies || {}}
            onDependencyVersionChange={handlers.handleDependencyVersionChange}
            onRemoveDependency={handleRemoveDependency}
            updatingDependencyIds={updatingDependencyIds || []}
          />
        </CollapsibleSection>

        {/* Build Queue Section */}
        <CollapsibleSection
          id="buildQueue"
          title="Build Queue"
          badge={queuedBuilds.length > 0 ? queuedBuilds.length : undefined}
          badgeType="count"
          collapsed={panels.isCollapsed('buildQueue')}
          onToggle={() => panels.togglePanel('buildQueue')}
          height={panels.calculatedHeights['buildQueue']}
          onResizeStart={(e) => panels.handleResizeStart('buildQueue', e)}
        >
          <BuildQueuePanel
            builds={queuedBuilds}
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
          <ProjectsPanel
            selection={selection}
            onSelect={handlers.handleSelect}
            onBuild={handlers.handleBuild}
            onCancelBuild={handlers.handleCancelBuild}
            onStageFilter={handlers.handleStageFilter}
            onOpenPackageDetail={handlers.handleOpenPackageDetail}
            onPackageInstall={handlers.handlePackageInstall}
            onOpenSource={handlers.handleOpenSource}
            onOpenKiCad={handlers.handleOpenKiCad}
            onOpenLayout={handlers.handleOpenLayout}
            onOpen3D={handlers.handleOpen3D}
            filterType="packages"
            projects={sidebarProjects}
            installingPackageIds={installingPackageIds}
          />
        </CollapsibleSection>

        {/* Problems Section */}
        <CollapsibleSection
          id="problems"
          title={activeStageFilter ? `Problems: ${activeStageFilter.stageName || activeStageFilter.buildId || 'Filtered'}` : 'Problems'}
          badge={activeStageFilter ? filteredProblems.length : (totalErrors + totalWarnings)}
          badgeType={activeStageFilter ? 'filter' : 'count'}
          errorCount={activeStageFilter ? undefined : totalErrors}
          warningCount={activeStageFilter ? undefined : totalWarnings}
          collapsed={panels.isCollapsed('problems')}
          onToggle={() => panels.togglePanel('problems')}
          onClearFilter={activeStageFilter ? handlers.clearStageFilter : undefined}
          height={panels.calculatedHeights['problems']}
          onResizeStart={(e) => panels.handleResizeStart('problems', e)}
        >
          <ProblemsPanel
            problems={filteredProblems}
            projects={projectsForProblems}
            selectedProjectRoot={selectedProjectRoot}
            onSelectProject={handlers.handleSelectProject}
            onProblemClick={handleProblemClick}
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
            projects={projects}
            selectedProjectRoot={selectedProjectRoot}
            selectedTargetNames={selectedTargetNames}
            onSelectProject={handlers.handleSelectProject}
            onSelectTarget={handlers.handleSelectTarget}
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
            projects={projects}
            selectedProjectRoot={selectedProjectRoot}
            selectedTargetNames={selectedTargetNames}
            onSelectProject={handlers.handleSelectProject}
            onSelectTarget={handlers.handleSelectTarget}
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
            onBuild={handlePackageBuild}
          />
        </div>
      )}
    </div>
  );
}
