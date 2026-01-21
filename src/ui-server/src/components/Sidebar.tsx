/**
 * Sidebar component - Main panel with all sections.
 * Based on the extension-mockup design.
 */

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { CollapsibleSection } from './CollapsibleSection';
import { ProjectsPanel } from './ProjectsPanel';
import { ProblemsPanel } from './ProblemsPanel';
import { StandardLibraryPanel } from './StandardLibraryPanel';
import { VariablesPanel } from './VariablesPanel';
import { BOMPanel } from './BOMPanel';
import { PackageDetailPanel } from './PackageDetailPanel';
import { BuildQueuePanel } from './BuildQueuePanel';
import { sendAction } from '../api/websocket';
import { api } from '../api/client';
import { useStore } from '../store';
import { SidebarHeader, useSidebarData, type Selection, type SelectedPackage, type StageFilter } from './sidebar-modules';
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
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set(['buildQueue', 'problems', 'stdlib', 'variables', 'bom']));
  const [sectionHeights, setSectionHeights] = useState<Record<string, number>>({});
  const [selectedPackage, setSelectedPackage] = useState<SelectedPackage | null>(null);
  const [activeStageFilter, setActiveStageFilter] = useState<StageFilter | null>(null);

  // Refs
  const bomRequestIdRef = useRef(0);
  const variablesRequestIdRef = useRef(0);
  const resizingRef = useRef<string | null>(null);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Use the data transformation hook
  const {
    projects,
    projectCount,
    packageCount,
    queuedBuilds,
    filteredProblems,
    totalErrors,
    totalWarnings,
  } = useSidebarData({ state, selection, activeStageFilter });

  // Allow external UI actions (e.g., open/close sections)
  useEffect(() => {
    const handleUiAction = (event: Event) => {
      const detail = (event as CustomEvent).detail as {
        type?: 'openSection' | 'closeSection' | 'toggleSection';
        sectionId?: string;
      };
      if (!detail?.sectionId || !detail?.type) return;

      const sectionId = detail.sectionId as string;
      setCollapsedSections((prev) => {
        const next = new Set(prev);
        if (detail.type === 'openSection') {
          next.delete(sectionId);
        } else if (detail.type === 'closeSection') {
          next.add(sectionId);
        } else if (detail.type === 'toggleSection') {
          if (next.has(sectionId)) {
            next.delete(sectionId);
          } else {
            next.add(sectionId);
          }
        }
        return next;
      });
    };

    window.addEventListener('atopile:ui_action', handleUiAction);
    return () => window.removeEventListener('atopile:ui_action', handleUiAction);
  }, []);

  // Initial data refresh after mount
  useEffect(() => {
    const timer = setTimeout(() => {
      action('refreshProblems');
      action('refreshPackages');
      action('refreshStdlib');
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  // Fetch BOM data when project or target selection changes
  useEffect(() => {
    if (!selectedProjectRoot) {
      useStore.getState().setBomData(null);
      useStore.getState().setBomError(null);
      return;
    }

    if (!selectedTargetName) {
      useStore.getState().setBomData(null);
      useStore.getState().setBomError('No build targets available for this project.');
      return;
    }

    const requestId = ++bomRequestIdRef.current;
    useStore.getState().setLoadingBom(true);
    useStore.getState().setBomError(null);

    api.bom
      .get(selectedProjectRoot, selectedTargetName)
      .then((data) => {
        if (requestId !== bomRequestIdRef.current) return;
        useStore.getState().setBomData(data);
      })
      .catch((error) => {
        if (requestId !== bomRequestIdRef.current) return;
        const message = error instanceof Error ? error.message : 'Failed to load BOM';
        useStore.getState().setBomData(null);
        useStore.getState().setBomError(message);
      });
  }, [selectedProjectRoot, selectedTargetName]);

  // Fetch Variables data when project or target selection changes
  useEffect(() => {
    if (!selectedProjectRoot) {
      useStore.getState().setVariablesData(null);
      useStore.getState().setVariablesError(null);
      return;
    }

    if (!selectedTargetName) {
      useStore.getState().setVariablesData(null);
      useStore.getState().setVariablesError('No build targets available for this project.');
      return;
    }

    const requestId = ++variablesRequestIdRef.current;
    useStore.getState().setLoadingVariables(true);
    useStore.getState().setVariablesError(null);

    api.variables
      .get(selectedProjectRoot, selectedTargetName)
      .then((data) => {
        if (requestId !== variablesRequestIdRef.current) return;
        useStore.getState().setVariablesData(data);
      })
      .catch((error) => {
        if (requestId !== variablesRequestIdRef.current) return;
        const message = error instanceof Error ? error.message : 'Failed to load variables';
        useStore.getState().setVariablesData(null);
        useStore.getState().setVariablesError(message);
      });
  }, [selectedProjectRoot, selectedTargetName]);

  // Handle package install action results
  useEffect(() => {
    const handleActionResult = (event: Event) => {
      const detail = (event as CustomEvent).detail as {
        action?: string;
        result?: {
          success?: boolean;
          error?: string;
        };
      };

      if (detail?.action === 'installPackage') {
        if (detail.result && !detail.result.success && detail.result.error) {
          useStore.getState().setInstallError(detail.result.error);
        }
      }
    };
    window.addEventListener('atopile:action_result', handleActionResult);
    return () => window.removeEventListener('atopile:action_result', handleActionResult);
  }, []);

  // Clear installing state when packages update (install completed)
  useEffect(() => {
    const installingId = state?.installingPackageId;
    if (!installingId) return;

    const pkg = state?.packages?.find(p =>
      p.identifier === installingId ||
      `${p.publisher}/${p.name}` === installingId
    );
    if (pkg?.installed) {
      useStore.getState().setInstallingPackage(null);
    }
  }, [state?.packages, state?.installingPackageId]);

  // Auto-expand: detect unused space and cropped sections
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const sectionIds = ['projects', 'packages', 'problems', 'stdlib', 'variables', 'bom'];
    let debounceTimeoutId: ReturnType<typeof setTimeout> | null = null;

    const checkAutoExpand = () => {
      const containerHeight = container.clientHeight;
      let totalUsedHeight = 0;
      let croppedSectionInfo: { id: string; neededHeight: number; currentHeight: number } | null = null;

      for (const id of sectionIds) {
        if (collapsedSections.has(id)) continue;

        const section = container.querySelector(`[data-section-id="${id}"]`) as HTMLElement;
        if (!section) continue;

        const sectionBody = section.querySelector('.section-body') as HTMLElement;
        const titleBar = section.querySelector('.section-title-bar') as HTMLElement;

        if (titleBar) totalUsedHeight += titleBar.offsetHeight;
        if (sectionBody) {
          const currentBodyHeight = sectionBody.offsetHeight;
          const contentHeight = sectionBody.scrollHeight;
          totalUsedHeight += currentBodyHeight;

          const isOverflowing = contentHeight > currentBodyHeight + 5;

          if (isOverflowing && !croppedSectionInfo) {
            croppedSectionInfo = {
              id,
              neededHeight: contentHeight - currentBodyHeight,
              currentHeight: section.offsetHeight,
            };
          }
        }

        const resizeHandle = section.querySelector('.section-resize-handle') as HTMLElement;
        if (resizeHandle) totalUsedHeight += resizeHandle.offsetHeight;

        totalUsedHeight += 1;
      }

      const unusedSpace = containerHeight - totalUsedHeight;
      if (unusedSpace > 20 && croppedSectionInfo) {
        const expandAmount = Math.min(unusedSpace, croppedSectionInfo.neededHeight);
        const newHeight = croppedSectionInfo.currentHeight + expandAmount;

        const currentSetHeight = sectionHeights[croppedSectionInfo.id];
        if (!currentSetHeight || Math.abs(currentSetHeight - newHeight) > 5) {
          setSectionHeights(prev => ({
            ...prev,
            [croppedSectionInfo!.id]: newHeight,
          }));
        }
      }
    };

    const debouncedCheckAutoExpand = () => {
      if (debounceTimeoutId !== null) {
        clearTimeout(debounceTimeoutId);
      }
      debounceTimeoutId = setTimeout(checkAutoExpand, 100);
    };

    const initialTimeoutId = setTimeout(checkAutoExpand, 150);

    const resizeObserver = new ResizeObserver(debouncedCheckAutoExpand);
    resizeObserver.observe(container);

    return () => {
      clearTimeout(initialTimeoutId);
      if (debounceTimeoutId !== null) {
        clearTimeout(debounceTimeoutId);
      }
      resizeObserver.disconnect();
    };
  }, [collapsedSections, sectionHeights]);

  // --- Event Handlers ---

  const toggleSection = (sectionId: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const handleSelect = (sel: Selection) => {
    setSelection(sel);

    if (sel.type === 'project' || sel.type === 'build' || sel.type === 'symbol') {
      const project = projects.find(p => p.id === sel.projectId);
      const projectRoot = project?.root;
      if (projectRoot) {
        action('selectProject', { projectRoot });
      }
    }
  };

  const handleBuild = (level: 'project' | 'build' | 'symbol', id: string, label: string) => {
    action('build', { level, id, label });
  };

  const handleCancelBuild = (buildId: string) => {
    action('cancelBuild', { buildId });
  };

  const handleCancelQueuedBuild = (build_id: string) => {
    action('cancelBuild', { buildId: build_id });
  };

  const handleStageFilter = (stageName: string, buildId?: string, projectId?: string) => {
    setActiveStageFilter({
      stageName: stageName || undefined,
      buildId,
      projectId
    });

    setCollapsedSections(prev => {
      const next = new Set(prev);
      next.delete('problems');
      return next;
    });
  };

  const clearStageFilter = () => {
    setActiveStageFilter(null);
  };

  const handleOpenPackageDetail = (pkg: SelectedPackage) => {
    setSelectedPackage(pkg);
    action('getPackageDetails', { packageId: pkg.fullName });
  };

  const handlePackageInstall = (packageId: string, projectRoot: string) => {
    useStore.getState().setInstallingPackage(packageId);
    action('installPackage', { packageId, projectRoot });
  };

  const handleCreateProject = (parentDirectory?: string, name?: string) => {
    action('createProject', { parentDirectory, name });
  };

  const handleProjectExpand = (projectRoot: string) => {
    const modules = state?.projectModules?.[projectRoot];
    if (projectRoot && (!modules || modules.length === 0)) {
      action('fetchModules', { projectRoot });
    }
    const files = state?.projectFiles?.[projectRoot];
    if (projectRoot && (!files || files.length === 0)) {
      action('fetchFiles', { projectRoot });
    }
    const deps = state?.projectDependencies?.[projectRoot];
    if (projectRoot && (!deps || deps.length === 0)) {
      action('fetchDependencies', { projectRoot });
    }
  };

  const handleOpenSource = (projectId: string, entry: string) => {
    action('openSource', { projectId, entry });
  };

  const handleOpenKiCad = (projectId: string, buildId: string) => {
    action('openKiCad', { projectId, buildId });
  };

  const handleOpenLayout = (projectId: string, buildId: string) => {
    action('openLayout', { projectId, buildId });
  };

  const handleOpen3D = (projectId: string, buildId: string) => {
    action('open3D', { projectId, buildId });
  };

  // --- Build Target Management ---

  const handleAddBuild = async (projectId: string) => {
    const modules = state?.projectModules?.[projectId] || [];
    const defaultModule = modules.find(m => m.name === 'App' || m.type === 'module') || modules[0];
    const defaultEntry = defaultModule?.entry || 'main.ato:App';

    const existingTargets = state?.projects?.find(p => p.root === projectId)?.targets || [];
    const existingNames = new Set(existingTargets.map(t => t.name));
    let newName = 'new-build';
    let counter = 1;
    while (existingNames.has(newName)) {
      newName = `new-build-${counter}`;
      counter++;
    }

    try {
      const result = await api.buildTargets.add(projectId, newName, defaultEntry);
      if (result.success) {
        action('refreshProjects');
      } else {
        console.error('Failed to add build target:', result.message);
      }
    } catch (error) {
      console.error('Failed to add build target:', error);
    }
  };

  const handleUpdateBuild = async (
    projectId: string,
    buildId: string,
    updates: { name?: string; entry?: string }
  ) => {
    const oldName = buildId;
    const newName = updates.name !== oldName ? updates.name : undefined;
    const newEntry = updates.entry;

    try {
      const result = await api.buildTargets.update(projectId, oldName, newName, newEntry);
      if (result.success) {
        action('refreshProjects');
      } else {
        console.error('Failed to update build target:', result.message);
      }
    } catch (error) {
      console.error('Failed to update build target:', error);
    }
  };

  const handleDeleteBuild = async (projectId: string, buildId: string) => {
    try {
      const result = await api.buildTargets.delete(projectId, buildId);
      if (result.success) {
        action('refreshProjects');
      } else {
        console.error('Failed to delete build target:', result.message);
      }
    } catch (error) {
      console.error('Failed to delete build target:', error);
    }
  };

  // --- Dependency Management ---

  const handleDependencyVersionChange = async (
    projectId: string,
    identifier: string,
    newVersion: string
  ) => {
    try {
      const result = await api.dependencies.updateVersion(projectId, identifier, newVersion);
      if (result.success) {
        action('fetchDependencies', { projectRoot: projectId });
      } else {
        console.error('Failed to update dependency version:', result.message);
      }
    } catch (error) {
      console.error('Failed to update dependency version:', error);
    }
  };

  // --- Resize Handlers ---

  const handleResizeStart = useCallback((sectionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    resizingRef.current = sectionId;
    startYRef.current = e.clientY;

    if (sectionHeights[sectionId]) {
      startHeightRef.current = sectionHeights[sectionId];
    } else {
      const section = (e.target as HTMLElement).closest('.collapsible-section');
      startHeightRef.current = section ? section.getBoundingClientRect().height : 200;
    }

    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
  }, [sectionHeights]);

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!resizingRef.current) return;

    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      const delta = e.clientY - startYRef.current;
      const newHeight = Math.max(100, startHeightRef.current + delta);
      setSectionHeights(prev => ({ ...prev, [resizingRef.current!]: newHeight }));
      rafRef.current = null;
    });
  }, []);

  const handleResizeEnd = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    resizingRef.current = null;
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
  }, [handleResizeMove]);

  // --- Render ---

  if (!state) {
    return <div className="sidebar loading">Loading...</div>;
  }

  return (
    <div className={`unified-layout ${selectedPackage ? 'package-detail-open' : ''}`}>
      {/* Header with logo and settings */}
      <SidebarHeader
        logoUri={state?.logoUri}
        version={state?.version}
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
          collapsed={collapsedSections.has('projects')}
          onToggle={() => toggleSection('projects')}
          height={sectionHeights.projects}
          maxHeight={sectionHeights.projects ? undefined : 350}
          onResizeStart={(e) => handleResizeStart('projects', e)}
        >
          <ProjectsPanel
            selection={selection}
            onSelect={handleSelect}
            onBuild={handleBuild}
            onCancelBuild={handleCancelBuild}
            onStageFilter={handleStageFilter}
            onCreateProject={handleCreateProject}
            onProjectExpand={handleProjectExpand}
            onOpenSource={handleOpenSource}
            onOpenKiCad={handleOpenKiCad}
            onOpenLayout={handleOpenLayout}
            onOpen3D={handleOpen3D}
            onFileClick={(projectId, filePath) => {
              const project = projects.find(p => p.id === projectId);
              if (project) {
                const fullPath = `${project.root}/${filePath}`;
                action('openFile', { file: fullPath });
              }
            }}
            onAddBuild={handleAddBuild}
            onUpdateBuild={handleUpdateBuild}
            onDeleteBuild={handleDeleteBuild}
            filterType="projects"
            projects={projects}
            projectModules={state?.projectModules || {}}
            projectFiles={state?.projectFiles || {}}
            projectDependencies={state?.projectDependencies || {}}
            onDependencyVersionChange={handleDependencyVersionChange}
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
          collapsed={collapsedSections.has('buildQueue')}
          onToggle={() => toggleSection('buildQueue')}
          height={collapsedSections.has('buildQueue') ? undefined : sectionHeights.buildQueue}
          onResizeStart={(e) => handleResizeStart('buildQueue', e)}
        >
          <BuildQueuePanel
            builds={queuedBuilds}
            onCancelBuild={handleCancelQueuedBuild}
          />
        </CollapsibleSection>

        {/* Packages Section */}
        <CollapsibleSection
          id="packages"
          title="Packages"
          badge={packageCount}
          loading={state?.isLoadingPackages}
          warningMessage={state?.packagesError || null}
          collapsed={collapsedSections.has('packages')}
          onToggle={() => toggleSection('packages')}
          height={sectionHeights.packages}
          maxHeight={sectionHeights.packages ? undefined : 350}
          onResizeStart={(e) => handleResizeStart('packages', e)}
        >
          <ProjectsPanel
            selection={selection}
            onSelect={handleSelect}
            onBuild={handleBuild}
            onCancelBuild={handleCancelBuild}
            onStageFilter={handleStageFilter}
            onOpenPackageDetail={handleOpenPackageDetail}
            onPackageInstall={handlePackageInstall}
            onOpenSource={handleOpenSource}
            onOpenKiCad={handleOpenKiCad}
            onOpenLayout={handleOpenLayout}
            onOpen3D={handleOpen3D}
            filterType="packages"
            projects={projects}
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
          collapsed={collapsedSections.has('problems')}
          onToggle={() => toggleSection('problems')}
          onClearFilter={activeStageFilter ? clearStageFilter : undefined}
          height={collapsedSections.has('problems') ? undefined : sectionHeights.problems}
          onResizeStart={(e) => handleResizeStart('problems', e)}
        >
          <ProblemsPanel
            problems={filteredProblems}
            projects={state?.projects?.map(p => ({ id: p.root, name: p.name, root: p.root })) || []}
            selectedProjectRoot={selectedProjectRoot}
            onSelectProject={(projectRoot) => {
              action('selectProject', { projectRoot });
            }}
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
          collapsed={collapsedSections.has('stdlib')}
          onToggle={() => toggleSection('stdlib')}
          height={collapsedSections.has('stdlib') ? undefined : sectionHeights.stdlib}
          onResizeStart={(e) => handleResizeStart('stdlib', e)}
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
            const varData = state?.currentVariablesData
            if (!varData?.nodes) return 0
            const countVars = (nodes: typeof varData.nodes): number => {
              let count = 0
              for (const n of nodes) {
                count += n.variables?.length || 0
                if (n.children) count += countVars(n.children)
              }
              return count
            }
            return countVars(varData.nodes)
          })()}
          collapsed={collapsedSections.has('variables')}
          onToggle={() => toggleSection('variables')}
          height={collapsedSections.has('variables') ? undefined : sectionHeights.variables}
          onResizeStart={(e) => handleResizeStart('variables', e)}
        >
          <VariablesPanel
            variablesData={state?.currentVariablesData}
            isLoading={state?.isLoadingVariables}
            error={state?.variablesError}
            projects={state?.projects}
            selectedProjectRoot={state?.selectedProjectRoot}
            onSelectProject={(projectRoot) => {
              useStore.getState().selectProject(projectRoot);
              if (projectRoot) {
                action('selectProject', { projectRoot });
              }
            }}
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
          collapsed={collapsedSections.has('bom')}
          onToggle={() => toggleSection('bom')}
          height={collapsedSections.has('bom') ? undefined : sectionHeights.bom}
          onResizeStart={(e) => handleResizeStart('bom', e)}
        >
          <BOMPanel
            bomData={state?.bomData}
            isLoading={state?.isLoadingBom}
            error={state?.bomError}
            projects={state?.projects}
            selectedProjectRoot={state?.selectedProjectRoot}
            onSelectProject={(projectRoot) => {
              useStore.getState().selectProject(projectRoot);
              if (projectRoot) {
                action('selectProject', { projectRoot });
              }
            }}
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
            isInstalling={state?.installingPackageId === selectedPackage.fullName}
            installError={state?.installError || null}
            error={state?.packageDetailsError || null}
            onClose={() => {
              setSelectedPackage(null);
              action('clearPackageDetails');
            }}
            onInstall={(version) => {
              const projectRoot = state?.selectedProjectRoot || (state?.projects?.[0]?.root);
              if (projectRoot) {
                useStore.getState().setInstallingPackage(selectedPackage.fullName);
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
