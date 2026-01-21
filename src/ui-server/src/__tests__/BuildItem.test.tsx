/**
 * BuildItem component tests
 * Tests build item rendering, expansion, stage display, and interactions
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BuildItem } from '../components/BuildItem';
import type { Build, BuildStage } from '../types/build';

// Test data - uses camelCase to match TypeScript interfaces
const mockStages: BuildStage[] = [
  {
    name: '[bold]init-build-context[/bold]',
    stageId: 'init',
    elapsedSeconds: 0.5,
    status: 'success',
    infos: 10,
    warnings: 0,
    errors: 0,
    alerts: 0,
  },
  {
    name: "compile 'App'",
    stageId: 'compile',
    elapsedSeconds: 2.3,
    status: 'success',
    infos: 50,
    warnings: 2,
    errors: 0,
    alerts: 0,
  },
  {
    name: 'picker',
    stageId: 'picker',
    elapsedSeconds: 5.7,
    status: 'warning',
    infos: 100,
    warnings: 5,
    errors: 1,
    alerts: 0,
  },
];

const mockBuild: Build = {
  name: 'default',
  displayName: 'default',
  projectName: 'my-project',
  status: 'warning',
  elapsedSeconds: 8.5,
  warnings: 7,
  errors: 1,
  returnCode: 0,
  stages: mockStages,
};

const defaultProps = {
  build: mockBuild,
  isSelected: false,
  selectedStageName: null,
  onSelectBuild: vi.fn(),
  onSelectStage: vi.fn(),
};

describe('BuildItem', () => {
  describe('basic rendering', () => {
    it('renders build name', () => {
      render(<BuildItem {...defaultProps} />);
      expect(screen.getByText('default')).toBeInTheDocument();
    });

    it('renders status icon', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      expect(container.querySelector('.build-status')).toBeInTheDocument();
    });

    it('renders current stage name', () => {
      render(<BuildItem {...defaultProps} />);
      // Last stage is 'picker'
      expect(screen.getByText('picker')).toBeInTheDocument();
    });

    it('renders elapsed time', () => {
      render(<BuildItem {...defaultProps} />);
      expect(screen.getByText('8.5s')).toBeInTheDocument();
    });
  });

  describe('status indicators', () => {
    it('shows warning count', () => {
      render(<BuildItem {...defaultProps} />);
      const warningIndicator = screen.getByTitle('7 warnings');
      expect(warningIndicator).toBeInTheDocument();
      expect(warningIndicator).toHaveTextContent('7');
    });

    it('shows error count', () => {
      render(<BuildItem {...defaultProps} />);
      const errorIndicator = screen.getByTitle('1 errors');
      expect(errorIndicator).toBeInTheDocument();
      expect(errorIndicator).toHaveTextContent('1');
    });

    it('hides warning indicator when zero', () => {
      const buildNoWarnings = { ...mockBuild, warnings: 0 };
      const { container } = render(<BuildItem {...defaultProps} build={buildNoWarnings} />);
      expect(container.querySelector('.indicator.warning')).not.toBeInTheDocument();
    });

    it('hides error indicator when zero', () => {
      const buildNoErrors = { ...mockBuild, errors: 0 };
      const { container } = render(<BuildItem {...defaultProps} build={buildNoErrors} />);
      expect(container.querySelector('.indicator.error')).not.toBeInTheDocument();
    });
  });

  describe('time formatting', () => {
    it('formats milliseconds correctly', () => {
      const build = { ...mockBuild, elapsedSeconds: 0.123 };
      render(<BuildItem {...defaultProps} build={build} />);
      expect(screen.getByText('123ms')).toBeInTheDocument();
    });

    it('formats seconds correctly', () => {
      const build = { ...mockBuild, elapsedSeconds: 45.2 };
      render(<BuildItem {...defaultProps} build={build} />);
      expect(screen.getByText('45.2s')).toBeInTheDocument();
    });

    it('formats minutes and seconds correctly', () => {
      const build = { ...mockBuild, elapsedSeconds: 125 };
      render(<BuildItem {...defaultProps} build={build} />);
      expect(screen.getByText('2m 5s')).toBeInTheDocument();
    });

    it('hides time for very short durations', () => {
      const build = { ...mockBuild, elapsedSeconds: 0.05, stages: [] };
      const { container } = render(<BuildItem {...defaultProps} build={build} />);
      expect(container.querySelector('.build-time')).not.toBeInTheDocument();
    });

    it('hides time for zero duration', () => {
      const build = { ...mockBuild, elapsedSeconds: 0, stages: [] };
      const { container } = render(<BuildItem {...defaultProps} build={build} />);
      expect(container.querySelector('.build-time')).not.toBeInTheDocument();
    });
  });

  describe('rich text stripping', () => {
    it('strips [bold] tags from stage names', () => {
      render(<BuildItem {...defaultProps} />);
      // Click to expand
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      // Should show 'init-build-context' not '[bold]init-build-context[/bold]'
      expect(screen.getByText('init-build-context')).toBeInTheDocument();
      expect(screen.queryByText('[bold]init-build-context[/bold]')).not.toBeInTheDocument();
    });

    it('strips quotes from stage names', () => {
      render(<BuildItem {...defaultProps} />);
      // Click to expand
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      // Should show 'compile App' not "compile 'App'"
      expect(screen.getByText('compile App')).toBeInTheDocument();
    });
  });

  describe('expand/collapse behavior', () => {
    it('starts collapsed', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      expect(container.querySelector('.build-item')).not.toHaveClass('expanded');
    });

    it('shows expand chevron when has stages', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      expect(container.querySelector('.build-chevron')).toBeInTheDocument();
    });

    it('hides expand chevron when no stages', () => {
      const buildNoStages = { ...mockBuild, stages: [] };
      const { container } = render(<BuildItem {...defaultProps} build={buildNoStages} />);
      expect(container.querySelector('.build-chevron')).not.toBeInTheDocument();
    });

    it('expands on click', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });

      fireEvent.click(header);

      expect(container.querySelector('.build-item')).toHaveClass('expanded');
    });

    it('collapses on second click', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });

      // Expand
      fireEvent.click(header);
      expect(container.querySelector('.build-item')).toHaveClass('expanded');

      // Collapse
      fireEvent.click(header);
      expect(container.querySelector('.build-item')).not.toHaveClass('expanded');
    });

    it('rotates chevron when expanded', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });

      fireEvent.click(header);

      expect(container.querySelector('.build-chevron')).toHaveClass('rotated');
    });

    it('shows stages list when expanded', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });

      fireEvent.click(header);

      expect(container.querySelector('.build-stages')).toBeInTheDocument();
    });

    it('hides stages list when collapsed', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      expect(container.querySelector('.build-stages')).not.toBeInTheDocument();
    });
  });

  describe('callbacks', () => {
    it('calls onSelectBuild when header clicked', () => {
      const onSelectBuild = vi.fn();
      render(<BuildItem {...defaultProps} onSelectBuild={onSelectBuild} />);

      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      expect(onSelectBuild).toHaveBeenCalledWith('default');
    });

    it('calls onSelectStage when stage clicked', () => {
      const onSelectStage = vi.fn();
      render(<BuildItem {...defaultProps} onSelectStage={onSelectStage} />);

      // Expand first
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      // Click on a stage
      const initStage = screen.getByText('init-build-context').closest('button');
      fireEvent.click(initStage!);

      // The callback receives the original stage name (with markup) as stored
      expect(onSelectStage).toHaveBeenCalledWith('default', '[bold]init-build-context[/bold]');
    });

    it('stage click stops propagation', () => {
      const onSelectBuild = vi.fn();
      const onSelectStage = vi.fn();
      render(<BuildItem {...defaultProps} onSelectBuild={onSelectBuild} onSelectStage={onSelectStage} />);

      // Expand first
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);
      onSelectBuild.mockClear(); // Clear the expand click

      // Click on a stage
      const initStage = screen.getByText('init-build-context').closest('button');
      fireEvent.click(initStage!);

      expect(onSelectStage).toHaveBeenCalled();
      // onSelectBuild shouldn't be called again due to stopPropagation
    });
  });

  describe('stage items', () => {
    it('renders all stages when expanded', () => {
      render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      expect(screen.getByText('init-build-context')).toBeInTheDocument();
      expect(screen.getByText('compile App')).toBeInTheDocument();
      expect(screen.getAllByText('picker').length).toBeGreaterThanOrEqual(1);
    });

    it('shows stage elapsed time in milliseconds', () => {
      render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      // 0.5s = 500ms
      expect(screen.getByText('500ms')).toBeInTheDocument();
    });

    it('shows stage warning count', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      // compile stage has 2 warnings, picker has 5
      const warningStats = container.querySelectorAll('.stat.warning');
      expect(warningStats.length).toBe(2);
    });

    it('shows stage error count', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      // picker stage has 1 error
      const errorStats = container.querySelectorAll('.stat.error');
      expect(errorStats.length).toBe(1);
    });

    it('marks selected stage', () => {
      // selectedStageName must match the original stage.name (with markup)
      const { container } = render(
        <BuildItem {...defaultProps} isSelected={true} selectedStageName="[bold]init-build-context[/bold]" />
      );
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      const stageItems = container.querySelectorAll('.stage-item');
      const initStage = Array.from(stageItems).find(item =>
        item.textContent?.includes('init-build-context')
      );

      expect(initStage).toHaveClass('selected');
    });
  });

  describe('CSS classes', () => {
    it('adds selected class when selected', () => {
      const { container } = render(<BuildItem {...defaultProps} isSelected={true} />);
      expect(container.querySelector('.build-item')).toHaveClass('selected');
    });

    it('adds expanded class when expanded', () => {
      const { container } = render(<BuildItem {...defaultProps} />);
      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      expect(container.querySelector('.build-item')).toHaveClass('expanded');
    });
  });

  describe('edge cases', () => {
    it('handles build with no stages', () => {
      const buildNoStages: Build = {
        ...mockBuild,
        stages: [],
      };
      render(<BuildItem {...defaultProps} build={buildNoStages} />);

      // Should render without error
      expect(screen.getByText('default')).toBeInTheDocument();
      // No expand chevron
      expect(screen.queryByRole('button', { name: /default/i })?.querySelector('.build-chevron')).toBeNull();
    });

    it('handles build with undefined stages', () => {
      const buildUndefinedStages: Build = {
        ...mockBuild,
        stages: undefined,
      };
      render(<BuildItem {...defaultProps} build={buildUndefinedStages} />);

      // Should render without error
      expect(screen.getByText('default')).toBeInTheDocument();
    });

    it('handles build status types', () => {
      const statuses: Build['status'][] = ['queued', 'building', 'success', 'warning', 'failed'];

      statuses.forEach(status => {
        const build = { ...mockBuild, status };
        const { container, unmount } = render(<BuildItem {...defaultProps} build={build} />);
        expect(container.querySelector('.build-status')).toBeInTheDocument();
        unmount();
      });
    });

    it('handles stage with zero warnings and errors', () => {
      const stageNoIssues: BuildStage[] = [
        {
          name: 'clean-stage',
          stageId: 'clean',
          elapsedSeconds: 1.0,
          status: 'success',
          infos: 5,
          warnings: 0,
          errors: 0,
          alerts: 0,
        },
      ];
      const buildClean = { ...mockBuild, stages: stageNoIssues };
      const { container } = render(<BuildItem {...defaultProps} build={buildClean} />);

      const header = screen.getByRole('button', { name: /default/i });
      fireEvent.click(header);

      expect(container.querySelector('.stage-item .stat.warning')).not.toBeInTheDocument();
      expect(container.querySelector('.stage-item .stat.error')).not.toBeInTheDocument();
    });
  });

  describe('getCurrentStage helper', () => {
    it('returns last stage name', () => {
      render(<BuildItem {...defaultProps} />);
      // Current stage shown in meta should be last stage
      expect(screen.getByText('picker')).toBeInTheDocument();
    });

    it('returns null for empty stages', () => {
      const buildEmpty = { ...mockBuild, stages: [] };
      const { container } = render(<BuildItem {...defaultProps} build={buildEmpty} />);
      // No stage should be shown in build meta
      expect(container.querySelector('.build-stage')).not.toBeInTheDocument();
    });
  });
});
