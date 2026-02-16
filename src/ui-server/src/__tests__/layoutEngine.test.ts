import { describe, expect, it } from 'vitest';
import type { TreeGraphData } from '../tree-viewer/types/tree';
import { computeTreeLayout } from '../tree-viewer/utils/layoutEngine';

function getX(data: ReturnType<typeof computeTreeLayout>, nodeId: string): number {
  const pos = data.positions.get(nodeId);
  if (!pos) {
    throw new Error(`Missing position for ${nodeId}`);
  }
  return pos.x;
}

describe('computeTreeLayout', () => {
  it('keeps upstream converters one level left of downstream converters', () => {
    const graph: TreeGraphData = {
      nodes: [
        { id: 'src', type: 'source', label: 'source' },
        { id: 'buck', type: 'converter', label: 'buck' },
        { id: 'ldo', type: 'converter', label: 'ldo' },
        { id: 'load', type: 'sink', label: 'load' },
      ],
      edges: [
        { id: 'src->buck', source: 'src', target: 'buck' },
        { id: 'buck->ldo', source: 'buck', target: 'ldo' },
        { id: 'ldo->load', source: 'ldo', target: 'load' },
      ],
    };

    const layout = computeTreeLayout(graph);

    expect(getX(layout, 'src')).toBeLessThan(getX(layout, 'buck'));
    expect(getX(layout, 'buck')).toBeLessThan(getX(layout, 'ldo'));
    expect(getX(layout, 'ldo')).toBeLessThan(getX(layout, 'load'));
  });

  it('aligns leaf sinks with sibling converters before downstream loads', () => {
    const graph: TreeGraphData = {
      nodes: [
        { id: 'src', type: 'source', label: 'source' },
        { id: 'buck', type: 'converter', label: 'buck' },
        { id: 'ldo', type: 'converter', label: 'ldo' },
        { id: 'mcu', type: 'sink', label: 'mcu' },
        { id: 'adc', type: 'sink', label: 'adc' },
      ],
      edges: [
        { id: 'src->buck', source: 'src', target: 'buck' },
        { id: 'buck->ldo', source: 'buck', target: 'ldo' },
        { id: 'buck->mcu', source: 'buck', target: 'mcu' },
        { id: 'ldo->adc', source: 'ldo', target: 'adc' },
      ],
    };

    const layout = computeTreeLayout(graph);
    const ldoX = getX(layout, 'ldo');
    const mcuX = getX(layout, 'mcu');
    const adcX = getX(layout, 'adc');

    expect(Math.abs(ldoX - mcuX)).toBeLessThan(1e-6);
    expect(ldoX).toBeLessThan(adcX);
  });

  it('handles cyclic graphs without exploding rank assignment', () => {
    const graph: TreeGraphData = {
      nodes: [
        { id: 'src', type: 'source', label: 'source' },
        { id: 'buck', type: 'converter', label: 'buck' },
        { id: 'ldo', type: 'converter', label: 'ldo' },
        { id: 'load', type: 'sink', label: 'load' },
      ],
      edges: [
        { id: 'src->buck', source: 'src', target: 'buck' },
        { id: 'buck->ldo', source: 'buck', target: 'ldo' },
        { id: 'ldo->buck', source: 'ldo', target: 'buck' },
        { id: 'ldo->load', source: 'ldo', target: 'load' },
      ],
    };

    const layout = computeTreeLayout(graph);

    expect(layout.positions.size).toBe(4);
    expect(getX(layout, 'src')).toBeLessThan(getX(layout, 'buck'));
    expect(getX(layout, 'src')).toBeLessThan(getX(layout, 'ldo'));
    expect(getX(layout, 'buck')).toBeLessThan(getX(layout, 'load'));
  });
});
