/**
 * Hook tests
 * Tests custom hooks for state management and API calls
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useStore } from '../store';
import { useProjects } from '../hooks/useProjects';
import { useBuilds } from '../hooks/useBuilds';
import { useProblems } from '../hooks/useProblems';
import { useConnection } from '../hooks/useConnection';
import type { Project, Build, Problem } from '../types/build';

// Mock the websocket module
vi.mock('../api/websocket', () => ({
  sendAction: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => true),
}));

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    projects: {
      list: vi.fn(),
    },
    builds: {
      start: vi.fn(),
      cancel: vi.fn(),
      history: vi.fn(),
      active: vi.fn(),
      queue: vi.fn(),
      status: vi.fn(),
    },
    problems: {
      list: vi.fn(),
    },
  },
}));

import { sendAction } from '../api/websocket';
import { api } from '../api/client';

// Helper to reset store state
const resetStore = () => {
  useStore.setState({
    isConnected: false,
    projects: [],
    selectedProjectRoot: null,
    selectedTargetNames: [],
    builds: [],
    queuedBuilds: [],
    selectedBuildName: null,
    problems: [],
    isLoadingProblems: false,
    problemFilter: { levels: ['error', 'warning'], buildNames: [], stageIds: [] },
    expandedTargets: [],
  });
};

const sampleProjects: Project[] = [
  {
    root: '/projects/test',
    name: 'test',
    targets: [
      { name: 'default', entry: 'main.ato:App', root: '/projects/test' },
    ],
  },
];

const sampleBuilds: Build[] = [
  {
    name: 'default',
    displayName: 'test:default',
    projectName: 'test',
    status: 'success',
    elapsedSeconds: 5.0,
    warnings: 0,
    errors: 0,
    returnCode: 0,
  },
];

describe('useProjects hook', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('returns projects from store', () => {
    useStore.setState({ projects: sampleProjects });
    const { result } = renderHook(() => useProjects());
    expect(result.current.projects).toEqual(sampleProjects);
  });

  it('returns selected project root', () => {
    useStore.setState({ selectedProjectRoot: '/projects/test' });
    const { result } = renderHook(() => useProjects());
    expect(result.current.selectedProjectRoot).toBe('/projects/test');
  });

  it('returns selected project when root matches', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test',
    });
    const { result } = renderHook(() => useProjects());
    expect(result.current.selectedProject?.name).toBe('test');
  });

  it('selectProject updates store and sends action', () => {
    const { result } = renderHook(() => useProjects());

    act(() => {
      result.current.selectProject('/projects/test');
    });

    expect(useStore.getState().selectedProjectRoot).toBe('/projects/test');
    expect(sendAction).toHaveBeenCalledWith('selectProject', { projectRoot: '/projects/test' });
  });

  it('toggleTarget updates store and sends action', () => {
    const { result } = renderHook(() => useProjects());

    act(() => {
      result.current.toggleTarget('default');
    });

    expect(useStore.getState().selectedTargetNames).toContain('default');
    expect(sendAction).toHaveBeenCalledWith('toggleTarget', { targetName: 'default' });
  });

  it('toggleTargetExpanded updates store and sends action', () => {
    const { result } = renderHook(() => useProjects());

    act(() => {
      result.current.toggleTargetExpanded('default');
    });

    expect(useStore.getState().expandedTargets).toContain('default');
    expect(sendAction).toHaveBeenCalledWith('toggleTargetExpanded', { targetName: 'default' });
  });

  it('refresh calls API and updates store', async () => {
    (api.projects.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      projects: sampleProjects,
    });

    const { result } = renderHook(() => useProjects());

    await act(async () => {
      await result.current.refresh();
    });

    expect(api.projects.list).toHaveBeenCalled();
    expect(useStore.getState().projects).toEqual(sampleProjects);
  });
});

describe('useBuilds hook', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('returns builds from store', () => {
    useStore.setState({ builds: sampleBuilds });
    const { result } = renderHook(() => useBuilds());
    expect(result.current.builds).toEqual(sampleBuilds);
  });

  it('returns queued builds', () => {
    const queuedBuilds = [{ ...sampleBuilds[0], status: 'queued' as const }];
    useStore.setState({ queuedBuilds });
    const { result } = renderHook(() => useBuilds());
    expect(result.current.queuedBuilds).toEqual(queuedBuilds);
  });

  it('allBuilds combines queued and completed builds', () => {
    const queuedBuilds = [{ ...sampleBuilds[0], name: 'queued', status: 'queued' as const }];
    useStore.setState({ builds: sampleBuilds, queuedBuilds });
    const { result } = renderHook(() => useBuilds());
    expect(result.current.allBuilds).toHaveLength(2);
  });

  it('selectBuild updates store and sends action', () => {
    const { result } = renderHook(() => useBuilds());

    act(() => {
      result.current.selectBuild('default');
    });

    expect(useStore.getState().selectedBuildName).toBe('default');
    expect(sendAction).toHaveBeenCalledWith('selectBuild', { buildName: 'default' });
  });

  it('startBuild calls API', async () => {
    (api.builds.start as ReturnType<typeof vi.fn>).mockResolvedValue(sampleBuilds[0]);

    const { result } = renderHook(() => useBuilds());

    await act(async () => {
      await result.current.startBuild('/projects/test', ['default']);
    });

    expect(api.builds.start).toHaveBeenCalledWith('/projects/test', ['default']);
  });

  it('cancelBuild calls API', async () => {
    (api.builds.cancel as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    const { result } = renderHook(() => useBuilds());

    await act(async () => {
      await result.current.cancelBuild('build-123');
    });

    expect(api.builds.cancel).toHaveBeenCalledWith('build-123');
  });

});

describe('useProblems hook', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  const sampleProblems: Problem[] = [
    { id: '1', level: 'error', message: 'Error 1' },
    { id: '2', level: 'warning', message: 'Warning 1' },
  ];

  it('returns problems from store', () => {
    useStore.setState({ problems: sampleProblems });
    const { result } = renderHook(() => useProblems());
    expect(result.current.problems).toEqual(sampleProblems);
  });

  it('returns filtered problems', () => {
    useStore.setState({
      problems: sampleProblems,
      problemFilter: { levels: ['error'], buildNames: [], stageIds: [] },
    });
    const { result } = renderHook(() => useProblems());
    expect(result.current.filteredProblems).toHaveLength(1);
    expect(result.current.filteredProblems[0].level).toBe('error');
  });

  it('returns error and warning counts', () => {
    useStore.setState({ problems: sampleProblems });
    const { result } = renderHook(() => useProblems());
    expect(result.current.errorCount).toBe(1);
    expect(result.current.warningCount).toBe(1);
  });

  it('refresh calls API and updates store', async () => {
    (api.problems.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      problems: sampleProblems,
    });

    const { result } = renderHook(() => useProblems());

    await act(async () => {
      await result.current.refresh();
    });

    expect(api.problems.list).toHaveBeenCalled();
    expect(useStore.getState().problems).toEqual(sampleProblems);
  });
});

describe('useConnection hook', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('returns connection state', () => {
    useStore.setState({ isConnected: true });
    const { result } = renderHook(() => useConnection());
    expect(result.current.isConnected).toBe(true);
  });

  it('returns disconnected state', () => {
    useStore.setState({ isConnected: false });
    const { result } = renderHook(() => useConnection());
    expect(result.current.isConnected).toBe(false);
  });
});
