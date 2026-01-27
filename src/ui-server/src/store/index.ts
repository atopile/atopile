/**
 * Zustand store for UI state management.
 *
 * This store owns all UI state. The UI Server connects directly to the
 * Python backend via HTTP/WebSocket - no VS Code extension middleman.
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { postMessage } from '../api/vscodeApi';
import type {
  AppState,
  Project,
  Build,
  BuildTarget,
  PackageInfo,
  PackageDetails,
  StdLibItem,
  BOMData,
  Problem,
  ModuleDefinition,
  FileTreeNode,
  ProjectDependency,
  VariablesData,
  TestItem,
  TestRun,
} from '../types/build';

const ERROR_TIMEOUT_MS = 8000;

let installErrorTimeout: ReturnType<typeof setTimeout> | null = null;
let packagesErrorTimeout: ReturnType<typeof setTimeout> | null = null;
let bomErrorTimeout: ReturnType<typeof setTimeout> | null = null;
let variablesErrorTimeout: ReturnType<typeof setTimeout> | null = null;
let packageDetailsErrorTimeout: ReturnType<typeof setTimeout> | null = null;
let projectsErrorTimeout: ReturnType<typeof setTimeout> | null = null;
let atopileErrorTimeout: ReturnType<typeof setTimeout> | null = null;

const arraysEqual = (a: string[], b: string[]) => {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
};

// Initial state for the store
const initialState: AppState = {
  // Connection
  isConnected: false,

  // Projects
  projects: [],
  isLoadingProjects: false,
  projectsError: null,
  selectedProjectRoot: null,
  selectedTargetNames: [],

  // Builds
  builds: [],
  queuedBuilds: [],
  buildHistory: [],

  // Packages
  packages: [],
  isLoadingPackages: false,
  packagesError: null,
  installingPackageIds: [],
  installError: null,
  updatingDependencyIds: [],

  // Standard Library
  stdlibItems: [],
  isLoadingStdlib: false,

  // BOM
  bomData: null,
  isLoadingBom: false,
  bomError: null,

  // Package details
  selectedPackageDetails: null,
  isLoadingPackageDetails: false,
  packageDetailsError: null,

  // Build selection
  selectedBuildId: null,
  selectedBuildName: null,
  selectedProjectName: null,

  // Log viewer
  logViewerBuildId: null as string | null,

  // Sidebar UI
  expandedTargets: [],
  activeEditorFile: null,
  lastAtoFile: null,

  // Atopile configuration
  atopile: {
    currentVersion: '',
    source: 'release',
    localPath: null,
    branch: null,
    availableVersions: [],
    availableBranches: [],
    detectedInstallations: [],
    isInstalling: false,
    installProgress: null,
    error: null,
  },

  // Problems
  problems: [],
  isLoadingProblems: false,
  problemFilter: {
    levels: ['error', 'warning'],
    buildNames: [],
    stageIds: [],
  },

  // Developer mode - shows all log audiences instead of just 'user'
  developerMode: false,

  // Project modules
  projectModules: {},
  isLoadingModules: false,

  // Project files
  projectFiles: {},
  isLoadingFiles: false,

  // Project dependencies
  projectDependencies: {},
  isLoadingDependencies: false,

  // Project builds (for installed dependencies)
  projectBuilds: {},
  isLoadingBuilds: false,

  // Variables
  currentVariablesData: null,
  isLoadingVariables: false,
  variablesError: null,

  // Test Explorer
  collectedTests: [] as TestItem[],
  isLoadingTests: false,
  testsError: null as string | null,
  testCollectionErrors: {} as Record<string, string>,
  selectedTestNodeIds: [] as string[],
  testRun: {
    testRunId: null,
    isRunning: false,
  } as TestRun,
  testFilter: '',
  testPaths: 'test src',
  testMarkers: '',
};

// Store actions interface
interface StoreActions {
  // Connection
  setConnected: (connected: boolean) => void;

  // Full state replacement (from WebSocket)
  replaceState: (state: Partial<AppState>) => void;

  // Projects
  setProjects: (projects: Project[]) => void;
  setLoadingProjects: (loading: boolean) => void;
  setProjectsError: (error: string | null) => void;
  selectProject: (projectRoot: string | null) => void;
  setSelectedTargets: (targetNames: string[]) => void;
  toggleTarget: (targetName: string) => void;
  toggleTargetExpanded: (targetName: string) => void;

  // Builds
  setBuilds: (builds: Build[]) => void;
  setQueuedBuilds: (builds: Build[]) => void;
  setBuildHistory: (builds: Build[]) => void;
  selectBuild: (buildName: string | null) => void;
  selectBuildById: (buildId: string | null, buildName?: string | null) => void;

  // Log viewer
  setLogViewerBuildId: (buildId: string | null) => void;

  // Active editor file (from VS Code)
  setActiveEditorFile: (filePath: string | null) => void;
  setLastAtoFile: (filePath: string | null) => void;

  // Packages
  setPackages: (packages: PackageInfo[]) => void;
  setLoadingPackages: (loading: boolean) => void;
  setPackagesError: (error: string | null) => void;
  setPackageDetails: (details: PackageDetails | null) => void;
  setLoadingPackageDetails: (loading: boolean) => void;
  addInstallingPackage: (packageId: string) => void;
  removeInstallingPackage: (packageId: string) => void;
  clearInstallingPackages: () => void;
  setInstallError: (packageId: string, error: string | null) => void;
  addUpdatingDependency: (projectRoot: string, dependencyId: string) => void;
  removeUpdatingDependency: (projectRoot: string, dependencyId: string) => void;

  // Problems
  setProblems: (problems: Problem[]) => void;
  setLoadingProblems: (loading: boolean) => void;
  setDeveloperMode: (enabled: boolean) => void;

  // Standard Library
  setStdlibItems: (items: StdLibItem[]) => void;
  setLoadingStdlib: (loading: boolean) => void;

  // BOM
  setBomData: (data: BOMData | null) => void;
  setLoadingBom: (loading: boolean) => void;
  setBomError: (error: string | null) => void;

  // Variables
  setVariablesData: (data: VariablesData | null) => void;
  setLoadingVariables: (loading: boolean) => void;
  setVariablesError: (error: string | null) => void;

  // Atopile config
  setAtopileConfig: (update: Partial<AppState['atopile']>) => void;

  // Project data
  setProjectModules: (projectRoot: string, modules: ModuleDefinition[]) => void;
  setProjectFiles: (projectRoot: string, files: FileTreeNode[]) => void;
  setProjectDependencies: (projectRoot: string, deps: ProjectDependency[]) => void;
  setProjectBuilds: (projectRoot: string, builds: BuildTarget[]) => void;
  setLoadingModules: (loading: boolean) => void;
  setLoadingFiles: (loading: boolean) => void;
  setLoadingDependencies: (loading: boolean) => void;

  // Test Explorer
  setCollectedTests: (tests: TestItem[]) => void;
  setLoadingTests: (loading: boolean) => void;
  setTestsError: (error: string | null) => void;
  setTestCollectionErrors: (errors: Record<string, string>) => void;
  setTestFilter: (filter: string) => void;
  setTestPaths: (paths: string) => void;
  setTestMarkers: (markers: string) => void;
  toggleTestSelected: (nodeId: string) => void;
  selectAllTests: () => void;
  clearTestSelection: () => void;
  startTestRun: (testRunId: string) => void;
  completeTestRun: () => void;

  // Reset
  reset: () => void;
}

// Combined store type
type Store = AppState & StoreActions;

export const useStore = create<Store>()(
  subscribeWithSelector(
    devtools(
      (set) => ({
        ...initialState,

      // Connection
      setConnected: (connected) => set({ isConnected: connected }),

      // Full state replacement (from WebSocket broadcast)
      replaceState: (newState) => {
        if (packagesErrorTimeout) {
          clearTimeout(packagesErrorTimeout);
          packagesErrorTimeout = null;
        }
        if (bomErrorTimeout) {
          clearTimeout(bomErrorTimeout);
          bomErrorTimeout = null;
        }
        if (variablesErrorTimeout) {
          clearTimeout(variablesErrorTimeout);
          variablesErrorTimeout = null;
        }
        if (packageDetailsErrorTimeout) {
          clearTimeout(packageDetailsErrorTimeout);
          packageDetailsErrorTimeout = null;
        }
        if (projectsErrorTimeout) {
          clearTimeout(projectsErrorTimeout);
          projectsErrorTimeout = null;
        }
        if (atopileErrorTimeout) {
          clearTimeout(atopileErrorTimeout);
          atopileErrorTimeout = null;
        }

        set((state) => ({
          ...state,
          ...newState,
          isConnected: true,
        }));

        if (newState.packagesError) {
          const error = newState.packagesError;
          packagesErrorTimeout = setTimeout(() => {
            set((state) =>
              state.packagesError === error ? { packagesError: null } : {}
            );
            packagesErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
        if (newState.bomError) {
          const error = newState.bomError;
          bomErrorTimeout = setTimeout(() => {
            set((state) =>
              state.bomError === error ? { bomError: null } : {}
            );
            bomErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
        if (newState.variablesError) {
          const error = newState.variablesError;
          variablesErrorTimeout = setTimeout(() => {
            set((state) =>
              state.variablesError === error ? { variablesError: null } : {}
            );
            variablesErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
        if (newState.packageDetailsError) {
          const error = newState.packageDetailsError;
          packageDetailsErrorTimeout = setTimeout(() => {
            set((state) =>
              state.packageDetailsError === error
                ? { packageDetailsError: null }
                : {}
            );
            packageDetailsErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
        if (newState.projectsError) {
          const error = newState.projectsError;
          projectsErrorTimeout = setTimeout(() => {
            set((state) =>
              state.projectsError === error ? { projectsError: null } : {}
            );
            projectsErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
        if (newState.atopile?.error) {
          const error = newState.atopile.error;
          atopileErrorTimeout = setTimeout(() => {
            set((state) =>
              state.atopile.error === error
                ? { atopile: { ...state.atopile, error: null } }
                : {}
            );
            atopileErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
      },

      // Projects
      setProjects: (projects) => set({ projects, isLoadingProjects: false }),

      setLoadingProjects: (loading) => set({ isLoadingProjects: loading }),

      setProjectsError: (error) => {
        if (projectsErrorTimeout) {
          clearTimeout(projectsErrorTimeout);
          projectsErrorTimeout = null;
        }
        set(
          error
            ? { projectsError: error, isLoadingProjects: false }
            : { projectsError: null }
        );
        if (error) {
          projectsErrorTimeout = setTimeout(() => {
            set((state) =>
              state.projectsError === error ? { projectsError: null } : {}
            );
            projectsErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
      },

      selectProject: (projectRoot) => set({ selectedProjectRoot: projectRoot }),

      setSelectedTargets: (targetNames) =>
        set({ selectedTargetNames: targetNames }),

      toggleTarget: (targetName) =>
        set((state) => {
          const selected = state.selectedTargetNames;
          if (selected.includes(targetName)) {
            return {
              selectedTargetNames: selected.filter((t) => t !== targetName),
            };
          }
          return {
            selectedTargetNames: [...selected, targetName],
          };
        }),

      toggleTargetExpanded: (targetName) =>
        set((state) => {
          const expanded = state.expandedTargets;
          if (expanded.includes(targetName)) {
            return {
              expandedTargets: expanded.filter((t) => t !== targetName),
            };
          }
          return {
            expandedTargets: [...expanded, targetName],
          };
        }),

  // Builds
  setBuilds: (builds) => set({ builds }),

  setQueuedBuilds: (queuedBuilds) => set({ queuedBuilds }),

  setBuildHistory: (buildHistory) => set({ buildHistory }),

      selectBuild: (buildName) => set({ selectedBuildName: buildName }),

      selectBuildById: (buildId, buildName = null) =>
        set({ selectedBuildId: buildId, selectedBuildName: buildName }),

      // Log viewer
      setLogViewerBuildId: (buildId) => set({ logViewerBuildId: buildId }),

      // Active editor file - just store what's provided, backend handles lastAtoFile
      setActiveEditorFile: (filePath) => set({ activeEditorFile: filePath }),

      setLastAtoFile: (filePath) => set({ lastAtoFile: filePath }),

      // Packages
      setPackages: (packages) => set({ packages, isLoadingPackages: false }),

      setLoadingPackages: (loading) => set({ isLoadingPackages: loading }),

      setPackagesError: (error) => {
        if (packagesErrorTimeout) {
          clearTimeout(packagesErrorTimeout);
          packagesErrorTimeout = null;
        }
        set({ packagesError: error, isLoadingPackages: false });
        if (error) {
          packagesErrorTimeout = setTimeout(() => {
            set((state) =>
              state.packagesError === error ? { packagesError: null } : {}
            );
            packagesErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
      },

      setPackageDetails: (details) =>
        set({
          selectedPackageDetails: details,
          isLoadingPackageDetails: false,
        }),

      setLoadingPackageDetails: (loading) =>
        set({ isLoadingPackageDetails: loading }),

      addInstallingPackage: (packageId) => {
        if (installErrorTimeout) {
          clearTimeout(installErrorTimeout);
          installErrorTimeout = null;
        }
        set((state) => ({
          installingPackageIds: state.installingPackageIds.includes(packageId)
            ? state.installingPackageIds
            : [...state.installingPackageIds, packageId],
          installError: null,
        }));
      },

      removeInstallingPackage: (packageId) =>
        set((state) => ({
          installingPackageIds: state.installingPackageIds.filter((id) => id !== packageId),
        })),

      clearInstallingPackages: () =>
        set({ installingPackageIds: [], installError: null }),

      setInstallError: (packageId, error) => {
        if (installErrorTimeout) {
          clearTimeout(installErrorTimeout);
          installErrorTimeout = null;
        }
        set((state) => ({
          installError: error,
          installingPackageIds: state.installingPackageIds.filter((id) => id !== packageId),
        }));
        if (error) {
          installErrorTimeout = setTimeout(() => {
            set({ installError: null });
            installErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
      },

      addUpdatingDependency: (projectRoot, dependencyId) =>
        set((state) => {
          const key = `${projectRoot}:${dependencyId}`;
          return {
            updatingDependencyIds: state.updatingDependencyIds.includes(key)
              ? state.updatingDependencyIds
              : [...state.updatingDependencyIds, key],
          };
        }),

      removeUpdatingDependency: (projectRoot, dependencyId) =>
        set((state) => {
          const key = `${projectRoot}:${dependencyId}`;
          return {
            updatingDependencyIds: state.updatingDependencyIds.filter((id) => id !== key),
          };
        }),

      // Problems
      setProblems: (problems) => set({ problems, isLoadingProblems: false }),
      setLoadingProblems: (loading) => set({ isLoadingProblems: loading }),
      setDeveloperMode: (enabled) => set({ developerMode: enabled }),

      // Standard Library
      setStdlibItems: (items) =>
        set({ stdlibItems: items, isLoadingStdlib: false }),
      setLoadingStdlib: (loading) => set({ isLoadingStdlib: loading }),

      // BOM
      setBomData: (data) => set({ bomData: data, isLoadingBom: false, bomError: null }),

      setLoadingBom: (loading) => set({ isLoadingBom: loading }),
      setBomError: (error) => {
        if (bomErrorTimeout) {
          clearTimeout(bomErrorTimeout);
          bomErrorTimeout = null;
        }
        set({ bomError: error, isLoadingBom: false });
        if (error) {
          bomErrorTimeout = setTimeout(() => {
            set((state) =>
              state.bomError === error ? { bomError: null } : {}
            );
            bomErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
      },

      // Variables
      setVariablesData: (data) =>
        set({ currentVariablesData: data, isLoadingVariables: false, variablesError: null }),

      setLoadingVariables: (loading) => set({ isLoadingVariables: loading }),
      setVariablesError: (error) => {
        if (variablesErrorTimeout) {
          clearTimeout(variablesErrorTimeout);
          variablesErrorTimeout = null;
        }
        set({ variablesError: error, isLoadingVariables: false });
        if (error) {
          variablesErrorTimeout = setTimeout(() => {
            set((state) =>
              state.variablesError === error ? { variablesError: null } : {}
            );
            variablesErrorTimeout = null;
          }, ERROR_TIMEOUT_MS);
        }
      },

      // Atopile config
      setAtopileConfig: (update) =>
        set((state) => ({
          atopile: {
            ...state.atopile,
            ...update,
          },
        })),

      // Project data
      setProjectModules: (projectRoot, modules) =>
        set((state) => ({
          projectModules: {
            ...state.projectModules,
            [projectRoot]: modules,
          },
          isLoadingModules: false,
        })),

      setProjectFiles: (projectRoot, files) =>
        set((state) => ({
          projectFiles: {
            ...state.projectFiles,
            [projectRoot]: files,
          },
          isLoadingFiles: false,
        })),

      setProjectDependencies: (projectRoot, deps) =>
        set((state) => ({
          projectDependencies: {
            ...state.projectDependencies,
            [projectRoot]: deps,
          },
          isLoadingDependencies: false,
        })),

      setProjectBuilds: (projectRoot, builds) =>
        set((state) => ({
          projectBuilds: {
            ...state.projectBuilds,
            [projectRoot]: builds,
          },
          isLoadingBuilds: false,
        })),

      setLoadingModules: (loading) => set({ isLoadingModules: loading }),
      setLoadingFiles: (loading) => set({ isLoadingFiles: loading }),
      setLoadingDependencies: (loading) => set({ isLoadingDependencies: loading }),

      // Test Explorer
      setCollectedTests: (tests) =>
        set({ collectedTests: tests, isLoadingTests: false, testsError: null }),

      setLoadingTests: (loading) => set({ isLoadingTests: loading }),

      setTestsError: (error) =>
        set({ testsError: error, isLoadingTests: false }),

      setTestCollectionErrors: (errors) => set({ testCollectionErrors: errors }),

      setTestFilter: (filter) => set({ testFilter: filter }),

      setTestPaths: (paths) => set({ testPaths: paths }),

      setTestMarkers: (markers) => set({ testMarkers: markers }),

      toggleTestSelected: (nodeId) =>
        set((state) => {
          const selected = state.selectedTestNodeIds;
          if (selected.includes(nodeId)) {
            return { selectedTestNodeIds: selected.filter((id) => id !== nodeId) };
          }
          return { selectedTestNodeIds: [...selected, nodeId] };
        }),

      selectAllTests: () =>
        set((state) => ({
          selectedTestNodeIds: state.collectedTests.map((t) => t.node_id),
        })),

      clearTestSelection: () => set({ selectedTestNodeIds: [] }),

      startTestRun: (testRunId) =>
        set({ testRun: { testRunId, isRunning: true } }),

      completeTestRun: () =>
        set((state) => ({ testRun: { ...state.testRun, isRunning: false } })),

      // Reset
      reset: () => set(initialState),
      }),
      { name: 'atopile-store' }
    )
  )
);

<<<<<<< HEAD
=======
// Receive cross-webview state updates
_channel?.addEventListener('message', (event) => {
  const { key, value } = event.data ?? {};
  if (key) {
    useStore.setState({ [key]: value });
  }
});

useStore.subscribe(
  (state) => ({
    projectRoot: state.selectedProjectRoot,
    targetNames: state.selectedTargetNames,
  }),
  (current, previous) => {
    if (
      current.projectRoot === previous.projectRoot &&
      arraysEqual(current.targetNames, previous.targetNames)
    ) {
      return;
    }
    postMessage({
      type: 'selectionChanged',
      projectRoot: current.projectRoot,
      targetNames: current.targetNames,
    });
  }
);

>>>>>>> 5ec6e6d4b (update layout/3d views to selected build)
// Selectors for common derived state
export const useSelectedProject = () =>
  useStore((state) => {
    if (!state.selectedProjectRoot) return null;
    return state.projects.find((p) => p.root === state.selectedProjectRoot);
  });

export const useSelectedBuild = () =>
  useStore((state) => {
    // Prefer buildId if available
    if (state.selectedBuildId) {
      return state.builds.find((b) => b.buildId === state.selectedBuildId);
    }
    // Fall back to buildName for backwards compatibility
    if (!state.selectedBuildName) return null;
    return state.builds.find(
      (b) => b.displayName === state.selectedBuildName || b.name === state.selectedBuildName
    );
  });

export const useFilteredProblems = () =>
  useStore((state) => {
    const { problems, problemFilter } = state;
    return problems.filter((p) => {
      if (!problemFilter.levels.includes(p.level)) return false;
      if (
        problemFilter.buildNames.length > 0 &&
        p.buildName &&
        !problemFilter.buildNames.includes(p.buildName)
      )
        return false;
      if (
        problemFilter.stageIds.length > 0 &&
        p.stage &&
        !problemFilter.stageIds.includes(p.stage)
      )
        return false;
      return true;
    });
  });
