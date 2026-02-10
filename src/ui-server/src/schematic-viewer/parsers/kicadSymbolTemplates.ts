import type { SchematicSymbolFamily } from '../types/schematic';
import type { KicadSymbol } from '../types/symbol';
import { parseKicadSymbolLib } from './kicadSymParser';

const cache = new Map<string, KicadSymbol | null>();

function wrapLib(symbolBody: string): string {
  return `(kicad_symbol_lib
  (version 20211014)
  (generator "atopile_symbol_templates")
  ${symbolBody}
)`;
}

const TWO_PIN_TEMPLATES: Partial<Record<
  Exclude<SchematicSymbolFamily, 'connector' | 'testpoint'>,
  string
>> = {
  resistor: wrapLib(`(symbol "ATO_R"
    (property "Reference" "R" (at 0 2.2 0) (effects (font (size 1 1))))
    (property "Value" "R" (at 0 -2.2 0) (effects (font (size 1 1))))
    (rectangle
      (start -2.2 1.0)
      (end 2.2 -1.0)
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (pin passive line (at -5 0 0) (length 2.8) (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
    (pin passive line (at 5 0 180) (length 2.8) (name "~" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
  )`),
  capacitor: wrapLib(`(symbol "ATO_C"
    (property "Reference" "C" (at 0 2.2 0) (effects (font (size 1 1))))
    (property "Value" "C" (at 0 -2.2 0) (effects (font (size 1 1))))
    (polyline
      (pts (xy -0.9 -1.8) (xy -0.9 1.8))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 0.9 -1.8) (xy 0.9 1.8))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (pin passive line (at -5 0 0) (length 3.8) (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
    (pin passive line (at 5 0 180) (length 3.8) (name "~" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
  )`),
  capacitor_polarized: wrapLib(`(symbol "ATO_C_POL"
    (property "Reference" "C" (at 0 2.2 0) (effects (font (size 1 1))))
    (property "Value" "C_Polarized" (at 0 -2.2 0) (effects (font (size 1 1))))
    (polyline
      (pts (xy -0.9 -1.8) (xy -0.9 1.8))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 0.9 -1.8) (xy 0.9 1.8))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy -1.7 0.45) (xy -1.2 0.45))
      (stroke (width 0.18) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy -1.45 0.2) (xy -1.45 0.7))
      (stroke (width 0.18) (type default))
      (fill (type none))
    )
    (pin passive line (at -5 0 0) (length 3.8) (name "+" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
    (pin passive line (at 5 0 180) (length 3.8) (name "-" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
  )`),
  inductor: wrapLib(`(symbol "ATO_L"
    (property "Reference" "L" (at 0 2.2 0) (effects (font (size 1 1))))
    (property "Value" "L" (at 0 -2.2 0) (effects (font (size 1 1))))
    (polyline
      (pts
        (xy -2.4 0.0)
        (xy -2.0 0.9)
        (xy -1.6 0.0)
        (xy -1.2 0.9)
        (xy -0.8 0.0)
        (xy -0.4 0.9)
        (xy 0.0 0.0)
        (xy 0.4 0.9)
        (xy 0.8 0.0)
        (xy 1.2 0.9)
        (xy 1.6 0.0)
        (xy 2.0 0.9)
        (xy 2.4 0.0)
      )
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (pin passive line (at -5 0 0) (length 2.6) (name "~" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
    (pin passive line (at 5 0 180) (length 2.6) (name "~" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
  )`),
  diode: wrapLib(`(symbol "ATO_D"
    (property "Reference" "D" (at 0 2.2 0) (effects (font (size 1 1))))
    (property "Value" "D" (at 0 -2.2 0) (effects (font (size 1 1))))
    (polyline
      (pts (xy -2.2 -1.4) (xy -2.2 1.4) (xy 0.4 0.0) (xy -2.2 -1.4))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 0.9 -1.5) (xy 0.9 1.5))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (pin passive line (at -5 0 0) (length 2.8) (name "A" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
    (pin passive line (at 5 0 180) (length 3.1) (name "K" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
  )`),
  led: wrapLib(`(symbol "ATO_LED"
    (property "Reference" "D" (at 0 2.5 0) (effects (font (size 1 1))))
    (property "Value" "LED" (at 0 -2.5 0) (effects (font (size 1 1))))
    (polyline
      (pts (xy -2.2 -1.4) (xy -2.2 1.4) (xy 0.4 0.0) (xy -2.2 -1.4))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 0.9 -1.5) (xy 0.9 1.5))
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 1.0 0.8) (xy 2.0 1.8))
      (stroke (width 0.18) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 1.8 1.8) (xy 2.0 1.8) (xy 2.0 1.6))
      (stroke (width 0.18) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 0.6 0.2) (xy 1.6 1.2))
      (stroke (width 0.18) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy 1.4 1.2) (xy 1.6 1.2) (xy 1.6 1.0))
      (stroke (width 0.18) (type default))
      (fill (type none))
    )
    (pin passive line (at -5 0 0) (length 2.8) (name "A" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
    (pin passive line (at 5 0 180) (length 3.1) (name "K" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
  )`),
};

const TESTPOINT_TEMPLATE = wrapLib(`(symbol "ATO_TP"
  (property "Reference" "TP" (at 0 2.2 0) (effects (font (size 1 1))))
  (property "Value" "TestPoint" (at 0 -2.2 0) (effects (font (size 1 1))))
  (circle
    (center 0 0.35)
    (radius 1.1)
    (stroke (width 0.254) (type default))
    (fill (type none))
  )
  (polyline
    (pts (xy 0 -0.75) (xy 0 -2.0))
    (stroke (width 0.254) (type default))
    (fill (type none))
  )
  (pin passive line (at 0 -5 90) (length 3.0) (name "TP" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
)`);

function buildConnectorTemplate(pinCount: number): string {
  const count = Math.min(Math.max(pinCount, 2), 12);
  const width = Math.max(3.8, count * 0.95);
  const left = -width / 2;
  const right = width / 2;

  const circles = Array.from({ length: count }, (_, i) => {
    const x = left + ((i + 1) * width) / (count + 1);
    return `(circle
      (center ${x.toFixed(3)} 0.0)
      (radius 0.24)
      (stroke (width 0.15) (type default))
      (fill (type none))
    )`;
  }).join('\n');

  return wrapLib(`(symbol "ATO_CONN_${count}"
    (property "Reference" "J" (at 0 2.4 0) (effects (font (size 1 1))))
    (property "Value" "Conn_01x${count}" (at 0 -2.4 0) (effects (font (size 1 1))))
    (rectangle
      (start ${left.toFixed(3)} 1.1)
      (end ${right.toFixed(3)} -1.1)
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    ${circles}
    (circle
      (center ${(left + 0.45).toFixed(3)} 0.8)
      (radius 0.18)
      (stroke (width 0.15) (type default))
      (fill (type none))
    )
  )`);
}

function parseTemplate(cacheKey: string, source: string): KicadSymbol | null {
  if (cache.has(cacheKey)) return cache.get(cacheKey) ?? null;
  try {
    const lib = parseKicadSymbolLib(source);
    const symbol = lib.symbols[0] ?? null;
    cache.set(cacheKey, symbol);
    return symbol;
  } catch {
    cache.set(cacheKey, null);
    return null;
  }
}

export function getKicadTemplateSymbol(
  family: SchematicSymbolFamily,
  pinCount: number,
): KicadSymbol | null {
  if (family === 'connector') {
    const count = Math.min(Math.max(pinCount, 2), 12);
    return parseTemplate(`connector-${count}`, buildConnectorTemplate(count));
  }
  if (family === 'testpoint') {
    return parseTemplate('testpoint', TESTPOINT_TEMPLATE);
  }
  const source = TWO_PIN_TEMPLATES[family];
  if (!source) return null;
  return parseTemplate(family, source);
}
