/**
 * StatusIcon component tests
 * Tests all build status icon rendering
 */

import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusIcon } from '../components/StatusIcon';

describe('StatusIcon', () => {
  describe('renders correct icons for each status', () => {
    it('renders queued status', () => {
      const { container } = render(<StatusIcon status="queued" />);
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // Queued shows a simple circle stroke
      const circle = svg?.querySelector('circle');
      expect(circle).toBeInTheDocument();
      expect(circle).toHaveAttribute('stroke', 'var(--text-muted)');
    });

    it('renders building status with spinning animation', () => {
      const { container } = render(<StatusIcon status="building" />);
      const span = container.querySelector('.status-icon');
      expect(span).toHaveClass('spinning');
      // Building shows dashed circle
      const circle = container.querySelector('circle');
      expect(circle).toHaveAttribute('stroke-dasharray', '20 10');
    });

    it('renders success status', () => {
      const { container } = render(<StatusIcon status="success" />);
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // Success shows a checkmark path
      const path = svg?.querySelector('path');
      expect(path).toBeInTheDocument();
      expect(path).toHaveAttribute('stroke', 'var(--success)');
    });

    it('renders warning status', () => {
      const { container } = render(<StatusIcon status="warning" />);
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // Warning shows exclamation mark
      const circle = svg?.querySelector('circle');
      expect(circle).toHaveAttribute('fill', 'var(--warning)');
    });

    it('renders failed status', () => {
      const { container } = render(<StatusIcon status="failed" />);
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // Failed shows X mark
      const circle = svg?.querySelector('circle');
      expect(circle).toHaveAttribute('fill', 'var(--error)');
    });
  });

  describe('size prop', () => {
    it('uses default size of 16', () => {
      const { container } = render(<StatusIcon status="success" />);
      const svg = container.querySelector('svg');
      expect(svg).toHaveStyle({ width: '16px', height: '16px' });
    });

    it('accepts custom size', () => {
      const { container } = render(<StatusIcon status="success" size={24} />);
      const svg = container.querySelector('svg');
      expect(svg).toHaveStyle({ width: '24px', height: '24px' });
    });
  });

  describe('stage status compatibility', () => {
    it('handles stage success status', () => {
      const { container } = render(<StatusIcon status="success" />);
      expect(container.querySelector('svg')).toBeInTheDocument();
    });

    it('handles stage warning status', () => {
      const { container } = render(<StatusIcon status="warning" />);
      expect(container.querySelector('svg')).toBeInTheDocument();
    });

    it('handles stage failed status', () => {
      const { container } = render(<StatusIcon status="failed" />);
      expect(container.querySelector('svg')).toBeInTheDocument();
    });
  });
});
