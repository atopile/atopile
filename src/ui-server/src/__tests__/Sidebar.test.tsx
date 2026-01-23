/**
 * Sidebar component tests
 * Tests main panel rendering and section toggling.
 *
 * Architecture: Sidebar uses Zustand store for state and WebSocket for actions.
 * Panels start collapsed by default (via usePanelSizing hook).
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useStore } from '../store';

// Mock child components to isolate Sidebar testing
vi.mock('../components/ProjectsPanel', () => ({
  ProjectsPanel: vi.fn(({ filterType }) => (
    <div data-testid={`projects-panel-${filterType}`}>ProjectsPanel ({filterType})</div>
  )),
}));

vi.mock('../components/ProblemsPanel', () => ({
  ProblemsPanel: vi.fn(({ problems }) => (
    <div data-testid="problems-panel">ProblemsPanel ({problems?.length || 0} problems)</div>
  )),
}));

vi.mock('../components/StandardLibraryPanel', () => ({
  StandardLibraryPanel: vi.fn(() => <div data-testid="stdlib-panel">StandardLibraryPanel</div>),
}));

vi.mock('../components/VariablesPanel', () => ({
  VariablesPanel: vi.fn(() => <div data-testid="variables-panel">VariablesPanel</div>),
}));

vi.mock('../components/BOMPanel', () => ({
  BOMPanel: vi.fn(() => <div data-testid="bom-panel">BOMPanel</div>),
}));

vi.mock('../components/BuildQueuePanel', () => ({
  BuildQueuePanel: vi.fn(() => <div data-testid="build-queue-panel">BuildQueuePanel</div>),
}));

vi.mock('../components/PackageDetailPanel', () => ({
  PackageDetailPanel: vi.fn(({ onClose }) => (
    <div data-testid="package-detail-panel">
      PackageDetailPanel
      <button onClick={onClose} data-testid="close-detail">Close</button>
    </div>
  )),
}));

vi.mock('../api/websocket', () => ({
  sendAction: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => true),
}));

const mockApi = {
  projects: { list: vi.fn() },
  builds: { history: vi.fn(), active: vi.fn() },
  packages: { summary: vi.fn() },
  problems: { list: vi.fn() },
  stdlib: { list: vi.fn() },
};

vi.mock('../api/client', () => ({
  api: mockApi,
}));

// Import after mocks
import { Sidebar } from '../components/Sidebar';

// Mock state data - minimal state needed for Sidebar to render
const mockState = {
  isConnected: true,
  projects: [
    {
      root: '/test/project',
      name: 'test-project',
      targets: [{ name: 'default', entry: 'main.ato:App', root: '/test/project' }],
    },
  ],
  builds: [],
  queuedBuilds: [],
  packages: [],
  problems: [],
  problemFilter: { levels: ['error', 'warning'], buildNames: [], stageIds: [] },
  stdlibItems: [],
  isLoadingStdlib: false,
  bomData: null,
  isLoadingBom: false,
  bomError: null,
  selectedPackageDetails: null,
  isLoadingPackageDetails: false,
  packageDetailsError: null,
  projectModules: {},
  isLoadingModules: false,
  projectFiles: {},
  isLoadingFiles: false,
  projectDependencies: {},
  isLoadingDependencies: false,
  currentVariablesData: null,
  isLoadingVariables: false,
  variablesError: null,
  selectedProjectRoot: null,
  selectedTargetNames: [],
  installingPackageIds: [],
  installError: null,
  isLoadingProjects: false,
  projectsError: null,
  isLoadingPackages: false,
  packagesError: null,
  isLoadingProblems: false,
  expandedTargets: [],
  atopile: {
    currentVersion: '0.14.0',
    source: 'release' as const,
    localPath: null,
    branch: null,
    availableVersions: [],
    availableBranches: [],
    detectedInstallations: [],
    isInstalling: false,
    installProgress: null,
    error: null,
  },
  developerMode: false,
  selectedBuildId: null,
  selectedBuildName: null,
  selectedProjectName: null,
};

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store with mock state
    useStore.setState(mockState);
  });

  describe('rendering', () => {
    it('renders all section titles', () => {
      render(<Sidebar />);
      expect(screen.getByText('Projects')).toBeInTheDocument();
      expect(screen.getByText('Build Queue')).toBeInTheDocument();
      expect(screen.getByText('Packages')).toBeInTheDocument();
      expect(screen.getByText('Problems')).toBeInTheDocument();
      expect(screen.getByText('Standard Library')).toBeInTheDocument();
      expect(screen.getByText('Variables')).toBeInTheDocument();
      expect(screen.getByText('BOM')).toBeInTheDocument();
    });

    it('renders the unified layout container', () => {
      const { container } = render(<Sidebar />);
      expect(container.querySelector('.unified-layout')).toBeInTheDocument();
    });

    it('renders the panel header', () => {
      const { container } = render(<Sidebar />);
      expect(container.querySelector('.panel-header')).toBeInTheDocument();
    });
  });

  describe('section collapsing', () => {
    it('starts with all sections collapsed by default', () => {
      const { container } = render(<Sidebar />);

      // All sections should be collapsed by default (usePanelSizing behavior)
      const sections = container.querySelectorAll('.collapsible-section');
      sections.forEach(section => {
        expect(section).toHaveClass('collapsed');
      });
    });

    it('toggles section when title bar clicked', () => {
      const { container } = render(<Sidebar />);

      const problemsSection = container.querySelector('[data-section-id="problems"]');
      expect(problemsSection).toHaveClass('collapsed');

      // Click to expand
      const problemsTitleBar = container.querySelector('[data-section-id="problems"] .section-title-bar');
      fireEvent.click(problemsTitleBar!);

      expect(problemsSection).not.toHaveClass('collapsed');
    });

    it('expands then collapses section on double click', () => {
      const { container } = render(<Sidebar />);

      const stdlibSection = container.querySelector('[data-section-id="stdlib"]');
      const stdlibTitleBar = container.querySelector('[data-section-id="stdlib"] .section-title-bar');

      // Expand
      fireEvent.click(stdlibTitleBar!);
      expect(stdlibSection).not.toHaveClass('collapsed');

      // Collapse
      fireEvent.click(stdlibTitleBar!);
      expect(stdlibSection).toHaveClass('collapsed');
    });
  });

  describe('panel content rendering when expanded', () => {
    it('renders ProblemsPanel when problems section is expanded', () => {
      const { container } = render(<Sidebar />);

      // Expand the Problems section
      const problemsTitleBar = container.querySelector('[data-section-id="problems"] .section-title-bar');
      fireEvent.click(problemsTitleBar!);

      expect(screen.getByTestId('problems-panel')).toBeInTheDocument();
    });

    it('renders StandardLibraryPanel when stdlib section is expanded', () => {
      const { container } = render(<Sidebar />);

      const stdlibTitleBar = container.querySelector('[data-section-id="stdlib"] .section-title-bar');
      fireEvent.click(stdlibTitleBar!);

      expect(screen.getByTestId('stdlib-panel')).toBeInTheDocument();
    });

    it('renders VariablesPanel when variables section is expanded', () => {
      const { container } = render(<Sidebar />);

      const variablesTitleBar = container.querySelector('[data-section-id="variables"] .section-title-bar');
      fireEvent.click(variablesTitleBar!);

      expect(screen.getByTestId('variables-panel')).toBeInTheDocument();
    });

    it('renders BOMPanel when bom section is expanded', () => {
      const { container } = render(<Sidebar />);

      const bomTitleBar = container.querySelector('[data-section-id="bom"] .section-title-bar');
      fireEvent.click(bomTitleBar!);

      expect(screen.getByTestId('bom-panel')).toBeInTheDocument();
    });
  });

  describe('initial refresh', () => {
    it('fetches initial data on mount', async () => {
      mockApi.projects.list.mockResolvedValueOnce({ projects: [] });
      mockApi.builds.history.mockResolvedValueOnce({ builds: [] });
      mockApi.builds.active.mockResolvedValueOnce({ builds: [] });
      mockApi.packages.summary.mockResolvedValueOnce({ packages: [] });
      mockApi.problems.list.mockResolvedValueOnce({ problems: [] });
      mockApi.stdlib.list.mockResolvedValueOnce({ items: [] });

      render(<Sidebar />);

      await waitFor(() => {
        expect(mockApi.projects.list).toHaveBeenCalled();
        expect(mockApi.builds.history).toHaveBeenCalled();
        expect(mockApi.builds.active).toHaveBeenCalled();
        expect(mockApi.packages.summary).toHaveBeenCalled();
        expect(mockApi.problems.list).toHaveBeenCalled();
        expect(mockApi.stdlib.list).toHaveBeenCalled();
      }, { timeout: 200 });
    });
  });

  describe('cleanup', () => {
    it('removes event listener on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      const { unmount } = render(<Sidebar />);
      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalled();
      removeEventListenerSpy.mockRestore();
    });
  });
});
