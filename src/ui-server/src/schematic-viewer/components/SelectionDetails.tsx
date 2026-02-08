/**
 * SelectionDetails — shows contextual info for the currently selected
 * component, module, port, or net. Extracted from SymbolInspector.
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
import { getPinColor } from '../lib/theme';
import {
  componentColor,
  moduleColor,
  netTypeColor,
  Section,
  SectionTitle,
  Swatch,
  ListButton,
} from './SymbolInspector';

export function SelectionDetails() {
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

  if (!sheet) return null;

  const hasSelection = selectedComp || selectedMod || selectedPort || selectedNet;
  if (!hasSelection) return null;

  return (
    <div style={{ borderTop: `1px solid ${theme.borderColor}` }}>
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
    </div>
  );
}
