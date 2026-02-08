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

// ── Color helpers (exported for reuse) ─────────────────────────

export function componentColor(reference: string): string {
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

export function moduleColor(typeName: string): string {
  const t = typeName.toLowerCase();
  if (/power|ldo|buck|boost/i.test(t)) return '#f38ba8';
  if (/mcu|esp|stm|rp2|cpu/i.test(t)) return '#89b4fa';
  if (/sensor|bme|bmp|lis/i.test(t)) return '#a6e3a1';
  if (/led|light|display/i.test(t)) return '#f9e2af';
  if (/usb|conn|jack/i.test(t)) return '#94e2d5';
  return '#89b4fa';
}

export function netTypeColor(type: string, theme: ThemeColors): string {
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
      <div style={{ padding: 12, fontSize: 11, color: theme.textMuted }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      {/* Selected component details */}
      {selectedComp && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Component</SectionTitle>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Swatch color={componentColor(selectedComp.reference)} round={false} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: theme.textPrimary }}>
                {selectedComp.designator}
              </div>
              <div style={{ fontSize: 11, color: theme.textSecondary }}>
                {selectedComp.name}
              </div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: theme.textMuted }}>
            {selectedComp.pins.length} pins
          </div>
          {connectedNets.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingTop: 4 }}>
              <div style={{ fontSize: 11, color: theme.textMuted }}>Connected nets:</div>
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

      {/* Selected module details */}
      {selectedMod && !selectedComp && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Module</SectionTitle>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Swatch color={moduleColor(selectedMod.typeName)} round={false} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: theme.textPrimary }}>
                {selectedMod.typeName}
              </div>
              <div style={{ fontSize: 11, color: theme.textSecondary }}>
                {selectedMod.name}
              </div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: theme.textMuted }}>
            {selectedMod.componentCount} components &middot;{' '}
            {selectedMod.interfacePins.length} interface pins
          </div>
          <button
            onClick={() => navigateInto(selectedMod.id)}
            style={{
              fontSize: 11,
              padding: '6px 12px',
              borderRadius: 3,
              marginTop: 8,
              width: '100%',
              background: moduleColor(selectedMod.typeName) + '20',
              color: moduleColor(selectedMod.typeName),
              border: `1px solid ${moduleColor(selectedMod.typeName)}40`,
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = moduleColor(selectedMod.typeName) + '35';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = moduleColor(selectedMod.typeName) + '20';
            }}
          >
            Enter Module {'>>'}
          </button>
          {connectedNets.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingTop: 8 }}>
              <div style={{ fontSize: 11, color: theme.textMuted }}>Connected nets:</div>
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

      {/* Selected port details */}
      {selectedPort && !selectedComp && !selectedMod && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Port</SectionTitle>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Swatch color={getPinColor(selectedPort.category, theme)} round />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: theme.textPrimary }}>
                {selectedPort.name}
              </div>
              <div style={{ fontSize: 11, color: theme.textSecondary }}>
                {selectedPort.interfaceType}
              </div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: theme.textMuted }}>
            External {selectedPort.side} interface
          </div>
          {connectedNets.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingTop: 4 }}>
              <div style={{ fontSize: 11, color: theme.textMuted }}>Connected nets:</div>
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

      {/* Selected net details */}
      {selectedNet && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Selected Net</SectionTitle>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Swatch color={netTypeColor(selectedNet.type, theme)} round />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: theme.textPrimary }}>
                {selectedNet.name}
              </div>
              <div style={{ fontSize: 11, color: theme.textSecondary, textTransform: 'capitalize' }}>
                {selectedNet.type}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingTop: 4 }}>
            <div style={{ fontSize: 11, color: theme.textMuted }}>
              {selectedNet.pins.length} pins connected:
            </div>
            {selectedNet.pins.map((pin, i) => {
              const comp = sheet.components.find((c) => c.id === pin.componentId);
              const mod = sheet.modules.find((m) => m.id === pin.componentId);
              const port = ports.find((p) => p.id === pin.componentId);
              const label = port
                ? `Port: ${port.name}`
                : comp?.designator ?? mod?.name ?? pin.componentId;
              return (
                <button
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    fontSize: 11,
                    width: '100%',
                    textAlign: 'left',
                    borderRadius: 3,
                    padding: '2px 4px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: theme.textPrimary,
                  }}
                  onClick={() => selectComponent(pin.componentId)}
                >
                  <span
                    style={{
                      fontFamily: 'monospace',
                      color: port ? getPinColor(port.category, theme) : theme.textMuted,
                    }}
                  >
                    {label}
                  </span>
                  {!port && (
                    <span style={{ color: theme.textPrimary }}>pin {pin.pinNumber}</span>
                  )}
                </button>
              );
            })}
          </div>
        </Section>
      )}

      {/* Module list */}
      {sheet.modules.length > 0 && (
        <Section theme={theme}>
          <SectionTitle theme={theme}>Modules</SectionTitle>
          {sheet.modules.map((mod) => (
            <div
              key={mod.id}
              style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}
            >
              <ListButton
                active={selectedComponentId === mod.id}
                color={moduleColor(mod.typeName)}
                round={false}
                onClick={() => selectComponent(mod.id)}
                theme={theme}
              >
                <span
                  style={{
                    fontFamily: 'monospace',
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
                style={{
                  fontSize: 11,
                  padding: '2px 6px',
                  borderRadius: 3,
                  flexShrink: 0,
                  color: theme.textMuted,
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
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

      {/* Port list */}
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
                style={{ fontFamily: 'monospace', color: theme.textMuted, fontSize: 9 }}
              >
                {port.side}
              </span>
            </ListButton>
          ))}
        </Section>
      )}

      {/* Component list */}
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
                style={{
                  fontFamily: 'monospace',
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

      {/* Net list */}
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
              style={{ fontFamily: 'monospace', color: theme.textMuted, fontSize: 10 }}
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

export function Section({
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
      style={{
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        ...(last ? {} : { borderBottom: `1px solid ${theme.borderColor}` }),
      }}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  children,
  theme,
}: {
  children: React.ReactNode;
  theme: ThemeColors;
}) {
  return (
    <div
      style={{
        fontSize: 10,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: 8,
        color: theme.textMuted,
      }}
    >
      {children}
    </div>
  );
}

export function Swatch({
  color,
  round,
}: {
  color: string;
  round: boolean;
}) {
  return (
    <span
      style={{
        width: 12,
        height: 12,
        display: 'inline-block',
        flexShrink: 0,
        backgroundColor: color,
        borderRadius: round ? '50%' : 2,
      }}
    />
  );
}

export function ListButton({
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
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 11,
        width: '100%',
        textAlign: 'left',
        borderRadius: 3,
        padding: '2px 4px',
        background: active ? `${color}20` : 'transparent',
        color: theme.textPrimary,
        flex: 1,
        border: 'none',
        cursor: 'pointer',
      }}
      onClick={onClick}
    >
      <span
        style={{
          width: 10,
          height: 10,
          display: 'inline-block',
          flexShrink: 0,
          backgroundColor: color,
          borderRadius: round ? '50%' : 2,
        }}
      />
      {children}
    </button>
  );
}
