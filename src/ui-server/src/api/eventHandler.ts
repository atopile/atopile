import { api } from './client';
import { useStore } from '../store';
import type { AppState } from '../types/build';
import { EventType } from '../types/gen/generated';

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

export async function handleEvent(
  event: EventType | string,
  data: unknown
): Promise<void> {
  const detail = (data ?? {}) as Record<string, unknown>;
  const store = useStore.getState();

  switch (event) {
    case EventType.ProjectsChanged:
      if (typeof detail.error === 'string') {
        store.setProjectsError(detail.error);
        break;
      }
      await fetchProjects();
      break;
    case EventType.BuildsChanged:
      await fetchBuilds();
      break;
    case EventType.PackagesChanged:
      if (typeof detail.error === 'string') {
        store.setInstallError(
          typeof detail.package_id === 'string' ? detail.package_id : 'unknown',
          detail.error
        );
      }
      await fetchPackages();
      break;
    case EventType.ProblemsChanged:
      await fetchProblems();
      break;
    case EventType.StdlibChanged:
      await fetchStdlib();
      break;
    case EventType.BOMChanged:
      await fetchBom();
      break;
    case EventType.VariablesChanged:
      await fetchVariables();
      break;
    case EventType.ProjectFilesChanged: {
      const projectRoot = typeof detail.project_root === 'string'
        ? detail.project_root
        : store.selectedProjectRoot;
      if (projectRoot) await fetchProjectFiles(projectRoot);
      break;
    }
    case EventType.ProjectModulesChanged: {
      const projectRoot = typeof detail.project_root === 'string'
        ? detail.project_root
        : store.selectedProjectRoot;
      if (projectRoot) await fetchProjectModules(projectRoot);
      break;
    }
    case EventType.ProjectDependenciesChanged: {
      const projectRoot = typeof detail.project_root === 'string'
        ? detail.project_root
        : store.selectedProjectRoot;
      if (projectRoot) await fetchProjectDependencies(projectRoot);
      break;
    }
    case EventType.AtopileConfigChanged:
      updateAtopileConfig({
        // Actual running atopile info
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
        localPath: typeof detail.local_path === 'string'
          ? detail.local_path as string
          : typeof detail.localPath === 'string'
            ? detail.localPath as string
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
