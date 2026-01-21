/**
 * Connected component tests
 * Tests for hook-based components (ProjectsPanelConnected, BuildQueuePanelConnected, ProblemsPanelConnected)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useStore } from '../store';
import { BuildQueuePanelConnected } from '../components/BuildQueuePanelConnected';
import { ProblemsPanelConnected } from '../components/ProblemsPanelConnected';
import { ProjectsPanelConnected } from '../components/ProjectsPanelConnected';
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
    builds: {
      cancel: vi.fn().mockResolvedValue(undefined),
      cancelAll: vi.fn().mockResolvedValue(undefined),
      start: vi.fn().mockResolvedValue({ name: 'default', status: 'queued' }),
    },
    modules: {
      list: vi.fn().mockResolvedValue({ modules: [] }),
    },
    files: {
      list: vi.fn().mockResolvedValue({ files: [] }),
    },
    dependencies: {
      list: vi.fn().mockResolvedValue({ dependencies: [] }),
    },
    problems: {
      list: vi.fn().mockResolvedValue({ problems: [] }),
    },
  },
}));

// Helper to reset store state
const resetStore = () => {
  useStore.setState({
    isConnected: true,
    projects: [],
    selectedProjectRoot: null,
    selectedTargetNames: [],
    builds: [],
    queuedBuilds: [],
    selectedBuildName: null,
    problems: [],
    isLoadingProblems: false,
    problemFilter: { levels: ['error', 'warning'], buildNames: [], stageIds: [] },
    projectModules: {},
    projectFiles: {},
    projectDependencies: {},
    expandedTargets: [],
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

const sampleQueuedBuilds: Build[] = [
  {
    name: 'default',
    displayName: 'test-project:default',
    projectName: 'test-project',
    buildId: 'build-123',
    status: 'building',
    elapsedSeconds: 5.2,
    warnings: 0,
    errors: 0,
    returnCode: null,
    projectRoot: '/projects/test-project',
    targets: ['default'],
    startedAt: Date.now() / 1000 - 5,
    stages: [
      { name: 'parse', stageId: 'parse', status: 'success', elapsedSeconds: 1.0, infos: 0, warnings: 0, errors: 0, alerts: 0 },
      { name: 'compile', stageId: 'compile', displayName: 'Compiling', status: 'running', elapsedSeconds: 4.2, infos: 0, warnings: 0, errors: 0, alerts: 0 },
    ],
  },
  {
    name: 'debug',
    displayName: 'test-project:debug',
    projectName: 'test-project',
    buildId: 'build-124',
    status: 'queued',
    elapsedSeconds: 0,
    warnings: 0,
    errors: 0,
    returnCode: null,
    projectRoot: '/projects/test-project',
    targets: ['debug'],
    queuePosition: 2,
  },
];

const sampleProblems: Problem[] = [
  {
    id: '1',
    level: 'error',
    message: 'Type error in module',
    file: 'src/main.ato',
    line: 10,
    column: 5,
    stage: 'compile',
    buildName: 'default',
    projectName: 'test-project',
  },
  {
    id: '2',
    level: 'warning',
    message: 'Unused variable',
    file: 'src/main.ato',
    line: 20,
    stage: 'lint',
    buildName: 'default',
    projectName: 'test-project',
  },
  {
    id: '3',
    level: 'error',
    message: 'Missing import',
    file: 'src/power.ato',
    line: 5,
    stage: 'compile',
    buildName: 'debug',
    projectName: 'test-project',
  },
];

describe('BuildQueuePanelConnected', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('renders empty state when no queued builds', () => {
    useStore.setState({ queuedBuilds: [] });
    render(<BuildQueuePanelConnected />);
    expect(screen.getByText('No active builds')).toBeInTheDocument();
  });

  it('renders queued builds from store', () => {
    useStore.setState({ queuedBuilds: sampleQueuedBuilds });
    render(<BuildQueuePanelConnected />);

    // Should show project and target names - may appear multiple times
    const projectNames = screen.getAllByText('test-project');
    expect(projectNames.length).toBeGreaterThan(0);
    const targetNames = screen.getAllByText(':default');
    expect(targetNames.length).toBeGreaterThan(0);
  });

  it('shows current stage for building builds', () => {
    useStore.setState({ queuedBuilds: sampleQueuedBuilds });
    render(<BuildQueuePanelConnected />);

    // Should show the running stage name
    expect(screen.getByText('Compiling')).toBeInTheDocument();
  });

  it('renders cancel buttons for active builds', () => {
    useStore.setState({ queuedBuilds: sampleQueuedBuilds });
    const { container } = render(<BuildQueuePanelConnected />);

    const cancelButtons = container.querySelectorAll('.queue-item-cancel');
    expect(cancelButtons.length).toBeGreaterThan(0);
  });
});

describe('ProblemsPanelConnected', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('renders empty state when no problems', () => {
    useStore.setState({ problems: [] });
    render(<ProblemsPanelConnected />);
    expect(screen.getByText('No problems')).toBeInTheDocument();
  });

  it('renders problems from store', () => {
    useStore.setState({ problems: sampleProblems });
    render(<ProblemsPanelConnected />);

    expect(screen.getByText('Type error in module')).toBeInTheDocument();
    expect(screen.getByText('Unused variable')).toBeInTheDocument();
    expect(screen.getByText('Missing import')).toBeInTheDocument();
  });

  it('shows error and warning counts', () => {
    useStore.setState({ problems: sampleProblems });
    const { container } = render(<ProblemsPanelConnected />);

    // Should have filter buttons with counts
    const errorButton = container.querySelector('.filter-btn.error span');
    const warningButton = container.querySelector('.filter-btn.warning span');

    expect(errorButton?.textContent).toBe('2'); // 2 errors
    expect(warningButton?.textContent).toBe('1'); // 1 warning
  });

  it('groups problems by file', () => {
    useStore.setState({ problems: sampleProblems });
    render(<ProblemsPanelConnected />);

    expect(screen.getByText('main.ato')).toBeInTheDocument();
    expect(screen.getByText('power.ato')).toBeInTheDocument();
  });

  it('filters problems based on store filter', () => {
    useStore.setState({
      problems: sampleProblems,
      problemFilter: { levels: ['error'], buildNames: [], stageIds: [] },
    });
    render(<ProblemsPanelConnected />);

    // Should only show errors when filtered to error level
    expect(screen.getByText('Type error in module')).toBeInTheDocument();
    expect(screen.getByText('Missing import')).toBeInTheDocument();
    // Warning should NOT appear when filter is set to error only
    expect(screen.queryByText('Unused variable')).not.toBeInTheDocument();
  });
});

describe('ProjectsPanelConnected', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('renders projects from store', () => {
    useStore.setState({ projects: sampleProjects });
    render(<ProjectsPanelConnected />);

    expect(screen.getByText('test-project')).toBeInTheDocument();
    expect(screen.getByText('other-project')).toBeInTheDocument();
  });

  it('highlights selected project', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test-project',
    });
    const { container } = render(<ProjectsPanelConnected />);

    const selectedItem = container.querySelector('.project-item.selected');
    expect(selectedItem).toBeInTheDocument();
  });

  it('shows targets when project is selected', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test-project',
    });
    render(<ProjectsPanelConnected />);

    // Should show targets for selected project
    expect(screen.getByText('default')).toBeInTheDocument();
    expect(screen.getByText('debug')).toBeInTheDocument();
  });

  it('shows checkboxes for target selection', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test-project',
    });
    const { container } = render(<ProjectsPanelConnected />);

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    expect(checkboxes).toHaveLength(2); // Two targets
  });

  it('shows checked state for selected targets', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test-project',
      selectedTargetNames: ['default'],
    });
    const { container } = render(<ProjectsPanelConnected />);

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    const checkedCheckboxes = Array.from(checkboxes).filter(
      (cb) => (cb as HTMLInputElement).checked
    );
    expect(checkedCheckboxes).toHaveLength(1);
  });

  it('shows build button when targets are selected', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test-project',
      selectedTargetNames: ['default'],
    });
    render(<ProjectsPanelConnected />);

    expect(screen.getByText(/Build \(1 target\)/)).toBeInTheDocument();
  });

  it('shows correct count in build button', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test-project',
      selectedTargetNames: ['default', 'debug'],
    });
    render(<ProjectsPanelConnected />);

    expect(screen.getByText(/Build \(2 targets\)/)).toBeInTheDocument();
  });

  it('does not show build button when no targets selected', () => {
    useStore.setState({
      projects: sampleProjects,
      selectedProjectRoot: '/projects/test-project',
      selectedTargetNames: [],
    });
    render(<ProjectsPanelConnected />);

    expect(screen.queryByText(/Build/)).not.toBeInTheDocument();
  });

  it('clicking project header selects it', () => {
    useStore.setState({ projects: sampleProjects });
    render(<ProjectsPanelConnected />);

    fireEvent.click(screen.getByText('test-project'));
    expect(useStore.getState().selectedProjectRoot).toBe('/projects/test-project');
  });
});
