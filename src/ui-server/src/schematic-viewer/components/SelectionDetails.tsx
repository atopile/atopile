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
import type {
  SchematicBOMComponent,
  SchematicBOMData,
  SchematicBOMParameter,
  SchematicVariable,
  SchematicVariableNode,
  SchematicVariablesData,
} from '../types/artifacts';
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
  bomData?: SchematicBOMData | null;
  variablesData?: SchematicVariablesData | null;
}

interface NetConnectionSummary {
  net: SchematicNet;
  pinNumbers: string[];
}

function formatMm(value: number): string {
  return `${value.toFixed(2)} mm`;
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null) return '-';
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}

function formatStock(stock: number | null | undefined): string {
  if (stock == null) return 'Unknown';
  if (stock <= 0) return 'Out of stock';
  if (stock >= 1_000_000) return `${(stock / 1_000_000).toFixed(1)}M`;
  if (stock >= 1_000) return `${(stock / 1_000).toFixed(1)}K`;
  return stock.toLocaleString();
}

function formatPartSource(source: string | null | undefined): string {
  if (source === 'picked') return 'Auto-picked';
  if (source === 'specified') return 'Specified';
  if (source === 'manual') return 'Manual';
  return source ?? '-';
}

function extractAddressPath(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const primary = raw.split('|')[0] ?? raw;
  let withAddress = primary;
  if (primary.includes('::')) {
    const parts = primary.split('::');
    withAddress = parts[parts.length - 1] ?? primary;
  }
  const trimmed = withAddress.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeComponentKey(value: string | null | undefined): string {
  if (!value) return '';
  let normalized = value;
  normalized = normalized.replace(/\|.*$/, '');
  if (normalized.includes('::')) {
    const parts = normalized.split('::');
    normalized = parts[parts.length - 1] ?? normalized;
  }
  normalized = normalized.toLowerCase();
  normalized = normalized.replace(/\[(\d+)\]/g, '_$1');
  normalized = normalized.replace(/[.\s/-]+/g, '_');
  normalized = normalized.replace(/[^a-z0-9_]/g, '_');
  normalized = normalized.replace(/_+/g, '_');
  normalized = normalized.replace(/^_+|_+$/g, '');
  return normalized;
}

function collectComponentMatchKeys(
  componentId: string,
  componentName: string,
  sourceAddress?: string,
): Set<string> {
  const keys = new Set<string>();
  const add = (value: string | null | undefined) => {
    const key = normalizeComponentKey(value);
    if (key) keys.add(key);
  };
  add(componentId);
  add(componentName);
  add(extractAddressPath(componentName));
  add(sourceAddress);
  add(extractAddressPath(sourceAddress));
  for (const key of Array.from(keys)) {
    if (key.endsWith('_package')) keys.add(key.slice(0, -'_package'.length));
    if (key.endsWith('_footprint')) keys.add(key.slice(0, -'_footprint'.length));
  }
  return keys;
}

function flattenVariableNodes(nodes: SchematicVariableNode[] | undefined): SchematicVariableNode[] {
  if (!nodes || nodes.length === 0) return [];
  const flat: SchematicVariableNode[] = [];
  const stack = [...nodes];
  while (stack.length > 0) {
    const node = stack.pop()!;
    flat.push(node);
    if (node.children && node.children.length > 0) {
      for (let i = node.children.length - 1; i >= 0; i -= 1) {
        stack.push(node.children[i]);
      }
    }
  }
  return flat;
}

function findBOMComponent(
  selectedComp: { id: string; name: string; designator: string } | null,
  selectedSource: SchematicSourceRef | null,
  bomData: SchematicBOMData | null | undefined,
): SchematicBOMComponent | null {
  if (!selectedComp) return null;
  const components = bomData?.components;
  if (!components || components.length === 0) return null;

  const byDesignator = components.find((component) =>
    (component.usages ?? []).some((usage) => usage.designator === selectedComp.designator));
  if (byDesignator) return byDesignator;

  const keys = collectComponentMatchKeys(
    selectedComp.id,
    selectedComp.name,
    selectedSource?.address,
  );
  if (keys.size === 0) return null;

  return components.find((component) =>
    (component.usages ?? []).some((usage) =>
      keys.has(normalizeComponentKey(usage.address)))) ?? null;
}

function findVariableNode(
  selectedComp: { id: string; name: string } | null,
  selectedSource: SchematicSourceRef | null,
  variablesData: SchematicVariablesData | null | undefined,
): SchematicVariableNode | null {
  if (!selectedComp) return null;
  const nodes = flattenVariableNodes(variablesData?.nodes);
  if (nodes.length === 0) return null;

  const keys = collectComponentMatchKeys(
    selectedComp.id,
    selectedComp.name,
    selectedSource?.address,
  );
  if (keys.size === 0) return null;

  for (const node of nodes) {
    const nodeKey = normalizeComponentKey(node.path);
    if (!nodeKey) continue;
    if (keys.has(nodeKey)) return node;
  }

  return null;
}

function formatVariableCell(
  value: string | null | undefined,
  tolerance: string | null | undefined,
): string {
  if (!value) return '--';
  return `${value}${tolerance ?? ''}`;
}

function PartParameters({
  variables,
  bomParameters,
}: {
  variables: SchematicVariable[];
  bomParameters: SchematicBOMParameter[];
}) {
  if (variables.length === 0 && bomParameters.length === 0) return null;

  return (
    <section className="selection-card">
      <div className="selection-card-kicker">Parameters</div>

      {variables.length > 0 && (
        <div className="selection-parameter-table">
          <div className="selection-parameter-table-header">
            <span>Parameter</span>
            <span>Spec</span>
            <span>Actual</span>
          </div>
          {variables.map((variable, index) => (
            <div
              key={`${variable.name}:${variable.type ?? 'value'}:${index}`}
              className={`selection-parameter-row ${variable.meetsSpec === false ? 'error' : ''}`}
            >
              <span className="selection-parameter-name">{variable.name}</span>
              <span className="selection-parameter-value">
                {formatVariableCell(variable.spec, variable.specTolerance)}
              </span>
              <span className="selection-parameter-value">
                {formatVariableCell(variable.actual, variable.actualTolerance)}
              </span>
            </div>
          ))}
        </div>
      )}

      {bomParameters.length > 0 && (
        <>
          <div className="selection-subsection-title">Picked Part Data</div>
          <div className="selection-meta-grid">
            {bomParameters.map((parameter) => (
              <InfoRow
                key={parameter.name}
                label={parameter.name}
                value={`${parameter.value}${parameter.unit ? ` ${parameter.unit}` : ''}`}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
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
          Open in ato
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

export function SelectionDetails({
  showTopBorder = true,
  bomData = null,
  variablesData = null,
}: SelectionDetailsProps) {
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

  const selectedBOMComponent = useMemo(
    () => findBOMComponent(selectedComp, selectedSource, bomData),
    [selectedComp, selectedSource, bomData],
  );
  const selectedVariableNode = useMemo(
    () => findVariableNode(selectedComp, selectedSource, variablesData),
    [selectedComp, selectedSource, variablesData],
  );
  const selectedVariables = selectedVariableNode?.variables ?? [];
  const selectedBOMParameters = selectedBOMComponent?.parameters ?? [];

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

          {selectedBOMComponent && (
            <section className="selection-card">
              <div className="selection-card-kicker">Part Details</div>
              <div className="selection-meta-grid">
                <InfoRow label="Supplier" value={selectedBOMComponent.manufacturer || '-'} />
                <InfoRow label="MPN" value={selectedBOMComponent.mpn || '-'} mono />
                <InfoRow label="LCSC" value={selectedBOMComponent.lcsc || '-'} mono />
                <InfoRow label="Stock" value={formatStock(selectedBOMComponent.stock)} />
                <InfoRow label="Unit price" value={formatCurrency(selectedBOMComponent.unitCost)} />
                {typeof selectedBOMComponent.quantity === 'number' && (
                  <InfoRow label="Quantity" value={selectedBOMComponent.quantity} />
                )}
                <InfoRow label="Source" value={formatPartSource(selectedBOMComponent.source)} />
                <InfoRow label="Package" value={selectedBOMComponent.package || '-'} />
              </div>
            </section>
          )}

          <PartParameters
            variables={selectedVariables}
            bomParameters={selectedBOMParameters}
          />

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
