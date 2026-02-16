import { describe, expect, it } from 'vitest';
import { i2cTreeToGraph } from '../tree-viewer/utils/dataTransform';

describe('i2cTreeToGraph', () => {
  it('keeps target nodes even when no controller is detected on a bus', () => {
    const graph = i2cTreeToGraph({
      version: '1.0',
      buses: [
        {
          id: 'bus_0',
          frequency: '400kHz',
          controllers: [],
          targets: [
            {
              id: 'bus_0_tgt_0',
              name: 'imu.i2c',
              parent_module: 'imu',
              address: '0x68',
              address_resolved: true,
            },
          ],
        },
      ],
    });

    expect(graph.nodes).toHaveLength(1);
    expect(graph.nodes[0]).toMatchObject({
      type: 'target',
      label: 'imu.i2c',
      sublabel: '0x68',
    });
    expect(graph.edges).toHaveLength(0);
  });
});

