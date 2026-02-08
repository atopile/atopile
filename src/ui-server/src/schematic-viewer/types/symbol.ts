/** Parsed KiCad symbol data */

export type PinElectricalType =
  | 'input' | 'output' | 'bidirectional' | 'tri_state'
  | 'passive' | 'free' | 'unspecified'
  | 'power_in' | 'power_out'
  | 'open_collector' | 'open_emitter' | 'no_connect';

export type PinGraphicStyle =
  | 'line' | 'inverted' | 'clock' | 'inverted_clock'
  | 'input_low' | 'clock_low' | 'output_low'
  | 'edge_clock_high' | 'non_logic';

export type PinSide = 'left' | 'right' | 'top' | 'bottom';

export type PinCategory =
  | 'power' | 'ground' | 'input' | 'output' | 'bidirectional'
  | 'passive' | 'nc' | 'i2c' | 'spi' | 'uart' | 'reset' | 'signal'
  | 'crystal' | 'control' | 'analog';

export interface KicadPin {
  name: string;
  number: string;
  electricalType: PinElectricalType;
  graphicStyle: PinGraphicStyle;
  x: number;
  y: number;
  angle: number;         // degrees: 0=right, 90=up, 180=left, 270=down
  length: number;
  nameHidden: boolean;
  numberHidden: boolean;
  // Computed
  side: PinSide;
  category: PinCategory;
  bodyX: number;         // where the pin meets the body
  bodyY: number;
}

export interface KicadRect {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  fillType: string;
}

export interface KicadCircle {
  centerX: number;
  centerY: number;
  radius: number;
  fillType: string;
}

export interface KicadPolyline {
  points: { x: number; y: number }[];
  fillType: string;
}

export interface KicadArc {
  startX: number;
  startY: number;
  midX: number;
  midY: number;
  endX: number;
  endY: number;
  fillType: string;
}

export interface KicadSymbol {
  name: string;
  reference: string;
  value: string;
  footprint: string;
  datasheet: string;
  pins: KicadPin[];
  rectangles: KicadRect[];
  circles: KicadCircle[];
  polylines: KicadPolyline[];
  arcs: KicadArc[];
  // Computed bounding box of the body
  bodyBounds: {
    minX: number; minY: number;
    maxX: number; maxY: number;
    width: number; height: number;
  };
  // Overall bounds including pins
  totalBounds: {
    minX: number; minY: number;
    maxX: number; maxY: number;
  };
}

export interface KicadSymbolLib {
  version: string;
  generator: string;
  symbols: KicadSymbol[];
}
