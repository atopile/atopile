import { describe, expect, it } from 'vitest';
import { parseKicadSymbolLib } from '../schematic-viewer/parsers/kicadSymParser';
import {
  getCanonicalKicadSymbol,
  getCanonicalSymbolCatalogMetadata,
} from '../schematic-viewer/symbol-catalog/canonicalSymbolCatalog';

const SIMPLE_LIB = `(kicad_symbol_lib
  (version 20211014)
  (generator "unit_test")
  (symbol "TestSymbol"
    (property "Reference" "R" (at 0 2 0) (effects (font (size 1 1))))
    (property "Value" "10k" (at 0 -2 0) (effects (font (size 1 1))))
    (rectangle
      (start -2 1)
      (end 2 -1)
      (stroke (width 0.254) (type default))
      (fill (type none))
    )
    (polyline
      (pts (xy -1.5 0) (xy 1.5 0))
      (stroke (width 0.2) (type default))
      (fill (type none))
    )
    (circle
      (center 0 0)
      (radius 0.4)
      (stroke (width 0.2) (type default))
      (fill (type none))
    )
    (arc
      (start -1 -1)
      (mid 0 -1.5)
      (end 1 -1)
      (stroke (width 0.2) (type default))
      (fill (type none))
    )
    (pin passive line (at -5 0 0) (length 3) (name "A" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))
    (pin passive line (at 5 0 180) (length 3) (name "B" (effects (font (size 1 1)))) (number "2" (effects (font (size 1 1)))))
  )
)`;

describe('kicadSymParser', () => {
  it('parses symbol primitives and pins from .kicad_sym text', () => {
    const lib = parseKicadSymbolLib(SIMPLE_LIB);
    expect(lib.version).toBe('20211014');
    expect(lib.generator).toBe('unit_test');
    expect(lib.symbols).toHaveLength(1);

    const [symbol] = lib.symbols;
    expect(symbol.name).toBe('TestSymbol');
    expect(symbol.reference).toBe('R');
    expect(symbol.value).toBe('10k');
    expect(symbol.rectangles).toHaveLength(1);
    expect(symbol.polylines).toHaveLength(1);
    expect(symbol.circles).toHaveLength(1);
    expect(symbol.arcs).toHaveLength(1);
    expect(symbol.pins).toHaveLength(2);
    expect(symbol.bodyBounds.width).toBeGreaterThan(0);
    expect(symbol.bodyBounds.height).toBeGreaterThan(0);
  });

  it('loads canonical symbols from imported KiCad catalog', () => {
    const resistor = getCanonicalKicadSymbol('resistor', 2);
    const capacitor = getCanonicalKicadSymbol('capacitor', 2);
    const connector = getCanonicalKicadSymbol('connector', 6);
    const testpoint = getCanonicalKicadSymbol('testpoint', 1);
    const meta = getCanonicalSymbolCatalogMetadata();

    expect(meta.source.repo).toContain('kicad-symbols');
    expect(meta.source.commit.length).toBeGreaterThan(6);
    expect(resistor?.name).toBe('R');
    expect(capacitor?.name).toBe('C');
    expect(connector?.name).toContain('Conn_01x06');
    expect(testpoint?.name).toContain('TestPoint');
  });
});
