/**
 * Sidebar Handlers Hook
 * Event handlers for the Sidebar component
 */

import { sendActionWithResponse } from '../../api/websocket';
import { api } from '../../api/client';
import { useStore } from '../../store';
import type { Selection, SelectedPackage, StageFilter } from './sidebarUtils';
import type { PanelId } from '../../utils/panelConfig';

interface PanelControls {
  expandPanel: (id: PanelId) => void;
  collapsePanel: (id: PanelId) => void;
  togglePanel: (id: PanelId) => void;
}

interface UseSidebarHandlersProps {
  projects: any[];
  state: any;
  panels: PanelControls;
  setSelection: React.Dispatch<React.SetStateAction<Selection>>;
  setSelectedPackage: React.Dispatch<React.SetStateAction<SelectedPackage | null>>;
  setActiveStageFilter: React.Dispatch<React.SetStateAction<StageFilter | null>>;
  action: (name: string, data?: Record<string, unknown>) => void;
}

export function useSidebarHandlers({
  projects,
  state,
  panels,
  setSelection,
  setSelectedPackage,
  setActiveStageFilter,
  action,
}: UseSidebarHandlersProps) {

  const handleSelect = (sel: Selection) => {
    setSelection(sel);

    if (sel.type === 'project' || sel.type === 'build' || sel.type === 'symbol') {
      const project = projects.find(p => p.id === sel.projectId);
      const projectRoot = project?.root || project?.path;
      if (projectRoot) {
        useStore.getState().setSelectedTargets([]);
        useStore.getState().selectProject(projectRoot);
      }
    }
  };

  const handleSelectProject = (projectRoot: string | null) => {
    useStore.getState().selectProject(projectRoot);
    useStore.getState().setSelectedTargets([]);
  };

  const handleSelectTarget = (projectRoot: string, targetName: string) => {
    useStore.getState().selectProject(projectRoot);
    useStore.getState().setSelectedTargets([targetName]);
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

    // Expand problems panel when filtering
    panels.expandPanel('problems');
  };

  const clearStageFilter = () => {
    setActiveStageFilter(null);
  };

  const handleOpenPackageDetail = (pkg: SelectedPackage) => {
    setSelectedPackage(pkg);
    useStore.getState().setLoadingPackageDetails(true);
    api.packages
      .details(pkg.fullName)
      .then((details) => useStore.getState().setPackageDetails(details))
      .catch((error) => {
        useStore.getState().setPackageDetailsError(
          error instanceof Error ? error.message : String(error)
        );
      });
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
      useStore.getState().setLoadingModules(true);
      api.modules
        .list(projectRoot)
        .then((result) => useStore.getState().setProjectModules(projectRoot, result.modules))
        .catch((error) => {
          console.error('Failed to fetch modules:', error);
          useStore.getState().setLoadingModules(false);
        });
    }
    const files = state?.projectFiles?.[projectRoot];
    if (projectRoot && (!files || files.length === 0)) {
      useStore.getState().setLoadingFiles(true);
      api.files
        .list(projectRoot)
        .then((result) => useStore.getState().setProjectFiles(projectRoot, result.files))
        .catch((error) => {
          console.error('Failed to fetch files:', error);
          useStore.getState().setLoadingFiles(false);
        });
    }
    const deps = state?.projectDependencies?.[projectRoot];
    if (projectRoot && (!deps || deps.length === 0)) {
      useStore.getState().setLoadingDependencies(true);
      api.dependencies
        .list(projectRoot)
        .then((result) => useStore.getState().setProjectDependencies(projectRoot, result.dependencies))
        .catch((error) => {
          console.error('Failed to fetch dependencies:', error);
          useStore.getState().setLoadingDependencies(false);
        });
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
    const store = useStore.getState();

    // Mark as updating
    store.addUpdatingDependency(projectId, identifier);

    try {
      // First update the config file
      const response = await sendActionWithResponse('updateDependencyVersion', {
        project_root: projectId,
        identifier,
        new_version: newVersion,
      });

      if (response.result?.success) {
        // Then install the updated version
        await sendActionWithResponse('installPackage', {
          packageId: identifier,
          projectRoot: projectId,
          version: newVersion,
        });

        // Refresh dependencies after install completes
        try {
          const result = await api.dependencies.list(projectId);
          useStore.getState().setProjectDependencies(projectId, result.dependencies);
        } catch (error) {
          console.error('Failed to refresh dependencies:', error);
        }
      } else {
        console.error('Failed to update dependency version:', response.result?.message);
      }
    } catch (error) {
      console.error('Failed to update dependency version:', error);
    } finally {
      // Mark as done
      store.removeUpdatingDependency(projectId, identifier);
    }
  };

  return {
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
  };
}
