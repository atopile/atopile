/**
 * Zustand store for UI state management.
 *
 * This store owns all UI state. The UI Server connects directly to the
 * Python backend via HTTP/WebSocket - no VS Code extension middleman.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  ServerData,
  UIState,
  AtopileState,
  Project,
  Build,
  PackageInfo,
  PackageDetails,
  StdLibItem,
  BOMData,
  Problem,
  ModuleDefinition,
  FileTreeNode,
  ProjectDependency,
  VariablesData,
} from '../types/build';

// Initial state for the store
const initialState: ServerData & UIState = {

  // Projects
  projects: [],
  isLoadingProjects: false,
  projectsError: null,
  selectedProjectRoot: null,
  selectedTargetNames: [],

  // Builds
  builds: [],
  queuedBuilds: [],

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

  // Variables
  currentVariablesData: null,
  isLoadingVariables: false,
  variablesError: null,

  // Connection
  isConnected: false,
};

// Store actions interface
interface StoreActions {
  // Connection
  setConnected: (connected: boolean) => void;
  setAtopileConfig: (config: Partial<AtopileState>) => void;

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
  selectBuild: (buildName: string | null) => void;
  selectBuildById: (buildId: string | null, buildName?: string | null) => void;

  // Log viewer
  setLogViewerBuildId: (buildId: string | null) => void;

  // Packages
  setPackages: (packages: PackageInfo[]) => void;
  setLoadingPackages: (loading: boolean) => void;
  setPackagesError: (error: string | null) => void;
  setPackageDetails: (details: PackageDetails | null) => void;
  setLoadingPackageDetails: (loading: boolean) => void;
  setPackageDetailsError: (error: string | null) => void;
  addInstallingPackage: (packageId: string) => void;
  removeInstallingPackage: (packageId: string) => void;
  setInstallError: (packageId: string, error: string | null) => void;
  clearInstallingPackages: () => void;
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

  // Project data
  setProjectModules: (projectRoot: string, modules: ModuleDefinition[]) => void;
  setLoadingModules: (loading: boolean) => void;
  setProjectFiles: (projectRoot: string, files: FileTreeNode[]) => void;
  setLoadingFiles: (loading: boolean) => void;
  setProjectDependencies: (projectRoot: string, deps: ProjectDependency[]) => void;
  setLoadingDependencies: (loading: boolean) => void;

  // Reset
  reset: () => void;
}

// Combined store type
type Store = ServerData & UIState & StoreActions;

export const useStore = create<Store>()(
  devtools(
    (set) => ({
      ...initialState,

      // Connection
      setConnected: (connected) => set({ isConnected: connected }),

      setAtopileConfig: (config) =>
        set((state) => ({
          atopile: { ...state.atopile, ...config },
        })),

      // Projects
      setProjects: (projects) =>
        set({ projects, isLoadingProjects: false, projectsError: null }),
      setLoadingProjects: (loading) => set({ isLoadingProjects: loading }),
      setProjectsError: (error) =>
        set({ projectsError: error, isLoadingProjects: false }),

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

      selectBuild: (buildName) => set({ selectedBuildName: buildName }),

      selectBuildById: (buildId, buildName = null) =>
        set({ selectedBuildId: buildId, selectedBuildName: buildName }),

      // Log viewer
      setLogViewerBuildId: (buildId) => set({ logViewerBuildId: buildId }),

      // Packages
      setPackages: (packages) => set({ packages, isLoadingPackages: false }),

      setLoadingPackages: (loading) => set({ isLoadingPackages: loading }),

      setPackagesError: (error) =>
        set({ packagesError: error, isLoadingPackages: false }),

      setPackageDetails: (details) =>
        set({
          selectedPackageDetails: details,
          isLoadingPackageDetails: false,
          packageDetailsError: null,
        }),

      setLoadingPackageDetails: (loading) =>
        set({ isLoadingPackageDetails: loading }),

      setPackageDetailsError: (error) =>
        set({ packageDetailsError: error, isLoadingPackageDetails: false }),

      addInstallingPackage: (packageId) =>
        set((state) => ({
          installingPackageIds: state.installingPackageIds.includes(packageId)
            ? state.installingPackageIds
            : [...state.installingPackageIds, packageId],
          installError: null,
        })),

      removeInstallingPackage: (packageId) =>
        set((state) => ({
          installingPackageIds: state.installingPackageIds.filter((id) => id !== packageId),
        })),

      setInstallError: (packageId, error) =>
        set((state) => ({
          installError: error,
          installingPackageIds: state.installingPackageIds.filter((id) => id !== packageId),
        })),

      clearInstallingPackages: () =>
        set({ installingPackageIds: [], installError: null }),

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
      setBomError: (error) => set({ bomError: error, isLoadingBom: false }),

      // Variables
      setVariablesData: (data) =>
        set({ currentVariablesData: data, isLoadingVariables: false, variablesError: null }),

      setLoadingVariables: (loading) => set({ isLoadingVariables: loading }),
      setVariablesError: (error) => set({ variablesError: error, isLoadingVariables: false }),

      // Project data
      setProjectModules: (projectRoot, modules) =>
        set((state) => ({
          projectModules: {
            ...state.projectModules,
            [projectRoot]: modules,
          },
          isLoadingModules: false,
        })),
      setLoadingModules: (loading) => set({ isLoadingModules: loading }),

      setProjectFiles: (projectRoot, files) =>
        set((state) => ({
          projectFiles: {
            ...state.projectFiles,
            [projectRoot]: files,
          },
          isLoadingFiles: false,
        })),
      setLoadingFiles: (loading) => set({ isLoadingFiles: loading }),

      setProjectDependencies: (projectRoot, deps) =>
        set((state) => ({
          projectDependencies: {
            ...state.projectDependencies,
            [projectRoot]: deps,
          },
          isLoadingDependencies: false,
        })),
      setLoadingDependencies: (loading) => set({ isLoadingDependencies: loading }),

      // Reset
      reset: () => set(initialState),
    }),
    { name: 'atopile-store' }
  )
);

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
