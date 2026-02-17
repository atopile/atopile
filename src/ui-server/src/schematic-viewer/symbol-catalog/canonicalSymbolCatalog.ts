import type { SchematicSymbolFamily } from '../types/schematic';
import type { KicadSymbol } from '../types/symbol';
import catalogJson from './atopileCanonicalSymbols.json';

interface CatalogSymbolEntry {
  source: {
    lib: string;
    symbolFile: string;
    symbolName: string;
  };
  symbol: KicadSymbol;
}

interface CanonicalCatalog {
  version: number;
  generator: string;
  generatedAt: string;
  source: {
    repo: string;
    commit: string;
  };
  families: Record<
    Exclude<SchematicSymbolFamily, 'connector'>,
    CatalogSymbolEntry
  >;
}

const catalog = catalogJson as CanonicalCatalog;

export function getCanonicalKicadSymbol(
  family: SchematicSymbolFamily,
  _pinCount: number,
): KicadSymbol | null {
  if (family === 'connector') return null;

  const entry = catalog.families[family];
  return entry?.symbol ?? null;
}

export function getCanonicalSymbolCatalogMetadata() {
  return {
    version: catalog.version,
    generator: catalog.generator,
    generatedAt: catalog.generatedAt,
    source: catalog.source,
  };
}
