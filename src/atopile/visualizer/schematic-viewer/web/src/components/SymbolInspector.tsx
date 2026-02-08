/**
 * SymbolInspector — right sidebar showing:
 * - Selected item details (component or module)
 * - Module list (with enter arrows)
 * - Component list
 * - Net list
 */

import { useMemo } from 'react';
import {
  useSchematicStore,
  useCurrentSheet,
  useCurrentPorts,
  useComponent,
  useModule,
  useComponentNets,
} from '../stores/schematicStore';
import { useTheme } from '../lib/theme';
import type { ThemeColors } from '../lib/theme';
import { getPinColor } from '../lib/theme';

// ── Color helpers ──────────────────────────────────────────────

function componentColor(reference: string): string {
  const r = reference.toUpperCase();
  if (r.startsWith('U')) return '#89b4fa';
  if (r.startsWith('R')) return '#cba6f7';
  if (r.startsWith('C')) return '#f9e2af';
  if (r.startsWith('L')) return '#94e2d5';
  if (r.startsWith('D')) return '#f38ba8';
  if (r.startsWith('Q')) return '#fab387';
  if (r.startsWith('J') || r.startsWith('P')) return '#a6e3a1';
  return '#7f849c';
}

function moduleColor(typeName: string): string {
  const t = typeName.toLowerCase();
  if (/power|ldo|buck|boost/i.test(t)) return '#f38ba8';
  if (/mcu|esp|stm|rp2|cpu/i.test(t)) return '#89b4fa';
  if (/sensor|bme|bmp|lis/i.test(t)) return '#a6e3a1';
  if (/led|light|display/i.test(t)) return '#f9e2af';
  if (/usb|conn|jack/i.test(t)) return '#94e2d5';
  return '#89b4fa';
}

function netTypeColor(type: string, theme: ThemeColors): string {
  switch (type) {
    case 'power':
      return theme.pinPower;
    case 'ground':
      return theme.pinGround;
    case 'bus':
      return theme.busI2C;
    case 'signal':
    default:
      return theme.pinSignal;
  }
}

// ── Main component ─────────────────────────────────────────────

export function SymbolInspector() {
  const sheet = useCurrentSheet();
  const ports = useCurrentPorts();
  const selectedComponentId = useSchematicStore(
    (s) => s.selectedComponentId,
  );
  const selectedNetId = useSchematicStore((s) => s.selectedNetId);
  const selectComponent = useSchematicStore((s) => s.selectComponent);
  const selectNet = useSchematicStore((s) => s.selectNet);
  const navigateInto = useSchematicStore((s) => s.navigateInto);
  const theme = useTheme();

  const selectedComp = useComponent(selectedComponentId);
  const selectedMod = useModule(selectedComponentId);
  const selectedPort = useMemo(() => {
    if (!selectedComponentId) return null;
    return ports.find((p) => p.id === selectedComponentId) ?? null;
  }, [selectedComponentId, ports]);
  const connectedNets = useComponentNets(selectedComponentId);

  const selectedNet = useMemo(() => {
    if (!selectedNetId || !sheet) return null;
    return sheet.nets.find((n) => n.id === selectedNetId) ?? null;
  }, [selectedNetId, sheet]);

  if (!sheet) {
    return (
      <div className="p-3 text-xs" style={{ color: theme.textMuted }}>
        Loading...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* ── Selected component details ──────────────────────── */}
      {selectedComp && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Component</SectionTitle>
          <div className="flex items-center gap-2">
            <Swatch
              color={componentColor(selectedComp.reference)}
              round={false}
            />
            <div>
              <div
                className="text-sm font-semibold"
                style={{ color: theme.textPrimary }}
              >
                {selectedComp.designator}
              </div>
              <div
                className="text-xs"
                style={{ color: theme.textSecondary }}
              >
                {selectedComp.name}
              </div>
            </div>
          </div>
          <div className="text-xs" style={{ color: theme.textMuted }}>
            {selectedComp.pins.length} pins
          </div>
          {connectedNets.length > 0 && (
            <div className="space-y-1 pt-1">
              <div
                className="text-xs"
                style={{ color: theme.textMuted }}
              >
                Connected nets:
              </div>
              {connectedNets.map((net) => (
                <ListButton
                  key={net.id}
                  active={selectedNetId === net.id}
                  color={netTypeColor(net.type, theme)}
                  round
                  onClick={() => selectNet(net.id)}
                  theme={theme}
                >
                  {net.name}
                </ListButton>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ── Selected module details ─────────────────────────── */}
      {selectedMod && !selectedComp && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Module</SectionTitle>
          <div className="flex items-center gap-2">
            <Swatch
              color={moduleColor(selectedMod.typeName)}
              round={false}
            />
            <div>
              <div
                className="text-sm font-semibold"
                style={{ color: theme.textPrimary }}
              >
                {selectedMod.typeName}
              </div>
              <div
                className="text-xs"
                style={{ color: theme.textSecondary }}
              >
                {selectedMod.name}
              </div>
            </div>
          </div>
          <div className="text-xs" style={{ color: theme.textMuted }}>
            {selectedMod.componentCount} components &middot;{' '}
            {selectedMod.interfacePins.length} interface pins
          </div>
          <button
            onClick={() => navigateInto(selectedMod.id)}
            className="text-xs px-3 py-1.5 rounded mt-2 w-full transition-colors"
            style={{
              background: moduleColor(selectedMod.typeName) + '20',
              color: moduleColor(selectedMod.typeName),
              border: `1px solid ${moduleColor(selectedMod.typeName)}40`,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background =
                moduleColor(selectedMod.typeName) + '35';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background =
                moduleColor(selectedMod.typeName) + '20';
            }}
          >
            Enter Module {'>>'}
          </button>
          {connectedNets.length > 0 && (
            <div className="space-y-1 pt-2">
              <div
                className="text-xs"
                style={{ color: theme.textMuted }}
              >
                Connected nets:
              </div>
              {connectedNets.map((net) => (
                <ListButton
                  key={net.id}
                  active={selectedNetId === net.id}
                  color={netTypeColor(net.type, theme)}
                  round
                  onClick={() => selectNet(net.id)}
                  theme={theme}
                >
                  {net.name}
                </ListButton>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ── Selected port details ──────────────────────────── */}
      {selectedPort && !selectedComp && !selectedMod && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Port</SectionTitle>
          <div className="flex items-center gap-2">
            <Swatch
              color={getPinColor(selectedPort.category, theme)}
              round
            />
            <div>
              <div
                className="text-sm font-semibold"
                style={{ color: theme.textPrimary }}
              >
                {selectedPort.name}
              </div>
              <div
                className="text-xs"
                style={{ color: theme.textSecondary }}
              >
                {selectedPort.interfaceType}
              </div>
            </div>
          </div>
          <div className="text-xs" style={{ color: theme.textMuted }}>
            External {selectedPort.side} interface
          </div>
          {connectedNets.length > 0 && (
            <div className="space-y-1 pt-1">
              <div className="text-xs" style={{ color: theme.textMuted }}>
                Connected nets:
              </div>
              {connectedNets.map((net) => (
                <ListButton
                  key={net.id}
                  active={selectedNetId === net.id}
                  color={netTypeColor(net.type, theme)}
                  round
                  onClick={() => selectNet(net.id)}
                  theme={theme}
                >
                  {net.name}
                </ListButton>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ── Selected net details ────────────────────────────── */}
      {selectedNet && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Net</SectionTitle>
          <div className="flex items-center gap-2">
            <Swatch
              color={netTypeColor(selectedNet.type, theme)}
              round
            />
            <div>
              <div
                className="text-sm font-semibold"
                style={{ color: theme.textPrimary }}
              >
                {selectedNet.name}
              </div>
              <div
                className="text-xs capitalize"
                style={{ color: theme.textSecondary }}
              >
                {selectedNet.type}
              </div>
            </div>
          </div>
          <div className="space-y-1 pt-1">
            <div className="text-xs" style={{ color: theme.textMuted }}>
              {selectedNet.pins.length} pins connected:
            </div>
            {selectedNet.pins.map((pin, i) => {
              const comp = sheet.components.find(
                (c) => c.id === pin.componentId,
              );
              const mod = sheet.modules.find(
                (m) => m.id === pin.componentId,
              );
              const port = ports.find(
                (p) => p.id === pin.componentId,
              );
              const label = port
                ? `Port: ${port.name}`
                : comp?.designator ?? mod?.name ?? pin.componentId;
              return (
                <button
                  key={i}
                  className="flex items-center gap-1.5 text-xs w-full text-left rounded px-1 py-0.5 hover:opacity-80"
                  onClick={() => selectComponent(pin.componentId)}
                >
                  <span
                    className="font-mono"
                    style={{ color: port ? getPinColor(port.category, theme) : theme.textMuted }}
                  >
                    {label}
                  </span>
                  {!port && (
                    <span style={{ color: theme.textPrimary }}>
                      pin {pin.pinNumber}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </Section>
      )}

      {/* ── Module list ──────────────────────────────────────── */}
      {sheet.modules.length > 0 && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Modules</SectionTitle>
          {sheet.modules.map((mod) => (
            <div
              key={mod.id}
              className="flex items-center gap-1 w-full"
            >
              <ListButton
                active={selectedComponentId === mod.id}
                color={moduleColor(mod.typeName)}
                round={false}
                onClick={() => selectComponent(mod.id)}
                theme={theme}
              >
                <span
                  className="font-mono"
                  style={{
                    color: theme.textMuted,
                    minWidth: 24,
                    display: 'inline-block',
                    fontSize: 9,
                  }}
                >
                  {mod.componentCount}p
                </span>
                <span
                  style={{
                    flex: 1,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {mod.name}
                </span>
              </ListButton>
              <button
                onClick={() => navigateInto(mod.id)}
                className="text-xs px-1.5 py-0.5 rounded flex-shrink-0 transition-colors"
                style={{
                  color: theme.textMuted,
                  background: 'transparent',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = theme.bgHover;
                  e.currentTarget.style.color = theme.textPrimary;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = theme.textMuted;
                }}
                title={`Enter ${mod.name}`}
              >
                {'>>'}
              </button>
            </div>
          ))}
        </Section>
      )}

      {/* ── Port list (external interfaces) ──────────────────── */}
      {ports.length > 0 && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Ports</SectionTitle>
          {ports.map((port) => (
            <ListButton
              key={port.id}
              active={selectedComponentId === port.id}
              color={getPinColor(port.category, theme)}
              round
              onClick={() => selectComponent(port.id)}
              theme={theme}
            >
              <span
                style={{
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {port.name}
              </span>
              <span
                className="font-mono"
                style={{ color: theme.textMuted, fontSize: 9 }}
              >
                {port.side}
              </span>
            </ListButton>
          ))}
        </Section>
      )}

      {/* ── Component list ──────────────────────────────────── */}
      {sheet.components.length > 0 && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Components</SectionTitle>
          {sheet.components.map((comp) => (
            <ListButton
              key={comp.id}
              active={selectedComponentId === comp.id}
              color={componentColor(comp.reference)}
              round={false}
              onClick={() => selectComponent(comp.id)}
              theme={theme}
            >
              <span
                className="font-mono"
                style={{
                  color: theme.textMuted,
                  minWidth: 24,
                  display: 'inline-block',
                }}
              >
                {comp.designator}
              </span>
              <span
                style={{
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {comp.name}
              </span>
            </ListButton>
          ))}
        </Section>
      )}

      {/* ── Net list ────────────────────────────────────────── */}
      <Section theme={theme} last>
        <SectionTitle theme={theme}>Nets</SectionTitle>
        {sheet.nets.map((net) => (
          <ListButton
            key={net.id}
            active={selectedNetId === net.id}
            color={netTypeColor(net.type, theme)}
            round
            onClick={() => selectNet(net.id)}
            theme={theme}
          >
            <span style={{ flex: 1 }}>{net.name}</span>
            <span
              className="font-mono"
              style={{ color: theme.textMuted, fontSize: 10 }}
            >
              {net.pins.length}p
            </span>
          </ListButton>
        ))}
      </Section>
    </div>
  );
}

// ── Shared micro-components ────────────────────────────────────

function Section({
  children,
  theme,
  last,
}: {
  children: React.ReactNode;
  theme: ThemeColors;
  last?: boolean;
}) {
  return (
    <div
      className="p-3 space-y-1.5"
      style={
        last
          ? undefined
          : { borderBottom: `1px solid ${theme.borderColor}` }
      }
    >
      {children}
    </div>
  );
}

function SectionTitle({
  children,
  theme,
}: {
  children: React.ReactNode;
  theme: ThemeColors;
}) {
  return (
    <div
      className="text-xs uppercase tracking-wider mb-2"
      style={{ color: theme.textMuted, fontSize: 10 }}
    >
      {children}
    </div>
  );
}

function Swatch({
  color,
  round,
}: {
  color: string;
  round: boolean;
}) {
  return (
    <span
      className={`w-3 h-3 inline-block flex-shrink-0 ${round ? 'rounded-full' : 'rounded-sm'}`}
      style={{ backgroundColor: color }}
    />
  );
}

function ListButton({
  children,
  active,
  color,
  round,
  onClick,
  theme,
}: {
  children: React.ReactNode;
  active: boolean;
  color: string;
  round: boolean;
  onClick: () => void;
  theme: ThemeColors;
}) {
  return (
    <button
      className="flex items-center gap-1.5 text-xs w-full text-left rounded px-1 py-0.5 transition-colors"
      style={{
        background: active ? `${color}20` : 'transparent',
        color: theme.textPrimary,
        flex: 1,
      }}
      onClick={onClick}
    >
      <span
        className={`w-2.5 h-2.5 inline-block flex-shrink-0 ${round ? 'rounded-full' : 'rounded-sm'}`}
        style={{ backgroundColor: color }}
      />
      {children}
    </button>
  );
}
