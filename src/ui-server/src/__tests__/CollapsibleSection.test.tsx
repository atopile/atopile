/**
 * CollapsibleSection component tests
 * Tests collapsible behavior, badges, and resize functionality
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CollapsibleSection } from '../components/CollapsibleSection';

describe('CollapsibleSection', () => {
  const defaultProps = {
    id: 'test-section',
    title: 'Test Section',
    collapsed: false,
    onToggle: vi.fn(),
    children: <div data-testid="content">Content</div>,
  };

  describe('basic rendering', () => {
    it('renders title correctly', () => {
      render(<CollapsibleSection {...defaultProps} />);
      expect(screen.getByText('Test Section')).toBeInTheDocument();
    });

    it('renders children when expanded', () => {
      render(<CollapsibleSection {...defaultProps} collapsed={false} />);
      expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('hides children when collapsed', () => {
      render(<CollapsibleSection {...defaultProps} collapsed={true} />);
      expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    });

    it('shows down chevron when expanded', () => {
      const { container } = render(<CollapsibleSection {...defaultProps} collapsed={false} />);
      // ChevronDown is rendered when not collapsed
      expect(container.querySelector('.section-chevron')).toBeInTheDocument();
    });

    it('shows right chevron when collapsed', () => {
      const { container } = render(<CollapsibleSection {...defaultProps} collapsed={true} />);
      // ChevronRight is rendered when collapsed
      expect(container.querySelector('.section-chevron')).toBeInTheDocument();
      expect(container.querySelector('.collapsible-section')).toHaveClass('collapsed');
    });
  });

  describe('toggle functionality', () => {
    it('calls onToggle when title bar is clicked', () => {
      const onToggle = vi.fn();
      const { container } = render(
        <CollapsibleSection {...defaultProps} onToggle={onToggle} />
      );

      const titleBar = container.querySelector('.section-title-bar');
      fireEvent.click(titleBar!);

      expect(onToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe('badges', () => {
    it('renders count badge', () => {
      render(<CollapsibleSection {...defaultProps} badge={5} />);
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('renders filter badge with icon', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} badge="filtered" badgeType="filter" />
      );
      expect(screen.getByText('filtered')).toBeInTheDocument();
      expect(container.querySelector('.filter-badge')).toBeInTheDocument();
    });

    it('shows clear button on filter badge when onClearFilter provided', () => {
      const onClearFilter = vi.fn();
      const { container } = render(
        <CollapsibleSection
          {...defaultProps}
          badge="filtered"
          badgeType="filter"
          onClearFilter={onClearFilter}
        />
      );

      const clearButton = container.querySelector('.clear-filter-btn');
      expect(clearButton).toBeInTheDocument();
    });

    it('calls onClearFilter when clear button clicked', () => {
      const onClearFilter = vi.fn();
      const { container } = render(
        <CollapsibleSection
          {...defaultProps}
          badge="filtered"
          badgeType="filter"
          onClearFilter={onClearFilter}
        />
      );

      const clearButton = container.querySelector('.clear-filter-btn');
      fireEvent.click(clearButton!);

      expect(onClearFilter).toHaveBeenCalledTimes(1);
    });

    it('stops propagation when clear button clicked', () => {
      const onToggle = vi.fn();
      const onClearFilter = vi.fn();
      const { container } = render(
        <CollapsibleSection
          {...defaultProps}
          badge="filtered"
          badgeType="filter"
          onToggle={onToggle}
          onClearFilter={onClearFilter}
        />
      );

      const clearButton = container.querySelector('.clear-filter-btn');
      fireEvent.click(clearButton!);

      // onClearFilter should be called, but onToggle should NOT be called
      expect(onClearFilter).toHaveBeenCalledTimes(1);
      expect(onToggle).not.toHaveBeenCalled();
    });
  });

  describe('error and warning counts', () => {
    it('renders error count when provided', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} errorCount={3} />
      );
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(container.querySelector('.section-error-count')).toBeInTheDocument();
    });

    it('renders warning count when provided', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} warningCount={7} />
      );
      expect(screen.getByText('7')).toBeInTheDocument();
      expect(container.querySelector('.section-warning-count')).toBeInTheDocument();
    });

    it('does not render error count when zero', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} errorCount={0} />
      );
      expect(container.querySelector('.section-error-count')).not.toBeInTheDocument();
    });

    it('does not render warning count when zero', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} warningCount={0} />
      );
      expect(container.querySelector('.section-warning-count')).not.toBeInTheDocument();
    });

    it('renders both error and warning counts', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} errorCount={2} warningCount={5} />
      );
      expect(container.querySelector('.section-error-count')).toBeInTheDocument();
      expect(container.querySelector('.section-warning-count')).toBeInTheDocument();
    });
  });

  describe('height and resize', () => {
    it('applies manual height when provided and not collapsed', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} height={200} collapsed={false} />
      );
      const section = container.querySelector('.collapsible-section');
      expect(section).toHaveStyle({ height: '200px' });
    });

    it('does not apply height when collapsed', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} height={200} collapsed={true} />
      );
      const section = container.querySelector('.collapsible-section');
      expect(section).not.toHaveStyle({ height: '200px' });
    });

    it('shows resize handle when onResizeStart provided and not flexGrow', () => {
      const onResizeStart = vi.fn();
      const { container } = render(
        <CollapsibleSection {...defaultProps} onResizeStart={onResizeStart} />
      );
      expect(container.querySelector('.section-resize-handle')).toBeInTheDocument();
    });

    it('hides resize handle when flexGrow is true', () => {
      const onResizeStart = vi.fn();
      const { container } = render(
        <CollapsibleSection {...defaultProps} onResizeStart={onResizeStart} flexGrow={true} />
      );
      expect(container.querySelector('.section-resize-handle')).not.toBeInTheDocument();
    });

    it('calls onResizeStart on mousedown', () => {
      const onResizeStart = vi.fn();
      const { container } = render(
        <CollapsibleSection {...defaultProps} onResizeStart={onResizeStart} />
      );

      const handle = container.querySelector('.section-resize-handle');
      fireEvent.mouseDown(handle!);

      expect(onResizeStart).toHaveBeenCalledTimes(1);
    });
  });

  describe('CSS classes', () => {
    it('adds collapsed class when collapsed', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} collapsed={true} />
      );
      expect(container.querySelector('.collapsible-section')).toHaveClass('collapsed');
    });

    it('adds flex-grow class when flexGrow is true', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} flexGrow={true} />
      );
      expect(container.querySelector('.collapsible-section')).toHaveClass('flex-grow');
    });

    it('adds has-height class when has manual height', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} height={200} collapsed={false} />
      );
      expect(container.querySelector('.collapsible-section')).toHaveClass('has-height');
    });

    it('sets data-section-id attribute', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} id="my-section" />
      );
      expect(container.querySelector('[data-section-id="my-section"]')).toBeInTheDocument();
    });
  });
});
