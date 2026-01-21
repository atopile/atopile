/**
 * Sidebar Handlers Hook
 * Event handlers for the Sidebar component
 */

import { useCallback, useRef } from 'react';
import { api } from '../../api/client';
import { useStore } from '../../store';
import type { Selection, SelectedPackage, StageFilter } from './sidebarUtils';
import type { Project } from './useSidebarData';

interface UseSidebarHandlersProps {
  projects: Project[];
  state: ReturnType<typeof useStore> | null;
  sectionHeights: Record<string, number>;
  setSectionHeights: React.Dispatch<React.SetStateAction<Record<string, number>>>;
  setCollapsedSections: React.Dispatch<React.SetStateAction<Set<string>>>;
  setSelection: React.Dispatch<React.SetStateAction<Selection>>;
  setSelectedPackage: React.Dispatch<React.SetStateAction<SelectedPackage | null>>;
  setActiveStageFilter: React.Dispatch<React.SetStateAction<StageFilter | null>>;
  action: (name: string, data?: Record<string, unknown>) => void;
}

export function useSidebarHandlers({
  projects,
  state,
  sectionHeights,
  setSectionHeights,
  setCollapsedSections,
  setSelection,
  setSelectedPackage,
  setActiveStageFilter,
  action,
}: UseSidebarHandlersProps) {
  // Resize refs
  const resizingRef = useRef<string | null>(null);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  const toggleSection = useCallback((sectionId: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  }, [setCollapsedSections]);

  const handleSelect = useCallback((sel: Selection) => {
    setSelection(sel);

    if (sel.type === 'project' || sel.type === 'build' || sel.type === 'symbol') {
      const project = projects.find(p => p.id === sel.projectId);
      const projectRoot = project?.root;
      if (projectRoot) {
        action('selectProject', { projectRoot });
      }
    }
  }, [projects, action, setSelection]);

  const handleBuild = useCallback((level: 'project' | 'build' | 'symbol', id: string, label: string) => {
    action('build', { level, id, label });
  }, [action]);

  const handleCancelBuild = useCallback((buildId: string) => {
    action('cancelBuild', { buildId });
  }, [action]);

  const handleCancelQueuedBuild = useCallback((build_id: string) => {
    action('cancelBuild', { buildId: build_id });
  }, [action]);

  const handleStageFilter = useCallback((stageName: string, buildId?: string, projectId?: string) => {
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
  }, [setActiveStageFilter, setCollapsedSections]);

  const clearStageFilter = useCallback(() => {
    setActiveStageFilter(null);
  }, [setActiveStageFilter]);

  const handleOpenPackageDetail = useCallback((pkg: SelectedPackage) => {
    setSelectedPackage(pkg);
    action('getPackageDetails', { packageId: pkg.fullName });
  }, [action, setSelectedPackage]);

  const handlePackageInstall = useCallback((packageId: string, projectRoot: string) => {
    useStore.getState().setInstallingPackage(packageId);
    action('installPackage', { packageId, projectRoot });
  }, [action]);

  const handleCreateProject = useCallback((parentDirectory?: string, name?: string) => {
    action('createProject', { parentDirectory, name });
  }, [action]);

  const handleProjectExpand = useCallback((projectRoot: string) => {
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
  }, [state, action]);

  const handleOpenSource = useCallback((projectId: string, entry: string) => {
    action('openSource', { projectId, entry });
  }, [action]);

  const handleOpenKiCad = useCallback((projectId: string, buildId: string) => {
    action('openKiCad', { projectId, buildId });
  }, [action]);

  const handleOpenLayout = useCallback((projectId: string, buildId: string) => {
    action('openLayout', { projectId, buildId });
  }, [action]);

  const handleOpen3D = useCallback((projectId: string, buildId: string) => {
    action('open3D', { projectId, buildId });
  }, [action]);

  // Build Target Management
  const handleAddBuild = useCallback(async (projectId: string) => {
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
  }, [state, action]);

  const handleUpdateBuild = useCallback(async (
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
  }, [action]);

  const handleDeleteBuild = useCallback(async (projectId: string, buildId: string) => {
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
  }, [action]);

  // Dependency Management
  const handleDependencyVersionChange = useCallback(async (
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
  }, [action]);

  // Resize Handlers
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
  }, [setSectionHeights]);

  const handleResizeEnd = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    resizingRef.current = null;
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
  }, [handleResizeMove]);

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
  }, [sectionHeights, handleResizeMove, handleResizeEnd]);

  return {
    toggleSection,
    handleSelect,
    handleBuild,
    handleCancelBuild,
    handleCancelQueuedBuild,
    handleStageFilter,
    clearStageFilter,
    handleOpenPackageDetail,
    handlePackageInstall,
    handleCreateProject,
    handleProjectExpand,
    handleOpenSource,
    handleOpenKiCad,
    handleOpenLayout,
    handleOpen3D,
    handleAddBuild,
    handleUpdateBuild,
    handleDeleteBuild,
    handleDependencyVersionChange,
    handleResizeStart,
  };
}
