/**
 * Sidebar Handlers Hook
 * Event handlers for the Sidebar component
 */

import { useCallback, useRef } from 'react';
import { sendActionWithResponse } from '../../api/websocket';
import { useStore } from '../../store';
import type { Selection, SelectedPackage, StageFilter } from './sidebarUtils';

interface UseSidebarHandlersProps {
  projects: any[];
  state: any;
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

  // Simple handlers - no useCallback needed
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
      const projectRoot = project?.root || project?.path;
      if (projectRoot) {
        useStore.getState().setSelectedTargets([]);
        action('setSelectedTargets', { targetNames: [] });
        action('selectProject', { projectRoot });
      }
    }
  };

  const handleSelectProject = (projectRoot: string | null) => {
    useStore.getState().selectProject(projectRoot);
    useStore.getState().setSelectedTargets([]);
    action('selectProject', { projectRoot });
    action('setSelectedTargets', { targetNames: [] });
  };

  const handleSelectTarget = (projectRoot: string, targetName: string) => {
    useStore.getState().selectProject(projectRoot);
    useStore.getState().setSelectedTargets([targetName]);
    action('selectProject', { projectRoot });
    action('setSelectedTargets', { targetNames: [targetName] });
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

  const handlePackageInstall = (packageId: string, projectRoot: string, version?: string) => {
    useStore.getState().addInstallingPackage(packageId);
    action('installPackage', { packageId, projectRoot, version });
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

  // Build Target Management
  const handleAddBuild = async (projectId: string) => {
    const modules = state?.projectModules?.[projectId] || [];
    const defaultModule = modules.find((m: any) => m.name === 'App' || m.type === 'module') || modules[0];
    const defaultEntry = defaultModule?.entry || 'main.ato:App';

    const existingTargets = state?.projects?.find((p: any) => p.root === projectId)?.targets || [];
    const existingNames = new Set(existingTargets.map((t: any) => t.name));
    let newName = 'new-build';
    let counter = 1;
    while (existingNames.has(newName)) {
      newName = `new-build-${counter}`;
      counter++;
    }

    try {
      const response = await sendActionWithResponse('addBuildTarget', {
        project_root: projectId,
        name: newName,
        entry: defaultEntry,
      });
      if (response.result?.success) {
        action('refreshProjects');
      } else {
        console.error('Failed to add build target:', response.result?.message);
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
      const response = await sendActionWithResponse('updateBuildTarget', {
        project_root: projectId,
        old_name: oldName,
        new_name: newName,
        new_entry: newEntry,
      });
      if (response.result?.success) {
        action('refreshProjects');
      } else {
        console.error('Failed to update build target:', response.result?.message);
      }
    } catch (error) {
      console.error('Failed to update build target:', error);
    }
  };

  const handleDeleteBuild = async (projectId: string, buildId: string) => {
    try {
      const response = await sendActionWithResponse('deleteBuildTarget', {
        project_root: projectId,
        name: buildId,
      });
      if (response.result?.success) {
        action('refreshProjects');
      } else {
        console.error('Failed to delete build target:', response.result?.message);
      }
    } catch (error) {
      console.error('Failed to delete build target:', error);
    }
  };

  // Dependency Management
  const handleDependencyVersionChange = async (
    projectId: string,
    identifier: string,
    newVersion: string
  ) => {
    try {
      const response = await sendActionWithResponse('updateDependencyVersion', {
        project_root: projectId,
        identifier,
        new_version: newVersion,
      });
      if (response.result?.success) {
        action('fetchDependencies', { projectRoot: projectId });
      } else {
        console.error('Failed to update dependency version:', response.result?.message);
      }
    } catch (error) {
      console.error('Failed to update dependency version:', error);
    }
  };

  // Resize Handlers - KEEP useCallback: added as document event listeners
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
    handleSelectProject,
    handleSelectTarget,
    handleResizeStart,
  };
}
