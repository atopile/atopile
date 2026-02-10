import type { SchematicSymbolFamily } from '../types/schematic';

export interface SymbolRenderTuning {
  bodyOffsetX: number;
  bodyOffsetY: number;
  bodyRotationDeg: number;
  leadDelta: number;
}

const DEFAULT_TUNING: SymbolRenderTuning = {
  bodyOffsetX: 0,
  bodyOffsetY: 0,
  bodyRotationDeg: 0,
  leadDelta: 0,
};

export const SYMBOL_RENDER_TUNING: Record<
  Exclude<SchematicSymbolFamily, 'connector'>,
  SymbolRenderTuning
> = {
  resistor: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    leadDelta: 0,
  },
  capacitor: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 90,
    leadDelta: 0.35,
  },
  capacitor_polarized: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 90,
    leadDelta: -0.05,
  },
  inductor: {
    bodyOffsetX: 0,
    bodyOffsetY: 0.25,
    bodyRotationDeg: 0,
    leadDelta: -0.05,
  },
  diode: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    leadDelta: 0,
  },
  led: {
    bodyOffsetX: -1.4,
    bodyOffsetY: -0.45,
    bodyRotationDeg: 0,
    leadDelta: -0.05,
  },
  testpoint: {
    bodyOffsetX: -0.05,
    bodyOffsetY: -0.04,
    bodyRotationDeg: 0,
    leadDelta: -1,
  },
};

export function getSymbolRenderTuning(
  family: SchematicSymbolFamily | null,
): SymbolRenderTuning {
  if (!family || family === 'connector') return DEFAULT_TUNING;
  return SYMBOL_RENDER_TUNING[family];
}
