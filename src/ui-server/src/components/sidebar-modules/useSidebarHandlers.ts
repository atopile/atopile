/**
 * Sidebar Handlers Hook
 * Event handlers for the Sidebar component
 */

import { sendActionWithResponse } from '../../api/websocket';
import { useStore } from '../../store';
import type { Selection, SelectedPackage, SelectedPart } from './sidebarUtils';

interface UseSidebarHandlersProps {
  projects: any[];
  state: any;
  setSelection: React.Dispatch<React.SetStateAction<Selection>>;
  setSelectedPackage: React.Dispatch<React.SetStateAction<SelectedPackage | null>>;
  setSelectedPart: React.Dispatch<React.SetStateAction<SelectedPart | null>>;
  action: (name: string, data?: Record<string, unknown>) => void;
}

export function useSidebarHandlers({
  projects,
  state,
  setSelection,
  setSelectedPackage,
  setSelectedPart,
  action,
}: UseSidebarHandlersProps) {

  const handleSelect = (sel: Selection) => {
    setSelection(sel);

    if (sel.type === 'project' || sel.type === 'build' || sel.type === 'symbol') {
      const project = projects.find(p => p.id === sel.projectId);
      const projectRoot = project?.root || project?.path;
      if (projectRoot) {
        const coreProject = state?.projects?.find((p: any) => p.root === projectRoot);
        const defaultTarget = coreProject?.targets?.[0]?.name ?? null;
        const targetNames = defaultTarget ? [defaultTarget] : [];
        useStore.getState().setSelectedTargets(targetNames);
      }
    }
  };

  const handleSelectProject = (projectRoot: string | null) => {
    const project = state?.projects?.find((p: any) => p.root === projectRoot);
    const defaultTarget = project?.targets?.[0]?.name ?? null;
    const targetNames = defaultTarget ? [defaultTarget] : [];
    useStore.getState().selectProject(projectRoot);
    useStore.getState().setSelectedTargets(targetNames);
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

  const handleOpenPartDetail = (part: SelectedPart) => {
    setSelectedPart(part);
    setSelectedPackage(null);
  };

  const handleOpenPackageDetail = async (pkg: SelectedPackage) => {
    setSelectedPackage(pkg);
    setSelectedPart(null);
    const requestedVersion = pkg.latestVersion || pkg.version;
    const store = useStore.getState();
    store.setLoadingPackageDetails(true);
    store.setPackageDetails(null);
    useStore.setState({ packageDetailsError: null });
    try {
      const response = await sendActionWithResponse('getPackageDetails', {
        packageId: pkg.fullName,
        version: requestedVersion,
      });
      const result = response.result ?? {};
      const details = (result as { details?: unknown }).details || null;
      store.setPackageDetails(details as any);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load package details';
      useStore.setState({ packageDetailsError: message, isLoadingPackageDetails: false });
    }
  };

  const handlePackageInstall = (packageId: string, projectRoot: string, version?: string) => {
    action('installPackage', { packageId, projectRoot, version });
  };

  const handleCreateProject = async (data?: { name?: string; license?: string; description?: string; parentDirectory?: string }) => {
    const response = await sendActionWithResponse('createProject', data || {});
    if (!response.result?.success) {
      const errorMsg = response.result?.error || 'Failed to create project';
      throw new Error(errorMsg);
    }
    // Projects are refreshed by the backend automatically
  };

  const handleStructureRefresh = () => {
    // Structure panel triggers its own module introspection request.
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
    // Also fetch builds for installed dependencies (reads local ato.yaml)
    const builds = state?.projectBuilds?.[projectRoot];
    if (projectRoot && (!builds || builds.length === 0)) {
      action('fetchBuilds', { projectRoot });
    }
  };

  const handleOpenSource = (projectId: string, entry: string) => {
    action('openSource', { projectId, entry });
  };

  const handleOpenKiCad = (projectId: string, targetName: string) => {
    action('openKiCad', { projectId, targetName });
  };

  const handleOpenLayout = (projectId: string, targetName: string) => {
    action('openLayout', { projectId, targetName });
  };

  const handleOpen3D = (projectId: string, targetName: string) => {
    action('open3D', { projectId, targetName });
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
        action('fetchDependencies', { projectRoot: projectId });
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
    handleOpenPartDetail,
    handleOpenPackageDetail,
    handlePackageInstall,
    handleCreateProject,
    handleProjectExpand,
    handleStructureRefresh,
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
