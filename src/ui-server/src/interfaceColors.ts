/**
 * Standard interface color policy.
 *
 * Colors are reserved for protocol/bus semantics only. Everything else
 * should default to neutral/monochrome tones.
 */

export type StandardInterfaceId =
  | 'i2c'
  | 'spi'
  | 'uart'
  | 'i2s'
  | 'qspi'
  | 'usb'
  | 'can'
  | 'jtag'
  | 'swd'
  | 'sdio'
  | 'ethernet'
  | 'pcie'
  | 'lin'
  | 'onewire';

export const STANDARD_INTERFACE_COLORS: Readonly<Record<StandardInterfaceId, string>> = {
  i2c: '#89b4fa',
  spi: '#cba6f7',
  uart: '#a6e3a1',
  i2s: '#74c7ec',
  qspi: '#fab387',
  usb: '#94e2d5',
  can: '#f38ba8',
  jtag: '#f9e2af',
  swd: '#89dceb',
  sdio: '#b4befe',
  ethernet: '#94e2d5',
  pcie: '#cba6f7',
  lin: '#f2cdcd',
  onewire: '#fab387',
};

interface AliasSpec {
  id: StandardInterfaceId;
  aliases: readonly string[];
}

const ALIAS_SPECS: readonly AliasSpec[] = [
  { id: 'i2c', aliases: ['i2c', 'i 2 c', 'scl', 'sda'] },
  { id: 'spi', aliases: ['spi', 'serial peripheral interface', 'mosi', 'miso', 'sck', 'sclk'] },
  { id: 'uart', aliases: ['uart', 'usart', 'serial'] },
  { id: 'i2s', aliases: ['i2s', 'i 2 s', 'inter ic sound', 'bclk', 'lrclk', 'ws'] },
  { id: 'qspi', aliases: ['qspi', 'quad spi', 'octospi'] },
  { id: 'usb', aliases: ['usb', 'usb2', 'usb3', 'type c', 'type-c', 'usbc'] },
  { id: 'can', aliases: ['can', 'canfd', 'can fd', 'controller area network'] },
  { id: 'jtag', aliases: ['jtag', 'tck', 'tms', 'tdi', 'tdo'] },
  { id: 'swd', aliases: ['swd', 'swclk', 'swdio'] },
  { id: 'sdio', aliases: ['sdio', 'sd mmc', 'sd-mmc', 'mmc'] },
  { id: 'ethernet', aliases: ['ethernet', 'eth', 'rmii', 'rgmii', 'mdio', 'mdc'] },
  { id: 'pcie', aliases: ['pcie', 'pci express'] },
  { id: 'lin', aliases: ['lin', 'local interconnect network'] },
  { id: 'onewire', aliases: ['onewire', 'one wire', '1wire', '1 wire', 'w1'] },
];

const ALIAS_TO_ID = buildAliasLookup();

function buildAliasLookup(): ReadonlyMap<string, StandardInterfaceId> {
  const out = new Map<string, StandardInterfaceId>();
  for (const spec of ALIAS_SPECS) {
    out.set(spec.id, spec.id);
    for (const alias of spec.aliases) {
      out.set(normalizeText(alias), spec.id);
      out.set(compactText(alias), spec.id);
    }
  }
  return out;
}

function normalizeText(raw: string): string {
  return raw
    .replace(/\u00B2/g, '2')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function compactText(raw: string): string {
  return normalizeText(raw).replace(/\s+/g, '');
}

/**
 * Resolve a category/interface string to a known standard interface id.
 */
export function resolveStandardInterfaceId(
  raw: string | null | undefined,
): StandardInterfaceId | null {
  if (!raw) return null;
  const normalized = normalizeText(raw);
  if (!normalized) return null;

  const exact = ALIAS_TO_ID.get(normalized) ?? ALIAS_TO_ID.get(compactText(raw));
  if (exact) return exact;

  // Conservative token fallback: avoid broad false positives.
  const tokens = new Set(normalized.split(/\s+/).filter(Boolean));
  if (tokens.has('i2c') || tokens.has('scl') || tokens.has('sda')) return 'i2c';
  if (
    tokens.has('spi') ||
    tokens.has('qspi') ||
    tokens.has('mosi') ||
    tokens.has('miso') ||
    tokens.has('sck') ||
    tokens.has('sclk')
  ) return tokens.has('qspi') ? 'qspi' : 'spi';
  if (tokens.has('uart') || tokens.has('usart')) return 'uart';
  if (tokens.has('i2s') || tokens.has('bclk') || tokens.has('lrclk')) return 'i2s';
  if (tokens.has('usb')) return 'usb';
  if (tokens.has('can') || tokens.has('canfd')) return 'can';
  if (tokens.has('swd') || tokens.has('swdio') || tokens.has('swclk')) return 'swd';
  if (tokens.has('jtag')) return 'jtag';
  if (tokens.has('sdio')) return 'sdio';
  if (tokens.has('ethernet') || tokens.has('eth')) return 'ethernet';
  if (tokens.has('pcie')) return 'pcie';
  if (tokens.has('lin')) return 'lin';
  if (tokens.has('onewire') || tokens.has('1wire') || tokens.has('w1')) return 'onewire';

  return null;
}

/**
 * Returns semantic bus/interface color, or null if the input is non-protocol.
 */
export function getStandardInterfaceColor(
  raw: string | null | undefined,
): string | null {
  const id = resolveStandardInterfaceId(raw);
  if (!id) return null;
  return STANDARD_INTERFACE_COLORS[id];
}
