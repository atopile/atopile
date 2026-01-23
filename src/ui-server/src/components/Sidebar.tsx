/**
 * Sidebar component - Main panel with all sections.
 * Uses unified panel sizing system for consistent expand/collapse behavior.
 */

import { useState, useRef, useMemo } from 'react';
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
  // State from UI store (synced from backend)
  const state = useStore((s) => s);

  const selectedProjectRoot = state?.selectedProjectRoot ?? null;
  const selectedTargetNames = state?.selectedTargetNames ?? [];
  const selectedTargetName = useMemo(() => {
    if (!selectedProjectRoot) return null;
    if (selectedTargetNames.length > 0) return selectedTargetNames[0];
    const project = state?.projects?.find((p) => p.root === selectedProjectRoot);
    return project?.targets?.[0]?.name ?? null;
  }, [selectedProjectRoot, selectedTargetNames, state?.projects]);

  // Local UI state
  const [selection, setSelection] = useState<Selection>({ type: 'none' });
  const [selectedPackage, setSelectedPackage] = useState<SelectedPackage | null>(null);
  const [activeStageFilter, setActiveStageFilter] = useState<StageFilter | null>(null);

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);

  // Use data transformation hook
  const {
    projects,
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
    action,
  });

  // Use handlers hook for event handlers
  const handlers = useSidebarHandlers({
    projects,
    state,
    panels,
    setSelection,
    setSelectedPackage,
    setActiveStageFilter,
    action,
  });

  // Loading state
  if (!state) {
    return <div className="sidebar loading">Loading...</div>;
  }

  return (
    <div className={`unified-layout ${selectedPackage ? 'package-detail-open' : ''}`}>
      {/* Header with settings */}
      <SidebarHeader
        atopile={state?.atopile}
        developerMode={state?.developerMode}
      />

      <div className="panel-sections" ref={containerRef}>
        {/* Projects Section */}
        <CollapsibleSection
          id="projects"
          title="Projects"
          badge={projectCount}
          loading={state?.isLoadingProjects}
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
            onFileClick={(projectId, filePath) => {
              const project = projects.find(p => p.id === projectId);
              if (project) {
                const fullPath = `${project.root}/${filePath}`;
                action('openFile', { file: fullPath });
              }
            }}
            onAddBuild={handlers.handleAddBuild}
            onUpdateBuild={handlers.handleUpdateBuild}
            onDeleteBuild={handlers.handleDeleteBuild}
            filterType="projects"
            projects={projects}
            projectModules={state?.projectModules || {}}
            projectFiles={state?.projectFiles || {}}
            projectDependencies={state?.projectDependencies || {}}
            onDependencyVersionChange={handlers.handleDependencyVersionChange}
            onRemoveDependency={(projectId, identifier) => {
              action('removePackage', { projectRoot: projectId, packageId: identifier });
            }}
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
          loading={state?.isLoadingPackages}
          warningMessage={state?.packagesError || null}
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
            projects={projects}
            installingPackageIds={state?.installingPackageIds}
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
            projects={state?.projects?.map(p => ({ id: p.root, name: p.name, root: p.root })) || []}
            selectedProjectRoot={selectedProjectRoot}
            onSelectProject={handlers.handleSelectProject}
            onProblemClick={(problem) => {
              action('openFile', { file: problem.file, line: problem.line, column: problem.column });
            }}
          />
        </CollapsibleSection>

        {/* Standard Library Section */}
        <CollapsibleSection
          id="stdlib"
          title="Standard Library"
          badge={state?.stdlibItems?.length || 0}
          collapsed={panels.isCollapsed('stdlib')}
          onToggle={() => panels.togglePanel('stdlib')}
          height={panels.calculatedHeights['stdlib']}
          onResizeStart={(e) => panels.handleResizeStart('stdlib', e)}
        >
          <StandardLibraryPanel
            items={state?.stdlibItems}
            isLoading={state?.isLoadingStdlib}
            onRefresh={() => action('refreshStdlib')}
          />
        </CollapsibleSection>

        {/* Variables Section */}
        <CollapsibleSection
          id="variables"
          title="Variables"
          badge={(() => {
            const varData = state?.currentVariablesData;
            if (!varData?.nodes) return 0;
            const countVars = (nodes: typeof varData.nodes): number => {
              let count = 0;
              for (const n of nodes) {
                count += n.variables?.length || 0;
                if (n.children) count += countVars(n.children);
              }
              return count;
            };
            return countVars(varData.nodes);
          })()}
          collapsed={panels.isCollapsed('variables')}
          onToggle={() => panels.togglePanel('variables')}
          height={panels.calculatedHeights['variables']}
          onResizeStart={(e) => panels.handleResizeStart('variables', e)}
        >
          <VariablesPanel
            variablesData={state?.currentVariablesData}
            isLoading={state?.isLoadingVariables}
            error={state?.variablesError}
            projects={state?.projects}
            selectedProjectRoot={state?.selectedProjectRoot}
            selectedTargetNames={state?.selectedTargetNames}
            onSelectProject={handlers.handleSelectProject}
            onSelectTarget={handlers.handleSelectTarget}
          />
        </CollapsibleSection>

        {/* BOM Section */}
        <CollapsibleSection
          id="bom"
          title="BOM"
          badge={state?.bomData?.components?.length ?? 0}
          warningCount={
            state?.bomData?.components
              ? state.bomData.components.filter(c => c.stock !== null && c.stock === 0).length
              : 0
          }
          collapsed={panels.isCollapsed('bom')}
          onToggle={() => panels.togglePanel('bom')}
          height={panels.calculatedHeights['bom']}
          onResizeStart={(e) => panels.handleResizeStart('bom', e)}
        >
          <BOMPanel
            bomData={state?.bomData}
            isLoading={state?.isLoadingBom}
            error={state?.bomError}
            projects={state?.projects}
            selectedProjectRoot={state?.selectedProjectRoot}
            selectedTargetNames={state?.selectedTargetNames}
            onSelectProject={handlers.handleSelectProject}
            onSelectTarget={handlers.handleSelectTarget}
            onGoToSource={(path, line) => {
              action('openFile', { file: path, line });
            }}
          />
        </CollapsibleSection>
      </div>

      {/* Detail Panel (slides in when package selected) */}
      {selectedPackage && (
        <div className="detail-panel-container">
          <PackageDetailPanel
            package={selectedPackage}
            packageDetails={state?.selectedPackageDetails || null}
            isLoading={state?.isLoadingPackageDetails || false}
            isInstalling={state?.installingPackageIds?.includes(selectedPackage.fullName) || false}
            installError={state?.installError || null}
            error={state?.packageDetailsError || null}
            onClose={() => {
              setSelectedPackage(null);
              action('clearPackageDetails');
            }}
            onInstall={(version) => {
              const projectRoot = state?.selectedProjectRoot || (state?.projects?.[0]?.root);
              if (projectRoot) {
                action('installPackage', {
                  packageId: selectedPackage.fullName,
                  projectRoot,
                  version
                });
              }
            }}
            onBuild={(entry?: string) => {
              const projectRoot = state?.selectedProjectRoot || (state?.projects?.[0]?.root);
              if (projectRoot) {
                action('buildPackage', {
                  packageId: selectedPackage.fullName,
                  projectRoot,
                  entry
                });
              }
            }}
          />
        </div>
      )}
    </div>
  );
}
