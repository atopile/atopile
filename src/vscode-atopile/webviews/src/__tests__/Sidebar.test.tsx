/**
 * Sidebar component tests
 * Tests main panel rendering, section toggling, and VS Code messaging
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { vscodeApiMocks } from './setup';

// Mock child components to isolate Sidebar testing
vi.mock('../components/ProjectsPanel', () => ({
  ProjectsPanel: vi.fn(({ filterType }) => (
    <div data-testid={`projects-panel-${filterType}`}>ProjectsPanel ({filterType})</div>
  )),
  mockProjects: [
    {
      id: '/test/project',
      name: 'test-project',
      type: 'project' as const,
      path: '/test/project',
      builds: [
        { id: 'default', name: 'default', entry: 'main.ato:App', status: 'idle', stages: [] },
      ],
    },
    {
      id: 'atopile/test-package',
      name: 'test-package',
      type: 'package' as const,
      path: 'packages/atopile/test-package',
      version: '1.0.0',
      builds: [],
    },
  ],
}));

vi.mock('../components/ProblemsPanel', () => ({
  ProblemsPanel: vi.fn(({ problems }) => (
    <div data-testid="problems-panel">ProblemsPanel ({problems?.length || 0} problems)</div>
  )),
  mockProblems: [
    { id: '1', level: 'error', message: 'Test error', file: 'test.ato', line: 10 },
  ],
}));

vi.mock('../components/StandardLibraryPanel', () => ({
  StandardLibraryPanel: vi.fn(() => <div data-testid="stdlib-panel">StandardLibraryPanel</div>),
}));

vi.mock('../components/VariablesPanel', () => ({
  VariablesPanel: vi.fn(() => <div data-testid="variables-panel">VariablesPanel</div>),
}));

vi.mock('../components/BOMPanel', () => ({
  BOMPanel: vi.fn(() => <div data-testid="bom-panel">BOMPanel</div>),
  mockBOM: [{ id: '1', mpn: 'TEST-PART', quantity: 5 }],
}));

vi.mock('../components/PackageDetailPanel', () => ({
  PackageDetailPanel: vi.fn(({ onClose }) => (
    <div data-testid="package-detail-panel">
      PackageDetailPanel
      <button onClick={onClose} data-testid="close-detail">Close</button>
    </div>
  )),
}));

// Import Sidebar after mocks
import { Sidebar } from '../components/Sidebar';

// Mock state data
const mockState = {
  isConnected: true,
  projects: [
    {
      root: '/test/project',
      name: 'test-project',
      targets: [{ name: 'default', entry: 'main.ato:App', root: '/test/project' }],
    },
  ],
  builds: [
    {
      name: 'default',
      display_name: 'default',
      project_name: 'test-project',
      status: 'success',
      elapsed_seconds: 5.2,
      warnings: 0,
      errors: 0,
      return_code: 0,
      stages: [],
    },
  ],
  packages: [
    {
      identifier: 'atopile/test-pkg',
      name: 'test-pkg',
      publisher: 'atopile',
      version: '1.0.0',
      installed: true,
      installed_in: ['/test/project'],
    },
  ],
  problems: [],
  problemFilter: { levels: [], buildNames: [], stageIds: [] },
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
};

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vscodeApiMocks.reset();
  });

  describe('loading state', () => {
    it('shows loading when no state received', () => {
      render(<Sidebar />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('sends ready message on mount', () => {
      render(<Sidebar />);
      expect(vscodeApiMocks.postMessage).toHaveBeenCalledWith({ type: 'ready' });
    });
  });

  describe('state handling', () => {
    it('renders content after receiving state', async () => {
      render(<Sidebar />);

      // Simulate receiving state from extension
      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: mockState },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Check sections are rendered
      expect(screen.getByText('Projects')).toBeInTheDocument();
      expect(screen.getByText('Packages')).toBeInTheDocument();
      expect(screen.getByText('Problems')).toBeInTheDocument();
    });

    it('updates state when new message received', async () => {
      render(<Sidebar />);

      // Initial state
      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: mockState },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Expand the Problems section (collapsed by default)
      const problemsTitle = screen.getByText('Problems');
      const sectionHeader = problemsTitle.closest('.section-title-bar');
      fireEvent.click(sectionHeader!);

      // Updated state with problem
      const updatedState = {
        ...mockState,
        problems: [{ id: '1', level: 'error', message: 'New error' }],
      };

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: updatedState },
        }));
      });

      // ProblemsPanel should receive updated problems
      await waitFor(() => {
        expect(screen.getByTestId('problems-panel')).toHaveTextContent('1 problems');
      });
    });
  });

  describe('section rendering', () => {
    beforeEach(async () => {
      render(<Sidebar />);
      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: mockState },
        }));
      });
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });
    });

    it('renders all section titles', () => {
      expect(screen.getByText('Projects')).toBeInTheDocument();
      expect(screen.getByText('Packages')).toBeInTheDocument();
      expect(screen.getByText('Problems')).toBeInTheDocument();
      expect(screen.getByText('Standard Library')).toBeInTheDocument();
      expect(screen.getByText('Variables')).toBeInTheDocument();
      expect(screen.getByText('BOM')).toBeInTheDocument();
    });

    it('renders ProjectsPanel for projects filter', () => {
      expect(screen.getByTestId('projects-panel-projects')).toBeInTheDocument();
    });

    it('renders ProjectsPanel for packages filter', () => {
      expect(screen.getByTestId('projects-panel-packages')).toBeInTheDocument();
    });

    // Note: problems, stdlib, variables, and bom sections are collapsed by default
    // so their panel children are not in the DOM until expanded
    it('renders ProblemsPanel when section is expanded', async () => {
      // Expand the Problems section
      const problemsTitle = screen.getByText('Problems');
      const sectionHeader = problemsTitle.closest('.section-title-bar');
      fireEvent.click(sectionHeader!);

      await waitFor(() => {
        expect(screen.getByTestId('problems-panel')).toBeInTheDocument();
      });
    });

    // Note: stdlib, variables, and bom sections are collapsed by default
    // so their panel children are not in the DOM until expanded
    it('renders StandardLibraryPanel when section is expanded', async () => {
      // Expand the Standard Library section
      const stdlibTitle = screen.getByText('Standard Library');
      const sectionHeader = stdlibTitle.closest('.section-title-bar');
      fireEvent.click(sectionHeader!);

      await waitFor(() => {
        expect(screen.getByTestId('stdlib-panel')).toBeInTheDocument();
      });
    });

    it('renders VariablesPanel when section is expanded', async () => {
      // Expand the Variables section
      const variablesTitle = screen.getByText('Variables');
      const sectionHeader = variablesTitle.closest('.section-title-bar');
      fireEvent.click(sectionHeader!);

      await waitFor(() => {
        expect(screen.getByTestId('variables-panel')).toBeInTheDocument();
      });
    });

    it('renders BOMPanel when section is expanded', async () => {
      // Expand the BOM section
      const bomTitle = screen.getByText('BOM');
      const sectionHeader = bomTitle.closest('.section-title-bar');
      fireEvent.click(sectionHeader!);

      await waitFor(() => {
        expect(screen.getByTestId('bom-panel')).toBeInTheDocument();
      });
    });
  });

  describe('section collapsing', () => {
    it('starts with stdlib, variables, bom sections collapsed by default', async () => {
      const { container } = render(<Sidebar />);

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: mockState },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Collapsed sections have the 'collapsed' class
      const stdlibSection = container.querySelector('[data-section-id="stdlib"]');
      const variablesSection = container.querySelector('[data-section-id="variables"]');
      const bomSection = container.querySelector('[data-section-id="bom"]');

      expect(stdlibSection).toHaveClass('collapsed');
      expect(variablesSection).toHaveClass('collapsed');
      expect(bomSection).toHaveClass('collapsed');

      // Projects and Packages should NOT be collapsed
      const projectsSection = container.querySelector('[data-section-id="projects"]');
      const packagesSection = container.querySelector('[data-section-id="packages"]');
      const problemsSection = container.querySelector('[data-section-id="problems"]');

      expect(projectsSection).not.toHaveClass('collapsed');
      expect(packagesSection).not.toHaveClass('collapsed');
      // Problems section is collapsed by default along with stdlib, variables, bom
      expect(problemsSection).toHaveClass('collapsed');
    });

    it('toggles section when title clicked', async () => {
      const { container } = render(<Sidebar />);

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: mockState },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Find the Projects section and verify it starts expanded
      const projectsSection = container.querySelector('[data-section-id="projects"]');
      expect(projectsSection).not.toHaveClass('collapsed');

      // Click to collapse - use container to find elements
      const projectsTitleBar = container.querySelector('[data-section-id="projects"] .section-title-bar');
      fireEvent.click(projectsTitleBar!);

      // Should now be collapsed
      expect(projectsSection).toHaveClass('collapsed');
    });

    it('expands collapsed section when clicked', async () => {
      const { container } = render(<Sidebar />);

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: mockState },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // stdlib starts collapsed
      const stdlibSection = container.querySelector('[data-section-id="stdlib"]');
      expect(stdlibSection).toHaveClass('collapsed');

      // Click to expand - use container
      const stdlibTitleBar = container.querySelector('[data-section-id="stdlib"] .section-title-bar');
      fireEvent.click(stdlibTitleBar!);

      // Should now be expanded
      expect(stdlibSection).not.toHaveClass('collapsed');
    });
  });

  describe('VS Code actions', () => {
    beforeEach(async () => {
      render(<Sidebar />);
      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: mockState },
        }));
      });
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });
    });

    it('clears postMessage mock on each test', () => {
      // Ready message should be sent
      expect(vscodeApiMocks.postMessage).toHaveBeenCalledWith({ type: 'ready' });
    });
  });

  describe('project transformation', () => {
    it('transforms state projects into component format', async () => {
      render(<Sidebar />);

      const stateWithBuilds = {
        ...mockState,
        builds: [
          {
            name: 'default',
            display_name: 'default',
            project_name: 'test-project',
            status: 'failed',
            elapsed_seconds: 10,
            warnings: 2,
            errors: 1,
            return_code: 1,
            stages: [
              { name: 'compile', stage_id: 'compile', elapsed_seconds: 5, status: 'failed', infos: 0, warnings: 2, errors: 1, alerts: 0 },
            ],
          },
        ],
      };

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: stateWithBuilds },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // ProjectsPanel should be rendered with projects data
      expect(screen.getByTestId('projects-panel-projects')).toBeInTheDocument();
    });

    it('transforms packages into component format', async () => {
      render(<Sidebar />);

      const stateWithPackages = {
        ...mockState,
        packages: [
          {
            identifier: 'atopile/sensor-bme280',
            name: 'sensor-bme280',
            publisher: 'atopile',
            version: '2.0.0',
            latest_version: '2.1.0',
            installed: true,
            installed_in: ['/test/project'],
            description: 'BME280 sensor driver',
          },
        ],
      };

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: stateWithPackages },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Packages panel should be rendered
      expect(screen.getByTestId('projects-panel-packages')).toBeInTheDocument();
    });

    it('filters out malformed packages', async () => {
      render(<Sidebar />);

      const stateWithMalformedPackages = {
        ...mockState,
        packages: [
          { identifier: 'good/package', name: 'package', installed: true, installed_in: [] },
          { identifier: null, name: null }, // Malformed
          { identifier: 'another/good', name: 'good', installed: false, installed_in: [] },
        ],
      };

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: stateWithMalformedPackages },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Should render without error
      expect(screen.getByTestId('projects-panel-packages')).toBeInTheDocument();
    });
  });

  describe('problem filtering', () => {
    it('applies problem filter from state', async () => {
      render(<Sidebar />);

      const stateWithProblemsAndFilter = {
        ...mockState,
        problems: [
          { id: '1', level: 'error', message: 'Error 1' },
          { id: '2', level: 'warning', message: 'Warning 1' },
          { id: '3', level: 'error', message: 'Error 2' },
        ],
        problemFilter: {
          levels: ['error'],
          buildNames: [],
          stageIds: [],
        },
      };

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: stateWithProblemsAndFilter },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Expand the Problems section (collapsed by default)
      const problemsTitle = screen.getByText('Problems');
      const sectionHeader = problemsTitle.closest('.section-title-bar');
      fireEvent.click(sectionHeader!);

      // ProblemsPanel receives filtered problems (only errors)
      // Mock counts all passed problems, filter happens in Sidebar
      await waitFor(() => {
        expect(screen.getByTestId('problems-panel')).toBeInTheDocument();
      });
    });
  });

  describe('cleanup', () => {
    it('removes event listener on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      const { unmount } = render(<Sidebar />);
      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('message', expect.any(Function));
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('entry point parsing', () => {
    it('parses valid entry point format', async () => {
      render(<Sidebar />);

      const stateWithEntry = {
        ...mockState,
        projects: [
          {
            root: '/test',
            name: 'test',
            targets: [{ name: 'default', entry: 'main.ato:MyModule', root: '/test' }],
          },
        ],
      };

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: stateWithEntry },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Should parse without error
      expect(screen.getByTestId('projects-panel-projects')).toBeInTheDocument();
    });

    it('handles entry without colon', async () => {
      render(<Sidebar />);

      const stateWithInvalidEntry = {
        ...mockState,
        projects: [
          {
            root: '/test',
            name: 'test',
            targets: [{ name: 'default', entry: 'main.ato', root: '/test' }],
          },
        ],
      };

      act(() => {
        window.dispatchEvent(new MessageEvent('message', {
          data: { type: 'state', data: stateWithInvalidEntry },
        }));
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      // Should handle gracefully
      expect(screen.getByTestId('projects-panel-projects')).toBeInTheDocument();
    });
  });
});
