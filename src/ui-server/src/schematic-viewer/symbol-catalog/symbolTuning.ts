import type { SchematicSymbolFamily } from '../types/schematic';

export interface SymbolRenderTuning {
  bodyOffsetX: number;
  bodyOffsetY: number;
  bodyRotationDeg: number;
  bodyScaleX?: number;
  bodyScaleY?: number;
  leadDelta: number;
}

const DEFAULT_TUNING: SymbolRenderTuning = {
  bodyOffsetX: 0,
  bodyOffsetY: 0,
  bodyRotationDeg: 0,
  bodyScaleX: 1,
  bodyScaleY: 1,
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
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: 0,
  },
  capacitor: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 90,
    bodyScaleX: 2.01,
    bodyScaleY: 2.08,
    leadDelta: 0.05,
  },
  capacitor_polarized: {
    bodyOffsetX: -0.9,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 90,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: -0.1,
  },
  inductor: {
    bodyOffsetX: 0,
    bodyOffsetY: 0.25,
    bodyRotationDeg: 0,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: -0.05,
  },
  diode: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  led: {
    bodyOffsetX: -1.55,
    bodyOffsetY: -0.45,
    bodyRotationDeg: 0,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: 0,
  },
  transistor_npn: {
    bodyOffsetX: 1.2,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  transistor_pnp: {
    bodyOffsetX: 1.2,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  mosfet_n: {
    bodyOffsetX: 1.4,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  mosfet_p: {
    bodyOffsetX: 1.4,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  testpoint: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.04,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: -1.15,
  },
};

export function getSymbolRenderTuning(
  family: SchematicSymbolFamily | null,
): SymbolRenderTuning {
  if (!family || family === 'connector') return DEFAULT_TUNING;
  return SYMBOL_RENDER_TUNING[family];
}
