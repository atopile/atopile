/**
 * KiCad .kicad_sym parser.
 *
 * Supports the symbol primitives we render in the schematic viewer:
 * - symbol/property/pin
 * - rectangle/circle/polyline/arc
 */

import type {
  KicadArc,
  KicadCircle,
  KicadPin,
  KicadPolyline,
  KicadRect,
  KicadSymbol,
  KicadSymbolLib,
  PinCategory,
  PinElectricalType,
  PinGraphicStyle,
  PinSide,
} from '../types/symbol';

type SExpr = string | SExpr[];

function tokenize(input: string): string[] {
  const tokens: string[] = [];
  let i = 0;
  while (i < input.length) {
    const ch = input[i];

    if (/\s/.test(ch)) {
      i += 1;
      continue;
    }
    if (ch === '(' || ch === ')') {
      tokens.push(ch);
      i += 1;
      continue;
    }
    if (ch === '"') {
      i += 1;
      let out = '';
      while (i < input.length) {
        const c = input[i];
        if (c === '\\' && i + 1 < input.length) {
          out += input[i + 1];
          i += 2;
          continue;
        }
        if (c === '"') {
          i += 1;
          break;
        }
        out += c;
        i += 1;
      }
      tokens.push(out);
      continue;
    }

    let j = i;
    while (j < input.length && !/\s/.test(input[j]) && input[j] !== '(' && input[j] !== ')') {
      j += 1;
    }
    tokens.push(input.slice(i, j));
    i = j;
  }
  return tokens;
}

function parseSExpr(tokens: string[]): SExpr[] {
  let i = 0;

  function parseNode(): SExpr {
    if (i >= tokens.length) throw new Error('Unexpected end of S-expression');
    const tok = tokens[i++];
    if (tok === '(') {
      const list: SExpr[] = [];
      while (i < tokens.length && tokens[i] !== ')') {
        list.push(parseNode());
      }
      if (tokens[i] !== ')') throw new Error('Unterminated S-expression list');
      i += 1; // skip ')'
      return list;
    }
    if (tok === ')') throw new Error('Unexpected )');
    return tok;
  }

  const out: SExpr[] = [];
  while (i < tokens.length) out.push(parseNode());
  return out;
}

function asList(node: SExpr): SExpr[] | null {
  return Array.isArray(node) ? node : null;
}

function asAtom(node: SExpr | undefined): string | null {
  return typeof node === 'string' ? node : null;
}

function listTag(list: SExpr[]): string | null {
  return asAtom(list[0]);
}

function parseNum(node: SExpr | undefined, fallback = 0): number {
  const raw = asAtom(node);
  if (!raw) return fallback;
  const n = Number.parseFloat(raw);
  return Number.isFinite(n) ? n : fallback;
}

function findChild(list: SExpr[], tag: string): SExpr[] | null {
  for (let i = 1; i < list.length; i += 1) {
    const child = asList(list[i]);
    if (child && listTag(child) === tag) return child;
  }
  return null;
}

function hasAtomDeep(node: SExpr, atom: string): boolean {
  if (typeof node === 'string') return node === atom;
  return node.some((child) => hasAtomDeep(child, atom));
}

function sideFromAngle(angle: number): PinSide {
  const a = ((Math.round(angle) % 360) + 360) % 360;
  if (a === 180) return 'left';
  if (a === 0) return 'right';
  if (a === 90) return 'top';
  return 'bottom';
}

function classifyPinCategory(name: string, electricalType: PinElectricalType): PinCategory {
  const n = name.toLowerCase();
  if (n === 'gnd' || n === 'vss' || n === 'lv' || n === '0v') return 'ground';
  if (n === 'vcc' || n === 'vdd' || n === 'hv' || n === 'vin' || n === 'vbat') return 'power';
  if (n.includes('scl') || n.includes('sda') || n.includes('i2c')) return 'i2c';
  if (n.includes('mosi') || n.includes('miso') || n.includes('sclk') || n.includes('spi')) return 'spi';
  if (n === 'tx' || n === 'rx' || n.includes('uart')) return 'uart';
  if (n.includes('rst') || n.includes('reset')) return 'reset';
  if (electricalType === 'power_in' || electricalType === 'power_out') return 'power';
  if (electricalType === 'input') return 'input';
  if (electricalType === 'output') return 'output';
  if (electricalType === 'bidirectional') return 'bidirectional';
  if (electricalType === 'no_connect') return 'nc';
  return 'signal';
}

function parseFillType(list: SExpr[]): string {
  const fill = findChild(list, 'fill');
  const type = fill ? findChild(fill, 'type') : null;
  return (type && asAtom(type[1])) || 'none';
}

function parsePin(list: SExpr[]): KicadPin {
  const electricalType = (asAtom(list[1]) || 'passive') as PinElectricalType;
  const graphicStyle = (asAtom(list[2]) || 'line') as PinGraphicStyle;

  const at = findChild(list, 'at');
  const x = at ? parseNum(at[1]) : 0;
  const y = at ? parseNum(at[2]) : 0;
  const angle = at ? parseNum(at[3]) : 0;

  const lengthNode = findChild(list, 'length');
  const length = lengthNode ? parseNum(lengthNode[1], 2.54) : 2.54;

  const nameNode = findChild(list, 'name');
  const name = (nameNode && asAtom(nameNode[1])) || '';
  const nameHidden = !!(nameNode && hasAtomDeep(nameNode, 'hide'));

  const numberNode = findChild(list, 'number');
  const number = (numberNode && asAtom(numberNode[1])) || '';
  const numberHidden = !!(numberNode && hasAtomDeep(numberNode, 'hide'));

  const side = sideFromAngle(angle);
  const rad = (angle * Math.PI) / 180;
  const bodyX = x - Math.cos(rad) * length;
  const bodyY = y - Math.sin(rad) * length;

  return {
    name,
    number,
    electricalType,
    graphicStyle,
    x,
    y,
    angle,
    length,
    nameHidden,
    numberHidden,
    side,
    category: classifyPinCategory(name, electricalType),
    bodyX,
    bodyY,
  };
}

function parseRectangle(list: SExpr[]): KicadRect {
  const start = findChild(list, 'start');
  const end = findChild(list, 'end');
  return {
    startX: start ? parseNum(start[1]) : 0,
    startY: start ? parseNum(start[2]) : 0,
    endX: end ? parseNum(end[1]) : 0,
    endY: end ? parseNum(end[2]) : 0,
    fillType: parseFillType(list),
  };
}

function parseCircle(list: SExpr[]): KicadCircle {
  const center = findChild(list, 'center');
  const radiusNode = findChild(list, 'radius');
  return {
    centerX: center ? parseNum(center[1]) : 0,
    centerY: center ? parseNum(center[2]) : 0,
    radius: radiusNode ? parseNum(radiusNode[1]) : 0,
    fillType: parseFillType(list),
  };
}

function parsePolyline(list: SExpr[]): KicadPolyline {
  const ptsNode = findChild(list, 'pts');
  const points: { x: number; y: number }[] = [];
  if (ptsNode) {
    for (let i = 1; i < ptsNode.length; i += 1) {
      const xy = asList(ptsNode[i]);
      if (!xy || listTag(xy) !== 'xy') continue;
      points.push({ x: parseNum(xy[1]), y: parseNum(xy[2]) });
    }
  }
  return { points, fillType: parseFillType(list) };
}

function parseArc(list: SExpr[]): KicadArc {
  const start = findChild(list, 'start');
  const mid = findChild(list, 'mid');
  const end = findChild(list, 'end');
  return {
    startX: start ? parseNum(start[1]) : 0,
    startY: start ? parseNum(start[2]) : 0,
    midX: mid ? parseNum(mid[1]) : 0,
    midY: mid ? parseNum(mid[2]) : 0,
    endX: end ? parseNum(end[1]) : 0,
    endY: end ? parseNum(end[2]) : 0,
    fillType: parseFillType(list),
  };
}

function computeBounds(symbol: {
  pins: KicadPin[];
  rectangles: KicadRect[];
  circles: KicadCircle[];
  polylines: KicadPolyline[];
  arcs: KicadArc[];
}): Pick<KicadSymbol, 'bodyBounds' | 'totalBounds'> {
  const bodyPoints: Array<[number, number]> = [];
  const totalPoints: Array<[number, number]> = [];

  for (const rect of symbol.rectangles) {
    const pts: Array<[number, number]> = [
      [rect.startX, rect.startY],
      [rect.endX, rect.endY],
      [rect.startX, rect.endY],
      [rect.endX, rect.startY],
    ];
    bodyPoints.push(...pts);
    totalPoints.push(...pts);
  }
  for (const circle of symbol.circles) {
    const pts: Array<[number, number]> = [
      [circle.centerX - circle.radius, circle.centerY],
      [circle.centerX + circle.radius, circle.centerY],
      [circle.centerX, circle.centerY - circle.radius],
      [circle.centerX, circle.centerY + circle.radius],
    ];
    bodyPoints.push(...pts);
    totalPoints.push(...pts);
  }
  for (const line of symbol.polylines) {
    for (const p of line.points) {
      bodyPoints.push([p.x, p.y]);
      totalPoints.push([p.x, p.y]);
    }
  }
  for (const arc of symbol.arcs) {
    const pts: Array<[number, number]> = [
      [arc.startX, arc.startY],
      [arc.midX, arc.midY],
      [arc.endX, arc.endY],
    ];
    bodyPoints.push(...pts);
    totalPoints.push(...pts);
  }

  for (const pin of symbol.pins) {
    totalPoints.push([pin.x, pin.y], [pin.bodyX, pin.bodyY]);
  }

  if (bodyPoints.length === 0 && symbol.pins.length > 0) {
    for (const pin of symbol.pins) bodyPoints.push([pin.bodyX, pin.bodyY]);
  }
  if (bodyPoints.length === 0) bodyPoints.push([0, 0]);
  if (totalPoints.length === 0) totalPoints.push(...bodyPoints);

  const minBodyX = Math.min(...bodyPoints.map((p) => p[0]));
  const maxBodyX = Math.max(...bodyPoints.map((p) => p[0]));
  const minBodyY = Math.min(...bodyPoints.map((p) => p[1]));
  const maxBodyY = Math.max(...bodyPoints.map((p) => p[1]));

  const minTotalX = Math.min(...totalPoints.map((p) => p[0]));
  const maxTotalX = Math.max(...totalPoints.map((p) => p[0]));
  const minTotalY = Math.min(...totalPoints.map((p) => p[1]));
  const maxTotalY = Math.max(...totalPoints.map((p) => p[1]));

  return {
    bodyBounds: {
      minX: minBodyX,
      minY: minBodyY,
      maxX: maxBodyX,
      maxY: maxBodyY,
      width: maxBodyX - minBodyX,
      height: maxBodyY - minBodyY,
    },
    totalBounds: {
      minX: minTotalX,
      minY: minTotalY,
      maxX: maxTotalX,
      maxY: maxTotalY,
    },
  };
}

function parseSymbolNode(node: SExpr[]): KicadSymbol {
  const name = asAtom(node[1]) || 'Unnamed';

  let reference = '';
  let value = '';
  let footprint = '';
  let datasheet = '';

  const pins: KicadPin[] = [];
  const rectangles: KicadRect[] = [];
  const circles: KicadCircle[] = [];
  const polylines: KicadPolyline[] = [];
  const arcs: KicadArc[] = [];

  const walk = (child: SExpr): void => {
    const list = asList(child);
    if (!list) return;
    const tag = listTag(list);
    if (!tag) return;

    if (tag === 'symbol') {
      for (let i = 2; i < list.length; i += 1) walk(list[i]);
      return;
    }
    if (tag === 'property') {
      const key = asAtom(list[1]) || '';
      const val = asAtom(list[2]) || '';
      if (key === 'Reference' && !reference) reference = val;
      if (key === 'Value' && !value) value = val;
      if (key === 'Footprint' && !footprint) footprint = val;
      if (key === 'Datasheet' && !datasheet) datasheet = val;
      return;
    }
    if (tag === 'pin') {
      pins.push(parsePin(list));
      return;
    }
    if (tag === 'rectangle') {
      rectangles.push(parseRectangle(list));
      return;
    }
    if (tag === 'circle') {
      circles.push(parseCircle(list));
      return;
    }
    if (tag === 'polyline') {
      polylines.push(parsePolyline(list));
      return;
    }
    if (tag === 'arc') {
      arcs.push(parseArc(list));
      return;
    }

    for (let i = 1; i < list.length; i += 1) walk(list[i]);
  };

  for (let i = 2; i < node.length; i += 1) walk(node[i]);

  const base = {
    name,
    reference,
    value,
    footprint,
    datasheet,
    pins,
    rectangles,
    circles,
    polylines,
    arcs,
  };
  return { ...base, ...computeBounds(base) };
}

export function parseKicadSymbolLib(content: string): KicadSymbolLib {
  const ast = parseSExpr(tokenize(content));
  const root = ast
    .map(asList)
    .find((list): list is SExpr[] =>
      !!list && (listTag(list) === 'kicad_symbol_lib' || listTag(list) === 'kicad_sym')
    );

  if (!root) throw new Error('Invalid .kicad_sym: missing root kicad_symbol_lib node');

  let version = '';
  let generator = '';
  const symbols: KicadSymbol[] = [];

  for (let i = 1; i < root.length; i += 1) {
    const child = asList(root[i]);
    if (!child) continue;
    const tag = listTag(child);
    if (tag === 'version') {
      version = asAtom(child[1]) || version;
    } else if (tag === 'generator') {
      generator = asAtom(child[1]) || generator;
    } else if (tag === 'symbol') {
      symbols.push(parseSymbolNode(child));
    }
  }

  return {
    version,
    generator,
    symbols,
  };
}
