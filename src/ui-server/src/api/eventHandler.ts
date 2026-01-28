import { api } from './client';
import { useStore } from '../store';
import type { AppState } from '../types/build';

type AtopileConfig = AppState['atopile'];

function normalizeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  return 'Unknown error';
}

async function fetchProjects(): Promise<void> {
  const store = useStore.getState();
  store.setLoadingProjects(true);
  store.setProjectsError(null);
  try {
    const result = await api.projects.list();
    store.setProjects(result.projects);
  } catch (error) {
    store.setProjectsError(normalizeError(error));
  }
}

async function fetchBuilds(): Promise<void> {
  const store = useStore.getState();
  try {
    const [history, active] = await Promise.all([
      api.builds.history(),
      api.builds.active(),
    ]);
    store.setBuilds(history.builds);
    store.setQueuedBuilds(active.builds);
  } catch (error) {
    console.error('[events] Failed to fetch builds:', error);
  }
}

async function fetchPackages(): Promise<void> {
  const store = useStore.getState();
  store.setLoadingPackages(true);
  store.setPackagesError(null);
  try {
    const result = await api.packages.summary();
    store.setPackages(result.packages);
    store.clearInstallingPackages();
  } catch (error) {
    store.setPackagesError(normalizeError(error));
  }
}

async function fetchStdlib(): Promise<void> {
  const store = useStore.getState();
  store.setLoadingStdlib(true);
  try {
    const result = await api.stdlib.list();
    store.setStdlibItems(result.items);
  } catch (error) {
    console.error('[events] Failed to fetch stdlib:', error);
    store.setLoadingStdlib(false);
  }
}

async function fetchProblems(): Promise<void> {
  const store = useStore.getState();
  store.setLoadingProblems(true);
  try {
    const result = await api.problems.list({ developerMode: store.developerMode });
    store.setProblems(result.problems);
  } catch (error) {
    console.error('[events] Failed to fetch problems:', error);
    store.setLoadingProblems(false);
  }
}

async function fetchProjectFiles(projectRoot: string): Promise<void> {
  const store = useStore.getState();
  store.setLoadingFiles(true);
  try {
    const result = await api.files.list(projectRoot);
    store.setProjectFiles(projectRoot, result.files);
  } catch (error) {
    console.error('[events] Failed to fetch files:', error);
    store.setLoadingFiles(false);
  }
}

async function fetchProjectModules(projectRoot: string): Promise<void> {
  const store = useStore.getState();
  store.setLoadingModules(true);
  try {
    const result = await api.modules.list(projectRoot);
    store.setProjectModules(projectRoot, result.modules);
  } catch (error) {
    console.error('[events] Failed to fetch modules:', error);
    store.setLoadingModules(false);
  }
}

async function fetchProjectDependencies(projectRoot: string): Promise<void> {
  const store = useStore.getState();
  store.setLoadingDependencies(true);
  try {
    const result = await api.dependencies.list(projectRoot);
    store.setProjectDependencies(projectRoot, result.dependencies);
  } catch (error) {
    console.error('[events] Failed to fetch dependencies:', error);
    store.setLoadingDependencies(false);
  }
}

async function fetchBom(): Promise<void> {
  const store = useStore.getState();
  const projectRoot = store.selectedProjectRoot;
  const targetName = store.selectedTargetNames[0];
  if (!projectRoot || !targetName) return;
  store.setLoadingBom(true);
  try {
    const result = await api.bom.get(projectRoot, targetName);
    store.setBomData(result);
  } catch (error) {
    store.setBomError(normalizeError(error));
  }
}

async function fetchVariables(): Promise<void> {
  const store = useStore.getState();
  const projectRoot = store.selectedProjectRoot;
  const targetName = store.selectedTargetNames[0];
  if (!projectRoot || !targetName) return;
  store.setLoadingVariables(true);
  try {
    const result = await api.variables.get(projectRoot, targetName);
    store.setVariablesData(result);
  } catch (error) {
    store.setVariablesError(normalizeError(error));
  }
}

function updateAtopileConfig(update: Partial<AtopileConfig>): void {
  const cleaned = Object.fromEntries(
    Object.entries(update).filter(([, value]) => value !== undefined)
  ) as Partial<AtopileConfig>;
  if (Object.keys(cleaned).length === 0) {
    return;
  }
  useStore.getState().setAtopileConfig(cleaned);
}

export async function fetchInitialData(): Promise<void> {
  await Promise.all([
    fetchProjects(),
    fetchBuilds(),
    fetchPackages(),
    fetchProblems(),
    fetchStdlib(),
  ]);
}

export async function handleEvent(event: string, data: unknown): Promise<void> {
  const detail = (data ?? {}) as Record<string, unknown>;
  const store = useStore.getState();

  switch (event) {
    case 'projects_changed':
      if (typeof detail.error === 'string') {
        store.setProjectsError(detail.error);
        break;
      }
      await fetchProjects();
      break;
    case 'builds_changed':
      await fetchBuilds();
      break;
    case 'packages_changed':
      if (typeof detail.error === 'string') {
        store.setInstallError(
          typeof detail.package_id === 'string' ? detail.package_id : 'unknown',
          detail.error
        );
      }
      await fetchPackages();
      break;
    case 'problems_changed':
      await fetchProblems();
      break;
    case 'stdlib_changed':
      await fetchStdlib();
      break;
    case 'bom_changed':
      await fetchBom();
      break;
    case 'variables_changed':
      await fetchVariables();
      break;
    case 'project_files_changed': {
      const projectRoot = typeof detail.project_root === 'string'
        ? detail.project_root
        : store.selectedProjectRoot;
      if (projectRoot) await fetchProjectFiles(projectRoot);
      break;
    }
    case 'project_modules_changed': {
      const projectRoot = typeof detail.project_root === 'string'
        ? detail.project_root
        : store.selectedProjectRoot;
      if (projectRoot) await fetchProjectModules(projectRoot);
      break;
    }
    case 'project_dependencies_changed': {
      const projectRoot = typeof detail.project_root === 'string'
        ? detail.project_root
        : store.selectedProjectRoot;
      if (projectRoot) await fetchProjectDependencies(projectRoot);
      break;
    }
    case 'atopile_config_changed':
      updateAtopileConfig({
        // Actual running atopile info (source of truth)
        actualVersion: typeof detail.actual_version === 'string'
          ? detail.actual_version as string
          : typeof detail.actualVersion === 'string'
            ? detail.actualVersion as string
            : undefined,
        actualSource: typeof detail.actual_source === 'string'
          ? detail.actual_source as string
          : typeof detail.actualSource === 'string'
            ? detail.actualSource as string
            : undefined,
        actualBinaryPath: typeof detail.actual_binary_path === 'string'
          ? detail.actual_binary_path as string
          : typeof detail.actualBinaryPath === 'string'
            ? detail.actualBinaryPath as string
            : undefined,
        // User selection state
        source: typeof detail.source === 'string' ? detail.source as AtopileConfig['source'] : undefined,
        currentVersion: typeof detail.current_version === 'string'
          ? detail.current_version as string
          : typeof detail.currentVersion === 'string'
            ? detail.currentVersion as string
            : undefined,
        branch: typeof detail.branch === 'string' ? detail.branch as string : undefined,
        localPath: typeof detail.local_path === 'string'
          ? detail.local_path as string
          : typeof detail.localPath === 'string'
            ? detail.localPath as string
            : undefined,
        availableVersions: Array.isArray(detail.available_versions)
          ? detail.available_versions as string[]
          : Array.isArray(detail.availableVersions)
            ? detail.availableVersions as string[]
            : undefined,
        availableBranches: Array.isArray(detail.available_branches)
          ? detail.available_branches as string[]
          : Array.isArray(detail.availableBranches)
            ? detail.availableBranches as string[]
            : undefined,
        detectedInstallations: Array.isArray(detail.detected_installations)
          ? detail.detected_installations as AtopileConfig['detectedInstallations']
          : Array.isArray(detail.detectedInstallations)
            ? detail.detectedInstallations as AtopileConfig['detectedInstallations']
            : undefined,
        isInstalling: typeof detail.is_installing === 'boolean'
          ? detail.is_installing as boolean
          : typeof detail.isInstalling === 'boolean'
            ? detail.isInstalling as boolean
            : undefined,
        installProgress: typeof detail.install_progress === 'object'
          ? detail.install_progress as AtopileConfig['installProgress']
          : typeof detail.installProgress === 'object'
            ? detail.installProgress as AtopileConfig['installProgress']
            : undefined,
        error: typeof detail.error === 'string' ? detail.error as string : undefined,
      });
      break;
    default:
      break;
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('atopile:event', { detail: { event, data } })
    );
  }
}
