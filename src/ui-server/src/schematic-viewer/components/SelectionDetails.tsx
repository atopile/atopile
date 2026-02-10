import { useMemo, type CSSProperties } from 'react';
import {
  useSchematicStore,
  useCurrentSheet,
  useCurrentPorts,
  useComponent,
  useModule,
  useComponentNets,
} from '../stores/schematicStore';
import type { SchematicInterfacePin, SchematicNet, SchematicPin, SchematicSourceRef } from '../types/schematic';
import { useTheme } from '../lib/theme';
import { getPinColor } from '../lib/theme';
import {
  componentColor,
  moduleColor,
  netTypeColor,
} from './SymbolInspector';
import {
  requestOpenSource,
  requestRevealInExplorer,
} from '../lib/vscodeApi';

interface SelectionDetailsProps {
  showTopBorder?: boolean;
}

interface NetConnectionSummary {
  net: SchematicNet;
  pinNumbers: string[];
}

function formatMm(value: number): string {
  return `${value.toFixed(2)} mm`;
}

function SourceCard({
  source,
  canOpen,
  canReveal,
  onOpen,
  onReveal,
}: {
  source: SchematicSourceRef | null;
  canOpen: boolean;
  canReveal: boolean;
  onOpen: () => void;
  onReveal: () => void;
}) {
  if (!source && !canOpen && !canReveal) return null;

  const location = source?.line != null
    ? source.column != null
      ? `${source.line}:${source.column}`
      : `${source.line}`
    : null;

  return (
    <section className="selection-card">
      <div className="selection-card-kicker">Source</div>
      <div className="selection-meta-grid">
        {!!source?.instancePath && (
          <InfoRow label="Instance" value={source.instancePath} mono />
        )}
        {!!source?.address && (
          <InfoRow label="Address" value={source.address} mono />
        )}
        {!!source?.filePath && (
          <InfoRow label="File" value={source.filePath} mono />
        )}
        {!!location && (
          <InfoRow label="Location" value={location} mono />
        )}
      </div>
      <div className="selection-actions">
        <button
          className="selection-action-btn"
          onClick={onOpen}
          disabled={!canOpen}
        >
          Open in ATO
        </button>
        <button
          className="selection-action-btn"
          onClick={onReveal}
          disabled={!canReveal}
        >
          Reveal in Explorer
        </button>
      </div>
    </section>
  );
}

function InfoRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="selection-meta-row">
      <span className="selection-meta-label">{label}</span>
      <span className={`selection-meta-value ${mono ? 'mono' : ''}`}>
        {value}
      </span>
    </div>
  );
}

function SelectionSwatch({
  color,
  round = false,
}: {
  color: string;
  round?: boolean;
}) {
  const style = {
    backgroundColor: color,
    borderRadius: round ? '999px' : 2,
  } as CSSProperties;
  return <span className="selection-swatch" style={style} />;
}

function NetConnectionList({
  rows,
  selectedNetId,
  onSelectNet,
  themeNetColor,
}: {
  rows: NetConnectionSummary[];
  selectedNetId: string | null;
  onSelectNet: (id: string) => void;
  themeNetColor: (net: SchematicNet) => string;
}) {
  if (rows.length === 0) {
    return <div className="selection-empty">No connected nets.</div>;
  }

  return (
    <div className="selection-list">
      {rows.map(({ net, pinNumbers }) => (
        <button
          key={net.id}
          className={`selection-list-row clickable ${selectedNetId === net.id ? 'active' : ''}`}
          onClick={() => onSelectNet(net.id)}
          type="button"
        >
          <div className="selection-list-main">
            <span className="selection-list-title">
              <span
                className="selection-dot"
                style={{ backgroundColor: themeNetColor(net) }}
              />
              <span className="selection-list-name">{net.name}</span>
            </span>
            <span className="selection-list-trailing">
              {pinNumbers.length > 0 ? pinNumbers.join(', ') : '--'}
            </span>
          </div>
          <div className="selection-list-subtitle">
            {net.type} · {net.pins.length} pins on net
          </div>
        </button>
      ))}
    </div>
  );
}

export function SelectionDetails({ showTopBorder = true }: SelectionDetailsProps) {
  const sheet = useCurrentSheet();
  const ports = useCurrentPorts();
  const selectedComponentId = useSchematicStore((s) => s.selectedComponentId);
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

  const selectedSource = useMemo(
    () => {
      if (!selectedComponentId) return null;
      return sheet?.components.find((c) => c.id === selectedComponentId)?.source
        ?? sheet?.modules.find((m) => m.id === selectedComponentId)?.source
        ?? ports.find((p) => p.id === selectedComponentId)?.source
        ?? null;
    },
    [selectedComponentId, sheet, ports],
  );
  const fallbackAddress = selectedComponentId && selectedComponentId.includes('::')
    ? selectedComponentId
    : undefined;
  const openSourceRequest = useMemo(() => {
    const address = selectedSource?.address ?? fallbackAddress;
    const filePath = selectedSource?.filePath;
    if (!address && !filePath) return null;
    return {
      address,
      filePath,
      line: selectedSource?.line,
      column: selectedSource?.column,
    };
  }, [selectedSource, fallbackAddress]);
  const revealSourceRequest = useMemo(() => {
    const address = selectedSource?.address ?? fallbackAddress;
    const filePath = selectedSource?.filePath;
    if (!address && !filePath) return null;
    return { address, filePath };
  }, [selectedSource, fallbackAddress]);

  const componentNets = useMemo((): NetConnectionSummary[] => {
    if (!selectedComp) return [];
    return connectedNets.map((net) => ({
      net,
      pinNumbers: net.pins
        .filter((pin) => pin.componentId === selectedComp.id)
        .map((pin) => pin.pinNumber),
    }));
  }, [selectedComp, connectedNets]);

  const componentPins = useMemo((): Array<{ pin: SchematicPin; net: SchematicNet | null }> => {
    if (!selectedComp) return [];
    const netByPin = new Map<string, SchematicNet>();
    for (const net of connectedNets) {
      for (const pin of net.pins) {
        if (pin.componentId === selectedComp.id && !netByPin.has(pin.pinNumber)) {
          netByPin.set(pin.pinNumber, net);
        }
      }
    }
    return selectedComp.pins.map((pin) => ({
      pin,
      net: netByPin.get(pin.number) ?? null,
    }));
  }, [selectedComp, connectedNets]);

  const moduleNets = useMemo((): NetConnectionSummary[] => {
    if (!selectedMod) return [];
    return connectedNets.map((net) => ({
      net,
      pinNumbers: net.pins
        .filter((pin) => pin.componentId === selectedMod.id)
        .map((pin) => pin.pinNumber),
    }));
  }, [selectedMod, connectedNets]);

  const modulePins = useMemo(
    (): Array<{ pin: SchematicInterfacePin; net: SchematicNet | null }> => {
      if (!selectedMod) return [];
      const netByPin = new Map<string, SchematicNet>();
      for (const net of connectedNets) {
        for (const pin of net.pins) {
          if (pin.componentId === selectedMod.id && !netByPin.has(pin.pinNumber)) {
            netByPin.set(pin.pinNumber, net);
          }
        }
      }
      return selectedMod.interfacePins.map((pin) => ({
        pin,
        net: netByPin.get(pin.id) ?? null,
      }));
    },
    [selectedMod, connectedNets],
  );

  const portNets = useMemo((): NetConnectionSummary[] => {
    if (!selectedPort) return [];
    return connectedNets.map((net) => ({
      net,
      pinNumbers: net.pins
        .filter((pin) => pin.componentId === selectedPort.id)
        .map((pin) => pin.pinNumber),
    }));
  }, [selectedPort, connectedNets]);

  const netMembers = useMemo(() => {
    if (!selectedNet || !sheet) return [];
    return selectedNet.pins.map((pin) => {
      const comp = sheet.components.find((c) => c.id === pin.componentId);
      if (comp) {
        return {
          id: comp.id,
          kind: 'component' as const,
          name: `${comp.designator} ${comp.name}`,
          subtitle: `Pin ${pin.pinNumber}`,
          color: componentColor(comp.reference),
        };
      }
      const mod = sheet.modules.find((m) => m.id === pin.componentId);
      if (mod) {
        return {
          id: mod.id,
          kind: 'module' as const,
          name: mod.name,
          subtitle: `Interface ${pin.pinNumber} · ${mod.typeName}`,
          color: moduleColor(mod.typeName),
        };
      }
      const port = ports.find((p) => p.id === pin.componentId);
      if (port) {
        return {
          id: port.id,
          kind: 'port' as const,
          name: `Port ${port.name}`,
          subtitle: `${port.interfaceType} · ${port.side}`,
          color: getPinColor(port.category, theme),
        };
      }
      return {
        id: pin.componentId,
        kind: 'unknown' as const,
        name: pin.componentId,
        subtitle: `Pin ${pin.pinNumber}`,
        color: theme.textMuted,
      };
    });
  }, [selectedNet, sheet, ports, theme]);

  const netMemberCounts = useMemo(() => {
    const components = new Set<string>();
    const modules = new Set<string>();
    const portEntries = new Set<string>();
    for (const member of netMembers) {
      if (member.kind === 'component') components.add(member.id);
      else if (member.kind === 'module') modules.add(member.id);
      else if (member.kind === 'port') portEntries.add(member.id);
    }
    return {
      components: components.size,
      modules: modules.size,
      ports: portEntries.size,
    };
  }, [netMembers]);

  if (!sheet) return null;

  const hasSelection = selectedComp || selectedMod || selectedPort || selectedNet;
  if (!hasSelection) return null;

  const sourceActions = {
    source: selectedSource,
    canOpen: !!openSourceRequest,
    canReveal: !!revealSourceRequest,
    onOpen: () => {
      if (!openSourceRequest) return;
      requestOpenSource(openSourceRequest);
    },
    onReveal: () => {
      if (!revealSourceRequest) return;
      requestRevealInExplorer(revealSourceRequest);
    },
  };

  return (
    <div className={`selection-details ${showTopBorder ? 'with-top-border' : ''}`}>
      {selectedComp && (
        <>
          <section className="selection-card">
            <div className="selection-card-header">
              <div className="selection-card-title-wrap">
                <SelectionSwatch color={componentColor(selectedComp.reference)} />
                <div>
                  <div className="selection-title">{selectedComp.designator}</div>
                  <div className="selection-subtitle">{selectedComp.name}</div>
                </div>
              </div>
              <span className="selection-badge">{selectedComp.reference}</span>
            </div>
            <div className="selection-meta-grid">
              <InfoRow label="ID" value={selectedComp.id} mono />
              <InfoRow
                label="Body"
                value={`${formatMm(selectedComp.bodyWidth)} × ${formatMm(selectedComp.bodyHeight)}`}
                mono
              />
              <InfoRow label="Pins" value={selectedComp.pins.length} />
              <InfoRow label="Connected nets" value={componentNets.length} />
              <InfoRow
                label="Unconnected"
                value={componentPins.filter((item) => !item.net).length}
              />
            </div>
          </section>

          <SourceCard {...sourceActions} />

          <section className="selection-card">
            <div className="selection-card-kicker">Connectivity</div>
            <NetConnectionList
              rows={componentNets}
              selectedNetId={selectedNetId}
              onSelectNet={(id) => selectNet(id)}
              themeNetColor={(net) => netTypeColor(net.type, theme)}
            />
          </section>

          <section className="selection-card">
            <div className="selection-card-kicker">Pins</div>
            <div className="selection-list">
              {componentPins.map(({ pin, net }) => (
                <div className="selection-list-row" key={pin.number}>
                  <div className="selection-list-main">
                    <span className="selection-list-title">
                      <span
                        className="selection-pin-chip"
                        style={{ color: getPinColor(pin.category, theme) }}
                      >
                        {pin.number}
                      </span>
                      <span className="selection-list-name">{pin.name || '(unnamed)'}</span>
                    </span>
                    <span className="selection-list-trailing">{pin.side}</span>
                  </div>
                  <div className="selection-list-subtitle">
                    {pin.category} · {pin.electricalType}
                  </div>
                  {net ? (
                    <button
                      type="button"
                      className={`selection-inline-btn ${selectedNetId === net.id ? 'active' : ''}`}
                      onClick={() => selectNet(net.id)}
                    >
                      <span
                        className="selection-dot"
                        style={{ backgroundColor: netTypeColor(net.type, theme) }}
                      />
                      {net.name}
                    </button>
                  ) : (
                    <div className="selection-list-subtitle">No net assigned.</div>
                  )}
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {selectedMod && !selectedComp && (
        <>
          <section className="selection-card">
            <div className="selection-card-header">
              <div className="selection-card-title-wrap">
                <SelectionSwatch color={moduleColor(selectedMod.typeName)} />
                <div>
                  <div className="selection-title">{selectedMod.name}</div>
                  <div className="selection-subtitle">{selectedMod.typeName}</div>
                </div>
              </div>
              <span className="selection-badge">module</span>
            </div>
            <div className="selection-meta-grid">
              <InfoRow label="ID" value={selectedMod.id} mono />
              <InfoRow
                label="Body"
                value={`${formatMm(selectedMod.bodyWidth)} × ${formatMm(selectedMod.bodyHeight)}`}
                mono
              />
              <InfoRow label="Components" value={selectedMod.componentCount} />
              <InfoRow label="Interface pins" value={selectedMod.interfacePins.length} />
              <InfoRow label="Connected nets" value={moduleNets.length} />
            </div>
            <button
              type="button"
              className="selection-enter-btn"
              onClick={() => navigateInto(selectedMod.id)}
            >
              Enter module
            </button>
          </section>

          <SourceCard {...sourceActions} />

          <section className="selection-card">
            <div className="selection-card-kicker">Connectivity</div>
            <NetConnectionList
              rows={moduleNets}
              selectedNetId={selectedNetId}
              onSelectNet={(id) => selectNet(id)}
              themeNetColor={(net) => netTypeColor(net.type, theme)}
            />
          </section>

          <section className="selection-card">
            <div className="selection-card-kicker">Interface Pins</div>
            <div className="selection-list">
              {modulePins.map(({ pin, net }) => (
                <div className="selection-list-row" key={pin.id}>
                  <div className="selection-list-main">
                    <span className="selection-list-title">
                      <span
                        className="selection-pin-chip"
                        style={{ color: getPinColor(pin.category, theme) }}
                      >
                        {pin.id}
                      </span>
                      <span className="selection-list-name">{pin.name}</span>
                    </span>
                    <span className="selection-list-trailing">{pin.side}</span>
                  </div>
                  <div className="selection-list-subtitle">
                    {pin.interfaceType} · {pin.category}
                    {pin.signals && pin.signals.length > 0 ? ` · ${pin.signals.length} signals` : ''}
                  </div>
                  {net ? (
                    <button
                      type="button"
                      className={`selection-inline-btn ${selectedNetId === net.id ? 'active' : ''}`}
                      onClick={() => selectNet(net.id)}
                    >
                      <span
                        className="selection-dot"
                        style={{ backgroundColor: netTypeColor(net.type, theme) }}
                      />
                      {net.name}
                    </button>
                  ) : (
                    <div className="selection-list-subtitle">No net assigned.</div>
                  )}
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {selectedPort && !selectedComp && !selectedMod && (
        <>
          <section className="selection-card">
            <div className="selection-card-header">
              <div className="selection-card-title-wrap">
                <SelectionSwatch color={getPinColor(selectedPort.category, theme)} round />
                <div>
                  <div className="selection-title">{selectedPort.name}</div>
                  <div className="selection-subtitle">{selectedPort.interfaceType}</div>
                </div>
              </div>
              <span className="selection-badge">port</span>
            </div>
            <div className="selection-meta-grid">
              <InfoRow label="ID" value={selectedPort.id} mono />
              <InfoRow label="Side" value={selectedPort.side} />
              <InfoRow label="Category" value={selectedPort.category} />
              <InfoRow
                label="Body"
                value={`${formatMm(selectedPort.bodyWidth)} × ${formatMm(selectedPort.bodyHeight)}`}
                mono
              />
              <InfoRow label="Connected nets" value={portNets.length} />
            </div>
            {selectedPort.signals && selectedPort.signals.length > 0 && (
              <div className="selection-signal-list">
                {selectedPort.signals.map((signal) => (
                  <span key={signal} className="selection-signal-pill">
                    {signal}
                  </span>
                ))}
              </div>
            )}
          </section>

          <SourceCard {...sourceActions} />

          <section className="selection-card">
            <div className="selection-card-kicker">Connectivity</div>
            <NetConnectionList
              rows={portNets}
              selectedNetId={selectedNetId}
              onSelectNet={(id) => selectNet(id)}
              themeNetColor={(net) => netTypeColor(net.type, theme)}
            />
          </section>
        </>
      )}

      {selectedNet && (
        <>
          <section className="selection-card">
            <div className="selection-card-header">
              <div className="selection-card-title-wrap">
                <SelectionSwatch color={netTypeColor(selectedNet.type, theme)} round />
                <div>
                  <div className="selection-title">{selectedNet.name}</div>
                  <div className="selection-subtitle">{selectedNet.type}</div>
                </div>
              </div>
              <span className="selection-badge">net</span>
            </div>
            <div className="selection-meta-grid">
              <InfoRow label="ID" value={selectedNet.id} mono />
              <InfoRow label="Connected pins" value={selectedNet.pins.length} />
              <InfoRow label="Components" value={netMemberCounts.components} />
              <InfoRow label="Modules" value={netMemberCounts.modules} />
              <InfoRow label="Ports" value={netMemberCounts.ports} />
            </div>
          </section>

          <section className="selection-card">
            <div className="selection-card-kicker">Members</div>
            {netMembers.length === 0 ? (
              <div className="selection-empty">No members on this net.</div>
            ) : (
              <div className="selection-list">
                {netMembers.map((member, index) => (
                  <button
                    key={`${member.id}:${index}`}
                    type="button"
                    className="selection-list-row clickable"
                    onClick={() => selectComponent(member.id)}
                  >
                    <div className="selection-list-main">
                      <span className="selection-list-title">
                        <span className="selection-dot" style={{ backgroundColor: member.color }} />
                        <span className="selection-list-name">{member.name}</span>
                      </span>
                      <span className="selection-list-trailing">{member.kind}</span>
                    </div>
                    <div className="selection-list-subtitle">{member.subtitle}</div>
                  </button>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
