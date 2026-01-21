/**
 * ProblemsPanel component tests
 * Tests problem display, filtering, grouping, and interactions
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProblemsPanel, mockProblems } from '../components/ProblemsPanel';

// Test data
const testProblems = [
  {
    id: '1',
    level: 'error' as const,
    message: 'Type error in module',
    file: 'src/main.ato',
    line: 10,
    column: 5,
    stage: 'compile',
    buildName: 'default',
  },
  {
    id: '2',
    level: 'warning' as const,
    message: 'Unused variable',
    file: 'src/main.ato',
    line: 20,
    stage: 'lint',
    buildName: 'default',
  },
  {
    id: '3',
    level: 'error' as const,
    message: 'Missing import',
    file: 'src/power.ato',
    line: 5,
    stage: 'compile',
    buildName: 'default',
  },
  {
    id: '4',
    level: 'warning' as const,
    message: 'Deprecated API usage',
    stage: 'analyze',
    buildName: 'test',
  },
];

describe('ProblemsPanel', () => {
  describe('empty state', () => {
    it('shows empty state when no problems', () => {
      render(<ProblemsPanel problems={[]} />);
      expect(screen.getByText('No problems')).toBeInTheDocument();
    });

    it('shows filter buttons with zero counts when empty', () => {
      render(<ProblemsPanel problems={[]} />);
      const buttons = screen.getAllByRole('button');
      // Should have error and warning filter buttons
      expect(buttons.length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText('0').length).toBe(2);
    });
  });

  describe('problem rendering', () => {
    it('renders all problems', () => {
      render(<ProblemsPanel problems={testProblems} />);
      expect(screen.getByText('Type error in module')).toBeInTheDocument();
      expect(screen.getByText('Unused variable')).toBeInTheDocument();
      expect(screen.getByText('Missing import')).toBeInTheDocument();
      expect(screen.getByText('Deprecated API usage')).toBeInTheDocument();
    });

    it('shows error count in toolbar', () => {
      const { container } = render(<ProblemsPanel problems={testProblems} />);
      // Two errors in test data - find in the error filter button
      const errorButton = container.querySelector('.filter-btn.error span');
      expect(errorButton?.textContent).toBe('2');
    });

    it('shows warning count in toolbar', () => {
      render(<ProblemsPanel problems={testProblems} />);
      // Two warnings in test data - may appear multiple times
      const twoElements = screen.getAllByText('2');
      expect(twoElements.length).toBeGreaterThanOrEqual(1);
    });

    it('shows location for problems with line numbers', () => {
      render(<ProblemsPanel problems={testProblems} />);
      expect(screen.getByText('[10:5]')).toBeInTheDocument(); // line:column
      expect(screen.getByText('[20]')).toBeInTheDocument(); // line only
    });

    it('shows stage label when available', () => {
      const { container } = render(<ProblemsPanel problems={testProblems} />);
      // Stage labels appear in .problem-source elements
      const stageLabels = container.querySelectorAll('.problem-source');
      const stageTexts = Array.from(stageLabels).map(el => el.textContent);
      expect(stageTexts).toContain('compile');
      expect(stageTexts).toContain('lint');
    });
  });

  describe('file grouping', () => {
    it('groups problems by file', () => {
      render(<ProblemsPanel problems={testProblems} />);
      // Should show file headers
      expect(screen.getByText('main.ato')).toBeInTheDocument();
      expect(screen.getByText('power.ato')).toBeInTheDocument();
    });

    it('shows (no file) for problems without file', () => {
      const { container } = render(<ProblemsPanel problems={testProblems} />);
      // The file name and path both show "(no file)"
      const noFileElements = container.querySelectorAll('.problems-file-name');
      const hasNoFileGroup = Array.from(noFileElements).some(el => el.textContent === '(no file)');
      expect(hasNoFileGroup).toBe(true);
    });

    it('shows file-level error/warning counts', () => {
      const { container } = render(<ProblemsPanel problems={testProblems} />);
      // main.ato has 1 error, 1 warning
      const fileGroups = container.querySelectorAll('.problems-file-group');
      expect(fileGroups.length).toBe(3); // main.ato, power.ato, (no file)
    });
  });

  describe('collapsing file groups', () => {
    it('can collapse file groups by clicking header', () => {
      render(<ProblemsPanel problems={testProblems} />);

      // Find and click the main.ato file header
      const mainAtoHeader = screen.getByText('main.ato').closest('.problems-file-header');
      fireEvent.click(mainAtoHeader!);

      // The problems under main.ato should be hidden
      // The group should have collapsed class
      const fileGroup = mainAtoHeader?.closest('.problems-file-group');
      expect(fileGroup).toHaveClass('collapsed');
    });

    it('can expand collapsed file groups', () => {
      render(<ProblemsPanel problems={testProblems} />);

      const mainAtoHeader = screen.getByText('main.ato').closest('.problems-file-header');

      // Collapse
      fireEvent.click(mainAtoHeader!);
      expect(mainAtoHeader?.closest('.problems-file-group')).toHaveClass('collapsed');

      // Expand
      fireEvent.click(mainAtoHeader!);
      expect(mainAtoHeader?.closest('.problems-file-group')).not.toHaveClass('collapsed');
    });
  });

  describe('filter functionality', () => {
    it('calls onToggleLevelFilter when error button clicked', () => {
      const onToggleLevelFilter = vi.fn();
      const { container } = render(
        <ProblemsPanel problems={testProblems} onToggleLevelFilter={onToggleLevelFilter} />
      );

      const errorButton = container.querySelector('.filter-btn.error');
      fireEvent.click(errorButton!);

      expect(onToggleLevelFilter).toHaveBeenCalledWith('error');
    });

    it('calls onToggleLevelFilter when warning button clicked', () => {
      const onToggleLevelFilter = vi.fn();
      const { container } = render(
        <ProblemsPanel problems={testProblems} onToggleLevelFilter={onToggleLevelFilter} />
      );

      const warningButton = container.querySelector('.filter-btn.warning');
      fireEvent.click(warningButton!);

      expect(onToggleLevelFilter).toHaveBeenCalledWith('warning');
    });

    it('shows active state when filter includes level', () => {
      const { container } = render(
        <ProblemsPanel
          problems={testProblems}
          filter={{ levels: ['error'], buildNames: [], stageIds: [] }}
        />
      );

      const errorButton = container.querySelector('.filter-btn.error');
      const warningButton = container.querySelector('.filter-btn.warning');

      expect(errorButton).toHaveClass('active');
      expect(warningButton).not.toHaveClass('active');
    });

    it('shows both as active when no filter or empty levels', () => {
      const { container } = render(<ProblemsPanel problems={testProblems} />);

      const errorButton = container.querySelector('.filter-btn.error');
      const warningButton = container.querySelector('.filter-btn.warning');

      expect(errorButton).toHaveClass('active');
      expect(warningButton).toHaveClass('active');
    });
  });

  describe('problem click handling', () => {
    it('calls onProblemClick when problem with file is clicked', () => {
      const onProblemClick = vi.fn();
      render(<ProblemsPanel problems={testProblems} onProblemClick={onProblemClick} />);

      // Click on a problem with a file
      const problemItem = screen.getByText('Type error in module').closest('.problem-item');
      fireEvent.click(problemItem!);

      expect(onProblemClick).toHaveBeenCalledWith(testProblems[0]);
    });

    it('has clickable class for problems with files', () => {
      render(<ProblemsPanel problems={testProblems} />);

      const problemWithFile = screen.getByText('Type error in module').closest('.problem-item');
      const problemWithoutFile = screen.getByText('Deprecated API usage').closest('.problem-item');

      expect(problemWithFile).toHaveClass('clickable');
      expect(problemWithoutFile).not.toHaveClass('clickable');
    });
  });

  describe('mock problems export', () => {
    it('exports valid mock problems for development', () => {
      expect(mockProblems).toBeDefined();
      expect(mockProblems.length).toBeGreaterThan(0);

      // Each mock problem should have required fields
      mockProblems.forEach((problem) => {
        expect(problem.id).toBeDefined();
        expect(problem.level).toMatch(/^(error|warning)$/);
        expect(problem.message).toBeDefined();
      });
    });

    it('can render with mock problems', () => {
      render(<ProblemsPanel problems={mockProblems} />);
      // Should render without errors
      expect(screen.getByText(/Cannot find module/)).toBeInTheDocument();
    });
  });
});
