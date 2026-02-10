#!/usr/bin/env tsx
import { execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { parseKicadSymbolLib } from '../src/schematic-viewer/parsers/kicadSymParser';

type FamilyKey =
  | 'resistor'
  | 'capacitor'
  | 'capacitor_polarized'
  | 'inductor'
  | 'diode'
  | 'led'
  | 'testpoint';

interface SymbolSource {
  lib: string;
  symbolFile: string;
  symbolName: string;
}

const KICAD_REPO_URL = 'https://gitlab.com/kicad/libraries/kicad-symbols.git';
const CONNECTOR_VARIANT_MIN = 1;
const CONNECTOR_VARIANT_MAX = 20;

const FAMILY_SOURCES: Record<FamilyKey, SymbolSource> = {
  resistor: { lib: 'Device', symbolFile: 'R.kicad_sym', symbolName: 'R' },
  capacitor: { lib: 'Device', symbolFile: 'C.kicad_sym', symbolName: 'C' },
  capacitor_polarized: {
    lib: 'Device',
    symbolFile: 'C_Polarized.kicad_sym',
    symbolName: 'C_Polarized',
  },
  inductor: { lib: 'Device', symbolFile: 'L.kicad_sym', symbolName: 'L' },
  diode: { lib: 'Device', symbolFile: 'D.kicad_sym', symbolName: 'D' },
  led: { lib: 'Device', symbolFile: 'LED.kicad_sym', symbolName: 'LED' },
  testpoint: {
    lib: 'Connector',
    symbolFile: 'TestPoint_Small.kicad_sym',
    symbolName: 'TestPoint_Small',
  },
};

function repoFromEnv(): string | null {
  const envPath = process.env.KICAD_SYMBOLS_DIR;
  if (!envPath) return null;
  return path.resolve(envPath);
}

async function cloneKiCadSymbolsTemp(): Promise<string> {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'atopile-kicad-symbols-'));
  const cloneDir = path.join(tempRoot, 'kicad-symbols');
  execFileSync('git', ['clone', '--depth', '1', KICAD_REPO_URL, cloneDir], {
    stdio: 'inherit',
  });
  return cloneDir;
}

function getRepoCommit(repoDir: string): string {
  return execFileSync('git', ['-C', repoDir, 'rev-parse', 'HEAD'], {
    encoding: 'utf8',
  }).trim();
}

async function readSymbolFile(repoDir: string, source: SymbolSource): Promise<string> {
  const symbolPath = path.join(repoDir, `${source.lib}.kicad_symdir`, source.symbolFile);
  return fs.readFile(symbolPath, 'utf8');
}

async function loadSymbol(repoDir: string, source: SymbolSource) {
  const content = await readSymbolFile(repoDir, source);
  const parsed = parseKicadSymbolLib(content);
  const symbol = parsed.symbols.find((candidate) => candidate.name === source.symbolName);
  if (!symbol) {
    throw new Error(
      `Symbol ${source.lib}:${source.symbolName} not found in ${source.symbolFile}`,
    );
  }
  return {
    source,
    symbol,
  };
}

function loadConnectorVariants(repoDir: string) {
  const loadTasks = Array.from(
    { length: CONNECTOR_VARIANT_MAX - CONNECTOR_VARIANT_MIN + 1 },
    (_, idx) => CONNECTOR_VARIANT_MIN + idx,
  ).map(async (pinCount) => {
    const countToken = pinCount.toString().padStart(2, '0');
    const symbolFile = `Conn_01x${countToken}.kicad_sym`;
    const symbolName = `Conn_01x${countToken}`;
    const source: SymbolSource = {
      lib: 'Connector_Generic',
      symbolFile,
      symbolName,
    };
    const loaded = await loadSymbol(repoDir, source);
    return [String(pinCount), loaded] as const;
  });
  return Promise.all(loadTasks).then((entries) => Object.fromEntries(entries));
}

async function main(): Promise<void> {
  const repoDir = repoFromEnv() ?? (await cloneKiCadSymbolsTemp());
  const commit = getRepoCommit(repoDir);

  const familyEntries = await Promise.all(
    (Object.keys(FAMILY_SOURCES) as FamilyKey[]).map(async (family) => {
      const loaded = await loadSymbol(repoDir, FAMILY_SOURCES[family]);
      return [family, loaded] as const;
    }),
  );
  const families = Object.fromEntries(familyEntries);

  const connector = {
    minPinCount: CONNECTOR_VARIANT_MIN,
    maxPinCount: CONNECTOR_VARIANT_MAX,
    variants: await loadConnectorVariants(repoDir),
  };

  const output = {
    version: 1,
    generator: 'scripts/import-kicad-canonical-symbols.ts',
    generatedAt: new Date().toISOString(),
    source: {
      repo: KICAD_REPO_URL,
      commit,
    },
    families,
    connector,
  };

  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const outPath = path.resolve(
    scriptDir,
    '../src/schematic-viewer/symbol-catalog/atopileCanonicalSymbols.json',
  );
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, `${JSON.stringify(output, null, 2)}\n`, 'utf8');
  process.stdout.write(`Wrote ${outPath}\n`);
}

main().catch((error) => {
  process.stderr.write(`${String(error)}\n`);
  process.exit(1);
});
