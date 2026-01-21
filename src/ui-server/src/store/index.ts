/**
 * Zustand store for UI state management.
 *
 * This store owns all UI state. The UI Server connects directly to the
 * Python backend via HTTP/WebSocket - no VS Code extension middleman.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  AppState,
  Project,
  Build,
  PackageInfo,
  PackageDetails,
  StdLibItem,
  BOMData,
  Problem,
  LogEntry,
  LogLevel,
  ModuleDefinition,
  FileTreeNode,
  ProjectDependency,
  VariablesData,
} from '../types/build';

// Initial state matching the backend AppState
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

  // Packages
  packages: [],
  isLoadingPackages: false,
  packagesError: null,
  installingPackageId: null,
  installError: null,

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

  // Build/Log selection
  selectedBuildName: null,
  selectedProjectName: null,
  selectedStageIds: [],
  logEntries: [],
  isLoadingLogs: false,
  logFile: null,

  // Log viewer UI
  enabledLogLevels: ['INFO', 'WARNING', 'ERROR', 'ALERT'],
  logSearchQuery: '',
  logTimestampMode: 'absolute',
  logAutoScroll: true,

  // Log counts
  logCounts: undefined,
  logTotalCount: undefined,
  logHasMore: undefined,

  // Sidebar UI
  expandedTargets: [],

  // Extension info
  version: 'dev',
  logoUri: '',

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
};

// Store actions interface
interface StoreActions {
  // Connection
  setConnected: (connected: boolean) => void;

  // Full state replacement (from WebSocket)
  replaceState: (state: Partial<AppState>) => void;

  // Projects
  setProjects: (projects: Project[]) => void;
  selectProject: (projectRoot: string | null) => void;
  toggleTarget: (targetName: string) => void;
  toggleTargetExpanded: (targetName: string) => void;

  // Builds
  setBuilds: (builds: Build[]) => void;
  setQueuedBuilds: (builds: Build[]) => void;
  selectBuild: (buildName: string | null) => void;

  // Packages
  setPackages: (packages: PackageInfo[]) => void;
  setLoadingPackages: (loading: boolean) => void;
  setPackagesError: (error: string | null) => void;
  setPackageDetails: (details: PackageDetails | null) => void;
  setLoadingPackageDetails: (loading: boolean) => void;
  setInstallingPackage: (packageId: string | null) => void;
  setInstallError: (error: string | null) => void;

  // Logs
  setLogEntries: (entries: LogEntry[]) => void;
  appendLogEntries: (entries: LogEntry[]) => void;
  toggleLogLevel: (level: LogLevel) => void;
  setLogSearchQuery: (query: string) => void;
  toggleLogTimestampMode: () => void;
  setLogAutoScroll: (enabled: boolean) => void;

  // Problems
  setProblems: (problems: Problem[]) => void;
  setDeveloperMode: (enabled: boolean) => void;

  // Standard Library
  setStdlibItems: (items: StdLibItem[]) => void;

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
  setProjectFiles: (projectRoot: string, files: FileTreeNode[]) => void;
  setProjectDependencies: (projectRoot: string, deps: ProjectDependency[]) => void;

  // Reset
  reset: () => void;
}

// Combined store type
type Store = AppState & StoreActions;

export const useStore = create<Store>()(
  devtools(
    (set) => ({
      ...initialState,

      // Connection
      setConnected: (connected) => set({ isConnected: connected }),

      // Full state replacement (from WebSocket broadcast)
      replaceState: (newState) =>
        set((state) => ({
          ...state,
          ...newState,
          isConnected: true,
        })),

      // Projects
      setProjects: (projects) => set({ projects }),

      selectProject: (projectRoot) => set({ selectedProjectRoot: projectRoot }),

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

      // Packages
      setPackages: (packages) => set({ packages, isLoadingPackages: false }),

      setLoadingPackages: (loading) => set({ isLoadingPackages: loading }),

      setPackagesError: (error) =>
        set({ packagesError: error, isLoadingPackages: false }),

      setPackageDetails: (details) =>
        set({
          selectedPackageDetails: details,
          isLoadingPackageDetails: false,
        }),

      setLoadingPackageDetails: (loading) =>
        set({ isLoadingPackageDetails: loading }),

      setInstallingPackage: (packageId) =>
        set({ installingPackageId: packageId, installError: null }),

      setInstallError: (error) =>
        set({ installError: error, installingPackageId: null }),

      // Logs
      setLogEntries: (entries) => set({ logEntries: entries }),

      appendLogEntries: (entries) =>
        set((state) => ({
          logEntries: [...state.logEntries, ...entries],
        })),

      toggleLogLevel: (level) =>
        set((state) => {
          const levels = state.enabledLogLevels;
          if (levels.includes(level)) {
            return {
              enabledLogLevels: levels.filter((l) => l !== level),
            };
          }
          return {
            enabledLogLevels: [...levels, level],
          };
        }),

      setLogSearchQuery: (query) => set({ logSearchQuery: query }),

      toggleLogTimestampMode: () =>
        set((state) => ({
          logTimestampMode:
            state.logTimestampMode === 'absolute' ? 'delta' : 'absolute',
        })),

      setLogAutoScroll: (enabled) => set({ logAutoScroll: enabled }),

      // Problems
      setProblems: (problems) => set({ problems, isLoadingProblems: false }),
      setDeveloperMode: (enabled) => set({ developerMode: enabled }),

      // Standard Library
      setStdlibItems: (items) =>
        set({ stdlibItems: items, isLoadingStdlib: false }),

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

export const useFilteredLogs = () =>
  useStore((state) => {
    const { logEntries, enabledLogLevels, logSearchQuery } = state;
    return logEntries.filter((entry) => {
      if (!enabledLogLevels.includes(entry.level)) return false;
      if (
        logSearchQuery &&
        !entry.message.toLowerCase().includes(logSearchQuery.toLowerCase())
      )
        return false;
      return true;
    });
  });
