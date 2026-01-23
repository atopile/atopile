/**
 * Hook tests
 * Tests custom hooks for state management and API calls
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
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

import { sendAction } from '../api/websocket';

const mockProjectsList = vi.fn();
const mockProblemsList = vi.fn();

vi.mock('../api/client', () => ({
  api: {
    projects: { list: mockProjectsList },
    problems: { list: mockProblemsList },
  },
}));

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

  it('selectProject sends action', () => {
    const { result } = renderHook(() => useProjects());

    act(() => {
      result.current.selectProject('/projects/test');
    });

    expect(useStore.getState().selectedProjectRoot).toBe('/projects/test');
  });

  it('toggleTarget updates selection', () => {
    const { result } = renderHook(() => useProjects());

    act(() => {
      result.current.toggleTarget('default');
    });

    expect(useStore.getState().selectedTargetNames).toContain('default');
  });

  it('toggleTargetExpanded updates UI', () => {
    const { result } = renderHook(() => useProjects());

    act(() => {
      result.current.toggleTargetExpanded('default');
    });

    expect(useStore.getState().expandedTargets).toContain('default');
  });

  it('refresh sends action', async () => {
    const { result } = renderHook(() => useProjects());

    mockProjectsList.mockResolvedValueOnce({ projects: sampleProjects });
    await act(async () => {
      await result.current.refresh();
    });

    expect(mockProjectsList).toHaveBeenCalled();
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

  it('selectBuild updates store', () => {
    const { result } = renderHook(() => useBuilds());

    act(() => {
      result.current.selectBuild('default');
    });

    expect(useStore.getState().selectedBuildName).toBe('default');
  });

  it('startBuild sends action', async () => {
    const { result } = renderHook(() => useBuilds());

    await act(async () => {
      await result.current.startBuild('/projects/test', ['default']);
    });

    expect(sendAction).toHaveBeenCalledWith('build', {
      projectRoot: '/projects/test',
      targets: ['default'],
    });
  });

  it('cancelBuild sends action', async () => {
    const { result } = renderHook(() => useBuilds());

    await act(async () => {
      await result.current.cancelBuild('build-123');
    });

    expect(sendAction).toHaveBeenCalledWith('cancelBuild', { buildId: 'build-123' });
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

  it('refresh fetches problems', async () => {
    const { result } = renderHook(() => useProblems());

    mockProblemsList.mockResolvedValueOnce({ problems: sampleProblems });
    await act(async () => {
      await result.current.refresh();
    });

    expect(mockProblemsList).toHaveBeenCalled();
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
