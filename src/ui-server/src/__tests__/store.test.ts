/**
 * Zustand store tests
 * Tests state management, actions, and selectors
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useStore, useSelectedProject, useSelectedBuild, useFilteredProblems, useFilteredLogs } from '../store';
import type { Project, Build, Problem } from '../types/build';

// Helper to reset store state between tests
const resetStore = () => {
  useStore.setState({
    isConnected: false,
    projects: [],
    selectedProjectRoot: null,
    selectedTargetNames: [],
    builds: [],
    queuedBuilds: [],
    packages: [],
    isLoadingPackages: false,
    packagesError: null,
    stdlibItems: [],
    isLoadingStdlib: false,
    bomData: null,
    isLoadingBom: false,
    bomError: null,
    selectedPackageDetails: null,
    isLoadingPackageDetails: false,
    packageDetailsError: null,
    selectedBuildName: null,
    selectedProjectName: null,
    selectedStageIds: [],
    logEntries: [],
    isLoadingLogs: false,
    logFile: null,
    enabledLogLevels: ['INFO', 'WARNING', 'ERROR', 'ALERT'],
    logSearchQuery: '',
    logTimestampMode: 'absolute',
    logAutoScroll: true,
    logCounts: undefined,
    logTotalCount: undefined,
    logHasMore: undefined,
    expandedTargets: [],
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
    problems: [],
    isLoadingProblems: false,
    problemFilter: {
      levels: ['error', 'warning'],
      buildNames: [],
      stageIds: [],
    },
    projectModules: {},
    isLoadingModules: false,
    projectFiles: {},
    isLoadingFiles: false,
    projectDependencies: {},
    isLoadingDependencies: false,
    currentVariablesData: null,
    isLoadingVariables: false,
    variablesError: null,
  });
};

// Sample test data
const sampleProjects: Project[] = [
  {
    root: '/projects/test-project',
    name: 'test-project',
    targets: [
      { name: 'default', entry: 'main.ato:App', root: '/projects/test-project' },
      { name: 'debug', entry: 'main.ato:Debug', root: '/projects/test-project' },
    ],
  },
  {
    root: '/projects/other-project',
    name: 'other-project',
    targets: [
      { name: 'default', entry: 'app.ato:Main', root: '/projects/other-project' },
    ],
  },
];

const sampleBuilds: Build[] = [
  {
    name: 'default',
    displayName: 'test-project:default',
    projectName: 'test-project',
    status: 'success',
    elapsedSeconds: 5.2,
    warnings: 2,
    errors: 0,
    returnCode: 0,
  },
  {
    name: 'debug',
    displayName: 'test-project:debug',
    projectName: 'test-project',
    status: 'failed',
    elapsedSeconds: 3.1,
    warnings: 0,
    errors: 3,
    returnCode: 1,
  },
];

const sampleProblems: Problem[] = [
  {
    id: '1',
    level: 'error',
    message: 'Type error',
    file: 'main.ato',
    line: 10,
    buildName: 'default',
    stage: 'compile',
  },
  {
    id: '2',
    level: 'warning',
    message: 'Unused variable',
    file: 'main.ato',
    line: 20,
    buildName: 'default',
    stage: 'lint',
  },
  {
    id: '3',
    level: 'error',
    message: 'Missing import',
    buildName: 'debug',
    stage: 'compile',
  },
];

describe('Zustand Store', () => {
  beforeEach(() => {
    resetStore();
  });

  describe('connection state', () => {
    it('starts disconnected', () => {
      expect(useStore.getState().isConnected).toBe(false);
    });

    it('can set connection state', () => {
      useStore.getState().setConnected(true);
      expect(useStore.getState().isConnected).toBe(true);

      useStore.getState().setConnected(false);
      expect(useStore.getState().isConnected).toBe(false);
    });
  });

  describe('replaceState', () => {
    it('replaces state from WebSocket broadcast', () => {
      useStore.getState().replaceState({
        projects: sampleProjects,
        builds: sampleBuilds,
      });

      const state = useStore.getState();
      expect(state.projects).toEqual(sampleProjects);
      expect(state.builds).toEqual(sampleBuilds);
      expect(state.isConnected).toBe(true); // Always sets connected
    });

    it('preserves unreplaced state', () => {
      useStore.setState({ selectedProjectRoot: '/test' });
      useStore.getState().replaceState({ selectedBuildName: 'release' });

      const state = useStore.getState();
      expect(state.selectedProjectRoot).toBe('/test');
      expect(state.selectedBuildName).toBe('release');
    });
  });

  describe('project actions', () => {
    beforeEach(() => {
      useStore.setState({ projects: sampleProjects });
    });

    it('can set projects', () => {
      useStore.getState().setProjects([sampleProjects[0]]);
      expect(useStore.getState().projects).toHaveLength(1);
    });

    it('can select project', () => {
      useStore.getState().selectProject('/projects/test-project');
      expect(useStore.getState().selectedProjectRoot).toBe('/projects/test-project');

      useStore.getState().selectProject(null);
      expect(useStore.getState().selectedProjectRoot).toBeNull();
    });

    it('can toggle target selection', () => {
      useStore.getState().toggleTarget('default');
      expect(useStore.getState().selectedTargetNames).toContain('default');

      useStore.getState().toggleTarget('debug');
      expect(useStore.getState().selectedTargetNames).toEqual(['default', 'debug']);

      useStore.getState().toggleTarget('default');
      expect(useStore.getState().selectedTargetNames).toEqual(['debug']);
    });

    it('can toggle target expanded state', () => {
      useStore.getState().toggleTargetExpanded('default');
      expect(useStore.getState().expandedTargets).toContain('default');

      useStore.getState().toggleTargetExpanded('default');
      expect(useStore.getState().expandedTargets).not.toContain('default');
    });
  });

  describe('build actions', () => {
    it('can set builds', () => {
      useStore.getState().setBuilds(sampleBuilds);
      expect(useStore.getState().builds).toEqual(sampleBuilds);
    });

    it('can set queued builds', () => {
      const queuedBuilds = [{ ...sampleBuilds[0], status: 'queued' as const }];
      useStore.getState().setQueuedBuilds(queuedBuilds);
      expect(useStore.getState().queuedBuilds).toEqual(queuedBuilds);
    });

    it('can select build', () => {
      useStore.getState().selectBuild('default');
      expect(useStore.getState().selectedBuildName).toBe('default');

      useStore.getState().selectBuild(null);
      expect(useStore.getState().selectedBuildName).toBeNull();
    });
  });

  describe('problem actions', () => {
    it('can set problems', () => {
      useStore.getState().setProblems(sampleProblems);
      expect(useStore.getState().problems).toEqual(sampleProblems);
      expect(useStore.getState().isLoadingProblems).toBe(false);
    });
  });

  describe('project data actions', () => {
    it('can set project modules', () => {
      const modules = [{ name: 'App', type: 'module' as const, file: 'main.ato', entry: 'main.ato:App' }];
      useStore.getState().setProjectModules('/project', modules);
      expect(useStore.getState().projectModules['/project']).toEqual(modules);
    });

    it('can set project files', () => {
      const files = [{ name: 'main.ato', path: '/project/main.ato', type: 'file' as const }];
      useStore.getState().setProjectFiles('/project', files);
      expect(useStore.getState().projectFiles['/project']).toEqual(files);
    });

    it('can set project dependencies', () => {
      const deps = [{ identifier: 'atopile/resistors', version: '1.0.0', name: 'resistors', publisher: 'atopile' }];
      useStore.getState().setProjectDependencies('/project', deps);
      expect(useStore.getState().projectDependencies['/project']).toEqual(deps);
    });
  });

  describe('reset action', () => {
    it('can reset to initial state', () => {
      useStore.setState({
        isConnected: true,
        projects: sampleProjects,
        selectedProjectRoot: '/test',
      });

      useStore.getState().reset();

      const state = useStore.getState();
      expect(state.isConnected).toBe(false);
      expect(state.projects).toEqual([]);
      expect(state.selectedProjectRoot).toBeNull();
    });
  });
});

describe('Store Selectors', () => {
  beforeEach(() => {
    resetStore();
  });

  describe('useSelectedProject', () => {
    it('returns null when no project selected', () => {
      useStore.setState({ projects: sampleProjects, selectedProjectRoot: null });
      const { result } = renderHook(() => useSelectedProject());
      expect(result.current).toBeNull();
    });

    it('returns selected project when one is selected', () => {
      useStore.setState({
        projects: sampleProjects,
        selectedProjectRoot: '/projects/test-project',
      });
      const { result } = renderHook(() => useSelectedProject());
      expect(result.current?.name).toBe('test-project');
    });
  });

  describe('useSelectedBuild', () => {
    it('returns null when no build selected', () => {
      useStore.setState({ builds: sampleBuilds, selectedBuildName: null });
      const { result } = renderHook(() => useSelectedBuild());
      expect(result.current).toBeNull();
    });

    it('returns selected build when one is selected', () => {
      useStore.setState({
        builds: sampleBuilds,
        selectedBuildName: 'default',
      });
      const { result } = renderHook(() => useSelectedBuild());
      expect(result.current?.name).toBe('default');
    });
  });

  describe('useFilteredProblems', () => {
    beforeEach(() => {
      useStore.setState({ problems: sampleProblems });
    });

    it('returns all problems when no filter', () => {
      useStore.setState({
        problemFilter: { levels: ['error', 'warning'], buildNames: [], stageIds: [] },
      });
      const { result } = renderHook(() => useFilteredProblems());
      expect(result.current).toHaveLength(3);
    });

    it('filters by level', () => {
      useStore.setState({
        problemFilter: { levels: ['error'], buildNames: [], stageIds: [] },
      });
      const { result } = renderHook(() => useFilteredProblems());
      expect(result.current).toHaveLength(2);
      expect(result.current.every((p) => p.level === 'error')).toBe(true);
    });

    it('filters by build name', () => {
      useStore.setState({
        problemFilter: { levels: ['error', 'warning'], buildNames: ['default'], stageIds: [] },
      });
      const { result } = renderHook(() => useFilteredProblems());
      expect(result.current).toHaveLength(2);
      expect(result.current.every((p) => p.buildName === 'default')).toBe(true);
    });

    it('filters by stage', () => {
      useStore.setState({
        problemFilter: { levels: ['error', 'warning'], buildNames: [], stageIds: ['compile'] },
      });
      const { result } = renderHook(() => useFilteredProblems());
      expect(result.current).toHaveLength(2);
      expect(result.current.every((p) => p.stage === 'compile')).toBe(true);
    });
  });

  describe('useFilteredLogs', () => {
    beforeEach(() => {
      useStore.setState({ logEntries: sampleLogs });
    });

    it('filters by enabled log levels', () => {
      useStore.setState({ enabledLogLevels: ['ERROR'] });
      const { result } = renderHook(() => useFilteredLogs());
      expect(result.current).toHaveLength(1);
      expect(result.current[0].level).toBe('ERROR');
    });

    it('filters by search query', () => {
      useStore.setState({
        enabledLogLevels: ['INFO', 'WARNING', 'ERROR', 'DEBUG'],
        logSearchQuery: 'build',
      });
      const { result } = renderHook(() => useFilteredLogs());
      expect(result.current).toHaveLength(1);
      expect(result.current[0].message).toContain('build');
    });

    it('combines level and search filters', () => {
      useStore.setState({
        enabledLogLevels: ['INFO', 'WARNING'],
        logSearchQuery: 'warning',
      });
      const { result } = renderHook(() => useFilteredLogs());
      expect(result.current).toHaveLength(1);
      expect(result.current[0].level).toBe('WARNING');
    });
  });
});
