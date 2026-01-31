/**
 * BuildTargetItem component tests
 * Tests build target rendering, stage expansion, and interactions
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BuildTargetItem } from '../components/BuildTargetItem';
import type { Build, BuildTarget, BuildStage } from '../types/build';

// Test data - uses camelCase to match TypeScript interfaces
const mockTarget: BuildTarget = {
  name: 'default',
  entry: 'main.ato:App',
  root: '/project',
};

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
  target: mockTarget,
  build: mockBuild,
  isChecked: false,
  isSelected: false,
  isExpanded: false,
  selectedStageIds: [],
  onToggle: vi.fn(),
  onToggleExpand: vi.fn(),
  onToggleStage: vi.fn(),
};

describe('BuildTargetItem', () => {
  describe('basic rendering', () => {
    it('renders target name', () => {
      render(<BuildTargetItem {...defaultProps} />);
      expect(screen.getByText('default')).toBeInTheDocument();
    });

    it('renders entry when no build', () => {
      render(<BuildTargetItem {...defaultProps} build={undefined} />);
      expect(screen.getByText('main.ato:App')).toBeInTheDocument();
    });

    it('renders checkbox', () => {
      render(<BuildTargetItem {...defaultProps} />);
      expect(screen.getByRole('checkbox')).toBeInTheDocument();
    });

    it('checkbox reflects isChecked prop', () => {
      render(<BuildTargetItem {...defaultProps} isChecked={true} />);
      expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('renders status icon when build exists', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} />);
      expect(container.querySelector('.build-status')).toBeInTheDocument();
    });

    it('does not render status icon when no build', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} build={undefined} />);
      expect(container.querySelector('.build-status')).not.toBeInTheDocument();
    });
  });

  describe('build information', () => {
    it('shows current stage name', () => {
      render(<BuildTargetItem {...defaultProps} />);
      // Last stage is 'picker'
      expect(screen.getByText('picker')).toBeInTheDocument();
    });

    it('strips rich text formatting from stage names', () => {
      render(<BuildTargetItem {...defaultProps} />);
      // Should show 'init-build-context' not '[bold]init-build-context[/bold]'
      // The current stage shown is 'picker', but when expanded we'll see init-build-context
    });

    it('shows elapsed time', () => {
      render(<BuildTargetItem {...defaultProps} />);
      expect(screen.getByText('8.5s')).toBeInTheDocument();
    });

    it('shows warning count indicator', () => {
      render(<BuildTargetItem {...defaultProps} />);
      expect(screen.getByTitle('7 warnings')).toBeInTheDocument();
    });

    it('shows error count indicator', () => {
      render(<BuildTargetItem {...defaultProps} />);
      expect(screen.getByTitle('1 errors')).toBeInTheDocument();
    });

    it('hides warning indicator when zero warnings', () => {
      const buildNoWarnings = { ...mockBuild, warnings: 0 };
      const { container } = render(<BuildTargetItem {...defaultProps} build={buildNoWarnings} />);
      expect(container.querySelector('.indicator.warning')).not.toBeInTheDocument();
    });

    it('hides error indicator when zero errors', () => {
      const buildNoErrors = { ...mockBuild, errors: 0 };
      const { container } = render(<BuildTargetItem {...defaultProps} build={buildNoErrors} />);
      expect(container.querySelector('.indicator.error')).not.toBeInTheDocument();
    });
  });

  describe('time formatting', () => {
    it('formats seconds correctly', () => {
      const build = { ...mockBuild, elapsedSeconds: 45.2 };
      render(<BuildTargetItem {...defaultProps} build={build} />);
      expect(screen.getByText('45.2s')).toBeInTheDocument();
    });

    it('formats minutes and seconds correctly', () => {
      const build = { ...mockBuild, elapsedSeconds: 125 };
      render(<BuildTargetItem {...defaultProps} build={build} />);
      expect(screen.getByText('2m 5s')).toBeInTheDocument();
    });

    it('hides time for very short durations', () => {
      const build = { ...mockBuild, elapsedSeconds: 0.05 };
      const { container } = render(<BuildTargetItem {...defaultProps} build={build} />);
      expect(container.querySelector('.build-time')).not.toBeInTheDocument();
    });
  });

  describe('checkbox interaction', () => {
    it('calls onToggle when checkbox clicked', () => {
      const onToggle = vi.fn();
      render(<BuildTargetItem {...defaultProps} onToggle={onToggle} />);

      fireEvent.click(screen.getByRole('checkbox'));
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('stops propagation on checkbox click', () => {
      const onToggle = vi.fn();
      const onToggleExpand = vi.fn();
      render(<BuildTargetItem {...defaultProps} onToggle={onToggle} onToggleExpand={onToggleExpand} />);

      fireEvent.click(screen.getByRole('checkbox'));
      expect(onToggle).toHaveBeenCalled();
      expect(onToggleExpand).not.toHaveBeenCalled();
    });
  });

  describe('expand/collapse', () => {
    it('shows expand button when build has stages', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} />);
      expect(container.querySelector('.expand-button')).toBeInTheDocument();
    });

    it('hides expand button when no stages', () => {
      const buildNoStages = { ...mockBuild, stages: [] };
      const { container } = render(<BuildTargetItem {...defaultProps} build={buildNoStages} />);
      expect(container.querySelector('.expand-button')).not.toBeInTheDocument();
    });

    it('calls onToggleExpand when expand button clicked', () => {
      const onToggleExpand = vi.fn();
      const { container } = render(<BuildTargetItem {...defaultProps} onToggleExpand={onToggleExpand} />);

      const expandButton = container.querySelector('.expand-button');
      fireEvent.click(expandButton!);

      expect(onToggleExpand).toHaveBeenCalledTimes(1);
    });

    it('calls onToggleExpand when info area clicked', () => {
      const onToggleExpand = vi.fn();
      const { container } = render(<BuildTargetItem {...defaultProps} onToggleExpand={onToggleExpand} />);

      const infoArea = container.querySelector('.build-target-info');
      fireEvent.click(infoArea!);

      expect(onToggleExpand).toHaveBeenCalledTimes(1);
    });

    it('shows stages list when expanded', () => {
      render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      expect(screen.getByText('init-build-context')).toBeInTheDocument();
      expect(screen.getByText("compile App")).toBeInTheDocument();
      expect(screen.getAllByText('picker').length).toBeGreaterThanOrEqual(1);
    });

    it('hides stages list when collapsed', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} isExpanded={false} />);
      expect(container.querySelector('.build-stages')).not.toBeInTheDocument();
    });

    it('rotates chevron when expanded', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      expect(container.querySelector('.build-chevron')).toHaveClass('rotated');
    });
  });

  describe('stage items', () => {
    it('renders all stages when expanded', () => {
      render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      const stageButtons = screen.getAllByRole('button');
      // Should have expand button + 3 stages
      expect(stageButtons.length).toBeGreaterThanOrEqual(3);
    });

    it('shows stage status icon', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      const stageItems = container.querySelectorAll('.stage-item');
      stageItems.forEach((item) => {
        expect(item.querySelector('.status-icon')).toBeInTheDocument();
      });
    });

    it('shows stage elapsed time', () => {
      render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      expect(screen.getByText('0.5s')).toBeInTheDocument();
      expect(screen.getByText('2.3s')).toBeInTheDocument();
      expect(screen.getByText('5.7s')).toBeInTheDocument();
    });

    it('shows stage warning count when > 0', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      const warningStats = container.querySelectorAll('.stat.warning');
      expect(warningStats.length).toBe(2); // compile has 2, picker has 5
    });

    it('shows stage error count when > 0', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      const errorStats = container.querySelectorAll('.stat.error');
      expect(errorStats.length).toBe(1); // picker has 1
    });

    it('calls onToggleStage when stage clicked', () => {
      const onToggleStage = vi.fn();
      render(<BuildTargetItem {...defaultProps} isExpanded={true} onToggleStage={onToggleStage} />);

      // Click on the init stage
      const initStage = screen.getByText('init-build-context').closest('button');
      fireEvent.click(initStage!);

      expect(onToggleStage).toHaveBeenCalledWith('init');
    });

    it('marks stage as selected when in selectedStageIds', () => {
      const { container } = render(
        <BuildTargetItem {...defaultProps} isExpanded={true} selectedStageIds={['compile']} />
      );

      const stageItems = container.querySelectorAll('.stage-item');
      const compileStage = Array.from(stageItems).find((item) =>
        item.textContent?.includes('compile')
      );

      expect(compileStage).toHaveClass('selected');
    });
  });

  describe('CSS classes', () => {
    it('adds expanded class when expanded', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} isExpanded={true} />);
      expect(container.querySelector('.build-target-item')).toHaveClass('expanded');
    });

    it('adds selected class when selected', () => {
      const { container } = render(<BuildTargetItem {...defaultProps} isSelected={true} />);
      expect(container.querySelector('.build-target-item')).toHaveClass('selected');
    });
  });
});
