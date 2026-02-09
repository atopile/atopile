import { describe, expect, it } from 'vitest';
import { detectBuses, type NetForBus } from '../schematic-viewer/lib/busDetector';
import type { ThemeColors } from '../schematic-viewer/lib/theme';

const theme: ThemeColors = {
  bgPrimary: '#000000',
  bgSecondary: '#000000',
  bgTertiary: '#000000',
  bgHover: '#000000',
  textPrimary: '#ffffff',
  textSecondary: '#cccccc',
  textMuted: '#888888',
  borderColor: '#444444',
  borderSubtle: '#333333',
  accent: '#ff5500',
  bodyFill: '#111111',
  bodyBorder: '#555555',
  pinPower: '#f38ba8',
  pinGround: '#a6adc8',
  pinI2C: '#89b4fa',
  pinSPI: '#cba6f7',
  pinUART: '#a6e3a1',
  pinReset: '#fab387',
  pinSignal: '#94e2d5',
  netElectrical: '#7f8ea8',
  pinNC: '#585b70',
  pinCrystal: '#f9e2af',
  pinAnalog: '#fab387',
  busI2C: '#89b4fa',
  busSPI: '#cba6f7',
  busUART: '#a6e3a1',
};

function mkNet(
  netId: string,
  netName: string,
  allowBundle: boolean,
): NetForBus {
  return {
    netId,
    netName,
    netType: 'bus',
    allowBundle,
    worldPins: [
      { x: 0, y: 0, side: 'right', compId: 'left_item' },
      { x: 20, y: 0, side: 'left', compId: 'right_item' },
    ],
  };
}

describe('busDetector', () => {
  it('detects a bus group when multiple bundle-eligible bus nets share endpoints', () => {
    const groups = detectBuses(
      [
        mkNet('n1', 'qspi_DATA0', true),
        mkNet('n2', 'qspi_DATA1', true),
      ],
      theme,
    );

    expect(groups).toHaveLength(1);
    expect(groups[0].memberNetIds.size).toBe(2);
  });

  it('does not bundle nets marked as non-bundleable', () => {
    const groups = detectBuses(
      [
        mkNet('n1', 'qspi_DATA0', false),
        mkNet('n2', 'qspi_DATA1', false),
      ],
      theme,
    );

    expect(groups).toHaveLength(0);
  });
});
