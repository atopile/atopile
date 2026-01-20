/**
 * BOMPanel component tests
 * Tests BOM display, filtering, search, expansion, and interactions
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BOMPanel, mockBOM } from '../components/BOMPanel';
import type { BOMData } from '../types/build';

// Test data
const testSelection = {
  type: 'none' as const,
};

const testProjects = [
  {
    id: '/test/project',
    name: 'test-project',
    type: 'project' as const,
    path: '/test/project',
    builds: [
      { id: 'default', name: 'default', entry: 'main.ato:App', status: 'idle' as const, stages: [] },
    ],
  },
];

const testBOMData: BOMData = {
  version: '1.0',
  components: [
    {
      id: 'r1',
      lcsc: 'C25744',
      manufacturer: 'Yageo',
      mpn: 'RC0402FR-0710KL',
      type: 'resistor',
      value: '10kΩ',
      package: '0402',
      description: 'Thick Film Resistor',
      quantity: 2,
      unitCost: 0.002,
      stock: 50000,
      isBasic: true,
      isPreferred: false,
      source: 'picked',
      parameters: [
        { name: 'Resistance', value: '10', unit: 'kΩ' },
      ],
      usages: [
        { address: 'App.power_supply.r_top', designator: 'R1' },
        { address: 'App.power_supply.r_bot', designator: 'R2' },
      ],
    },
    {
      id: 'c1',
      lcsc: 'C1525',
      manufacturer: 'Samsung',
      mpn: 'CL05B104KO5NNNC',
      type: 'capacitor',
      value: '100nF',
      package: '0402',
      quantity: 3,
      unitCost: 0.003,
      stock: 0, // Out of stock
      source: 'picked',
      parameters: [],
      usages: [
        { address: 'App.mcu.decoupling[0]', designator: 'C1' },
        { address: 'App.mcu.decoupling[1]', designator: 'C2' },
        { address: 'App.sensor.decoupling', designator: 'C3' },
      ],
    },
    {
      id: 'u1',
      lcsc: 'C15742',
      manufacturer: 'STMicroelectronics',
      mpn: 'STM32F405RGT6',
      type: 'ic',
      value: 'STM32F405RGT6',
      package: 'LQFP-64',
      description: 'ARM Cortex-M4 MCU',
      quantity: 1,
      unitCost: 8.50,
      stock: 1200,
      source: 'specified',
      parameters: [],
      usages: [
        { address: 'App.mcu', designator: 'U1' },
      ],
    },
  ],
};

const defaultProps = {
  selection: testSelection,
  onSelectionChange: vi.fn(),
  projects: testProjects,
};

describe('BOMPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('mock data export', () => {
    it('exports valid mock BOM data', () => {
      expect(mockBOM).toBeDefined();
      expect(mockBOM.length).toBeGreaterThan(0);

      // Each mock component should have required fields
      mockBOM.forEach((component) => {
        expect(component.id).toBeDefined();
        expect(component.type).toBeDefined();
        expect(component.value).toBeDefined();
        expect(component.quantity).toBeGreaterThan(0);
      });
    });

    it('can render with mock data', () => {
      render(<BOMPanel {...defaultProps} />);
      // Should show first mock component value
      expect(screen.getByText('10kΩ ±1%')).toBeInTheDocument();
    });
  });

  describe('loading state', () => {
    it('shows loading spinner when isLoading is true', () => {
      render(<BOMPanel {...defaultProps} isLoading={true} />);
      expect(screen.getByText('Loading BOM...')).toBeInTheDocument();
    });

    it('shows loading spinner icon', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} isLoading={true} />);
      expect(container.querySelector('.loading-spinner')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message when error prop is set', () => {
      render(<BOMPanel {...defaultProps} error="Failed to load BOM" />);
      expect(screen.getByText('Failed to load BOM')).toBeInTheDocument();
    });

    it('shows retry button when onRefresh provided', () => {
      const onRefresh = vi.fn();
      render(<BOMPanel {...defaultProps} error="Error" onRefresh={onRefresh} />);
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('calls onRefresh when retry clicked', () => {
      const onRefresh = vi.fn();
      render(<BOMPanel {...defaultProps} error="Error" onRefresh={onRefresh} />);
      fireEvent.click(screen.getByText('Retry'));
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe('empty state', () => {
    it('shows empty state when no components match filter', () => {
      render(<BOMPanel {...defaultProps} bomData={{ version: '1.0', components: [] }} />);
      expect(screen.getByText('No components found')).toBeInTheDocument();
    });
  });

  describe('summary bar', () => {
    it('shows unique parts count', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('unique')).toBeInTheDocument();
    });

    it('shows total components count', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      // Total: 2 + 3 + 1 = 6
      expect(screen.getByText('6')).toBeInTheDocument();
      expect(screen.getByText('total')).toBeInTheDocument();
    });

    it('shows total cost', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      // Cost: 0.002*2 + 0.003*3 + 8.50*1 = 0.004 + 0.009 + 8.50 = $8.513
      expect(screen.getByText('$8.51')).toBeInTheDocument();
      expect(screen.getByText('cost')).toBeInTheDocument();
    });

    it('shows out of stock warning when applicable', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      // One component (c1) is out of stock
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('out of stock')).toBeInTheDocument();
    });
  });

  describe('component rendering', () => {
    it('renders all components', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByText('10kΩ')).toBeInTheDocument();
      expect(screen.getByText('100nF')).toBeInTheDocument();
      // STM32 appears as both value and MPN, so check it exists
      expect(screen.getAllByText('STM32F405RGT6').length).toBeGreaterThan(0);
    });

    it('shows MPN for each component', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByText('RC0402FR-0710KL')).toBeInTheDocument();
      expect(screen.getByText('CL05B104KO5NNNC')).toBeInTheDocument();
    });

    it('shows quantity for each component', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByText('×2')).toBeInTheDocument();
      expect(screen.getByText('×3')).toBeInTheDocument();
      expect(screen.getByText('×1')).toBeInTheDocument();
    });

    it('shows type badges', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(container.querySelector('.type-resistor')).toBeInTheDocument();
      expect(container.querySelector('.type-capacitor')).toBeInTheDocument();
      expect(container.querySelector('.type-ic')).toBeInTheDocument();
    });
  });

  describe('row expansion', () => {
    it('starts with rows collapsed', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(container.querySelector('.bom-row.expanded')).not.toBeInTheDocument();
    });

    it('expands row on click', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const rows = container.querySelectorAll('.bom-row');

      fireEvent.click(rows[0]);

      expect(rows[0]).toHaveClass('expanded');
    });

    it('collapses row on second click', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const rows = container.querySelectorAll('.bom-row');

      // Expand
      fireEvent.click(rows[0]);
      expect(rows[0]).toHaveClass('expanded');

      // Collapse
      fireEvent.click(rows[0]);
      expect(rows[0]).not.toHaveClass('expanded');
    });

    it('shows details when expanded', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const rows = container.querySelectorAll('.bom-row');

      // Rows are sorted by cost descending: IC ($8.50), capacitor ($0.009), resistor ($0.004)
      // Click on the first row (IC)
      fireEvent.click(rows[0]);

      // Should show manufacturer, package, etc.
      expect(screen.getByText('Manufacturer')).toBeInTheDocument();
      expect(screen.getByText('STMicroelectronics')).toBeInTheDocument();
      expect(screen.getByText('Package')).toBeInTheDocument();
    });

    it('shows LCSC link when expanded', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const rows = container.querySelectorAll('.bom-row');

      // Click on the first row (IC)
      fireEvent.click(rows[0]);

      expect(screen.getByText('C15742')).toBeInTheDocument();
    });

    it('shows source badge when expanded', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const rows = container.querySelectorAll('.bom-row');

      // Click on the resistor row (last due to sorting)
      fireEvent.click(rows[2]);

      expect(screen.getByText('Auto-picked')).toBeInTheDocument();
    });
  });

  describe('search functionality', () => {
    it('renders search input', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByPlaceholderText('Search value, MPN...')).toBeInTheDocument();
    });

    it('filters by value', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const searchInput = screen.getByPlaceholderText('Search value, MPN...');

      fireEvent.change(searchInput, { target: { value: '10k' } });

      expect(screen.getByText('10kΩ')).toBeInTheDocument();
      expect(screen.queryByText('100nF')).not.toBeInTheDocument();
    });

    it('filters by MPN', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const searchInput = screen.getByPlaceholderText('Search value, MPN...');

      fireEvent.change(searchInput, { target: { value: 'STM32' } });

      // STM32 appears as both value and MPN, so check it exists
      expect(screen.getAllByText('STM32F405RGT6').length).toBeGreaterThan(0);
      expect(screen.queryByText('10kΩ')).not.toBeInTheDocument();
    });

    it('filters by LCSC', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const searchInput = screen.getByPlaceholderText('Search value, MPN...');

      fireEvent.change(searchInput, { target: { value: 'C1525' } });

      expect(screen.getByText('100nF')).toBeInTheDocument();
      expect(screen.queryByText('10kΩ')).not.toBeInTheDocument();
    });

    it('filters by manufacturer', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const searchInput = screen.getByPlaceholderText('Search value, MPN...');

      fireEvent.change(searchInput, { target: { value: 'Yageo' } });

      expect(screen.getByText('10kΩ')).toBeInTheDocument();
      expect(screen.queryByText('100nF')).not.toBeInTheDocument();
    });

    it('shows empty state when no matches', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const searchInput = screen.getByPlaceholderText('Search value, MPN...');

      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      expect(screen.getByText('No components found')).toBeInTheDocument();
    });

    it('is case insensitive', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const searchInput = screen.getByPlaceholderText('Search value, MPN...');

      fireEvent.change(searchInput, { target: { value: 'stm32' } });

      // STM32 appears as both value and MPN, so check it exists
      expect(screen.getAllByText('STM32F405RGT6').length).toBeGreaterThan(0);
    });
  });

  describe('type filtering', () => {
    it('shows All filter button', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByTitle('All components')).toBeInTheDocument();
    });

    it('shows type filter buttons', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByTitle('Resistors')).toBeInTheDocument();
      expect(screen.getByTitle('Capacitors')).toBeInTheDocument();
      expect(screen.getByTitle('ICs / Chips')).toBeInTheDocument();
    });

    it('filters by resistor type', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);

      fireEvent.click(screen.getByTitle('Resistors'));

      expect(screen.getByText('10kΩ')).toBeInTheDocument();
      expect(screen.queryByText('100nF')).not.toBeInTheDocument();
      expect(screen.queryByText('STM32F405RGT6')).not.toBeInTheDocument();
    });

    it('filters by capacitor type', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);

      fireEvent.click(screen.getByTitle('Capacitors'));

      expect(screen.queryByText('10kΩ')).not.toBeInTheDocument();
      expect(screen.getByText('100nF')).toBeInTheDocument();
      expect(screen.queryByText('STM32F405RGT6')).not.toBeInTheDocument();
    });

    it('filters by IC type', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);

      fireEvent.click(screen.getByTitle('ICs / Chips'));

      expect(screen.queryByText('10kΩ')).not.toBeInTheDocument();
      expect(screen.queryByText('100nF')).not.toBeInTheDocument();
      // STM32 appears twice (value and MPN) so check it exists
      expect(screen.getAllByText('STM32F405RGT6').length).toBeGreaterThan(0);
    });

    it('shows all when All clicked after filtering', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);

      // Filter first
      fireEvent.click(screen.getByTitle('Resistors'));
      expect(screen.queryByText('100nF')).not.toBeInTheDocument();

      // Click All
      fireEvent.click(screen.getByTitle('All components'));
      expect(screen.getByText('100nF')).toBeInTheDocument();
    });

    it('marks active filter button', () => {
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);

      const resistorBtn = screen.getByTitle('Resistors');
      fireEvent.click(resistorBtn);

      expect(resistorBtn).toHaveClass('active');
    });
  });

  describe('stock warnings', () => {
    it('shows warning icon for out of stock items', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      // The capacitor (c1) is out of stock
      const warningIcons = container.querySelectorAll('.bom-stock-warning');
      expect(warningIcons.length).toBeGreaterThan(0);
    });

    it('shows out of stock text when expanded', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);

      // Find the capacitor row (out of stock) and expand it
      const rows = container.querySelectorAll('.bom-row');
      // Find the row with 100nF
      const capacitorRow = Array.from(rows).find(row =>
        row.textContent?.includes('100nF')
      );

      if (capacitorRow) {
        fireEvent.click(capacitorRow);
        expect(screen.getByText('Out of stock')).toBeInTheDocument();
      }
    });
  });

  describe('cost formatting', () => {
    it('formats small costs with 4 decimals', () => {
      // unitCost 0.002 for resistor
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const rows = container.querySelectorAll('.bom-row');

      // Rows are sorted by cost descending: IC ($8.50), capacitor ($0.009), resistor ($0.004)
      // The resistor is the last row (index 2)
      fireEvent.click(rows[2]);
      expect(screen.getByText('$0.0020')).toBeInTheDocument();
    });

    it('formats medium costs with 3 decimals', () => {
      // 0.003 * 3 = 0.009
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      // Total cost is shown in row header
      expect(container.textContent).toContain('$0.009');
    });

    it('formats large costs with 2 decimals', () => {
      // 8.50 * 1 = 8.50 (IC is first due to sort)
      render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      expect(screen.getByText('$8.50')).toBeInTheDocument();
    });
  });

  describe('go to source', () => {
    it('calls onGoToSource when usage clicked', async () => {
      const onGoToSource = vi.fn();
      const { container: container } = render(
        <BOMPanel {...defaultProps} bomData={testBOMData} onGoToSource={onGoToSource} />
      );

      // Expand first row
      const rows = container.querySelectorAll('.bom-row');
      fireEvent.click(rows[0]);

      // Click on a usage link
      const usageItems = container.querySelectorAll('.usage-single, .usage-instance');
      if (usageItems.length > 0) {
        fireEvent.click(usageItems[0]);
        expect(onGoToSource).toHaveBeenCalled();
      }
    });
  });

  describe('sorting', () => {
    it('sorts by cost descending by default', () => {
      const { container: container } = render(<BOMPanel {...defaultProps} bomData={testBOMData} />);
      const rows = container.querySelectorAll('.bom-row');

      // First row should be the most expensive (IC at $8.50)
      expect(rows[0].textContent).toContain('STM32F405RGT6');
    });
  });

  describe('props handling', () => {
    it('uses mock data when bomData not provided', () => {
      render(<BOMPanel {...defaultProps} />);
      // Should show mock data
      expect(screen.getByText('10kΩ ±1%')).toBeInTheDocument();
    });

    it('handles null bomData', () => {
      render(<BOMPanel {...defaultProps} bomData={null} />);
      // Should fall back to mock data
      expect(screen.getByText('10kΩ ±1%')).toBeInTheDocument();
    });

    it('handles empty components array', () => {
      render(<BOMPanel {...defaultProps} bomData={{ version: '1.0', components: [] }} />);
      expect(screen.getByText('No components found')).toBeInTheDocument();
    });
  });
});
