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
  connector: {
    minPinCount: number;
    maxPinCount: number;
    variants: Record<string, CatalogSymbolEntry>;
  };
}

const catalog = catalogJson as CanonicalCatalog;

function nearestConnectorVariant(pinCount: number): string | null {
  const entries = Object.keys(catalog.connector.variants)
    .map((raw) => Number.parseInt(raw, 10))
    .filter((v) => Number.isFinite(v))
    .sort((a, b) => a - b);
  if (entries.length === 0) return null;

  const clamped = Math.min(
    Math.max(pinCount, catalog.connector.minPinCount),
    catalog.connector.maxPinCount,
  );

  let nearest = entries[0];
  let nearestDistance = Math.abs(nearest - clamped);
  for (const candidate of entries) {
    const distance = Math.abs(candidate - clamped);
    if (distance < nearestDistance) {
      nearest = candidate;
      nearestDistance = distance;
    }
  }
  return String(nearest);
}

export function getCanonicalKicadSymbol(
  family: SchematicSymbolFamily,
  pinCount: number,
): KicadSymbol | null {
  if (family === 'connector') {
    const key = nearestConnectorVariant(pinCount);
    if (!key) return null;
    return catalog.connector.variants[key]?.symbol ?? null;
  }

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

