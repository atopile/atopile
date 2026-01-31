/**
 * ProblemsPanel component tests
 * Tests problem display, grouping, sorting, and interactions
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProblemsPanel } from '../components/ProblemsPanel';

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
  });

  describe('problem rendering', () => {
    it('renders all problems', () => {
      render(<ProblemsPanel problems={testProblems} />);
      expect(screen.getByText('Type error in module')).toBeInTheDocument();
      expect(screen.getByText('Unused variable')).toBeInTheDocument();
      expect(screen.getByText('Missing import')).toBeInTheDocument();
      expect(screen.getByText('Deprecated API usage')).toBeInTheDocument();
    });

    it('shows error count in summary', () => {
      const { container } = render(<ProblemsPanel problems={testProblems} />);
      // Error count is shown as just the number with an icon
      const errorCount = container.querySelector('.problems-count.error');
      expect(errorCount?.textContent).toBe('2');
    });

    it('shows warning count in summary', () => {
      const { container } = render(<ProblemsPanel problems={testProblems} />);
      // Warning count is shown as just the number with an icon
      const warningCount = container.querySelector('.problems-count.warning');
      expect(warningCount?.textContent).toBe('2');
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

  describe('error sorting', () => {
    it('sorts errors before warnings within each file group', () => {
      // Create problems where warning comes first in input
      const mixedProblems = [
        {
          id: 'w1',
          level: 'warning' as const,
          message: 'Warning first',
          file: 'test.ato',
          line: 1,
        },
        {
          id: 'e1',
          level: 'error' as const,
          message: 'Error second',
          file: 'test.ato',
          line: 2,
        },
      ];

      const { container } = render(<ProblemsPanel problems={mixedProblems} />);

      // Get all problem items in order
      const items = container.querySelectorAll('.problem-item');
      expect(items.length).toBe(2);

      // First item should be error (sorted to top)
      expect(items[0]).toHaveClass('error');
      expect(items[0].textContent).toContain('Error second');

      // Second item should be warning
      expect(items[1]).toHaveClass('warning');
      expect(items[1].textContent).toContain('Warning first');
    });
  });

  describe('collapsing file groups', () => {
    it('can collapse file groups by clicking header', () => {
      render(<ProblemsPanel problems={testProblems} />);

      // Find and click the main.ato file header
      const mainAtoHeader = screen.getByText('main.ato').closest('.problems-file-header');
      fireEvent.click(mainAtoHeader!);

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
});
