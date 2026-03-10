import { useMemo, useState } from "react";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import { STORE_KEYS } from "../../shared/types";
import { Separator, JsonView, Table, TableHeader, TableBody, TableRow, TableHead, TableCell, GraphVisualizer2D, SearchBar } from "../shared/components";
import type { GraphNode, GraphEdge } from "../shared/components";
import { ComponentShowcase } from "../shared/components/ComponentShowcase";

function useAllStoreEntries(): Array<{ key: string; value: unknown }> {
  // Subscribe to all known keys so we re-render on any change.
  for (const key of STORE_KEYS) {
    WebviewRpcClient.useSubscribe(key);
  }
  // Read the full state object, which may contain keys beyond STORE_KEYS.
  const state = (rpcClient as any)?._state ?? {};
  return Object.keys(state)
    .sort()
    .map((key) => ({ key, value: state[key] }));
}

function StoreTable() {
  const entries = useAllStoreEntries();
  const [keyFilter, setKeyFilter] = useState("");
  const [valueFilter, setValueFilter] = useState("");

  const filtered = useMemo(() => {
    const kf = keyFilter.toLowerCase();
    const vf = valueFilter.toLowerCase();
    return entries.filter(({ key, value }) => {
      if (kf && !key.toLowerCase().includes(kf)) return false;
      if (vf && !JSON.stringify(value).toLowerCase().includes(vf)) return false;
      return true;
    });
  }, [entries, keyFilter, valueFilter]);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead style={{ width: "1%", whiteSpace: "nowrap" }}>
            <SearchBar value={keyFilter} onChange={setKeyFilter} placeholder="Key" />
          </TableHead>
          <TableHead>
            <SearchBar value={valueFilter} onChange={setValueFilter} placeholder="Value" />
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {filtered.map(({ key, value }) => (
          <TableRow key={key}>
            <TableCell><code>{key}</code></TableCell>
            <TableCell><JsonView value={value} defaultOpen={false} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function App() {
  const connected = WebviewRpcClient.useSubscribe("connected");
  const coreStatus = WebviewRpcClient.useSubscribe("coreStatus");

  const nodes: GraphNode[] = [
    { id: "panels", label: "Panels",       x: 0,   y: 0   },
    { id: "bridge", label: "Extension Host", x: 200, y: 0 },
    { id: "core",   label: "Core Server",  subtitle: coreStatus.coreServerPort ? `Port ${coreStatus.coreServerPort}` : undefined, x: 420, y: 0   },
    { id: "logs",   label: "Log Viewer",   x: 200, y: 100 },
  ];

  const connColor = (ok: boolean) => ok ? 'var(--success)' : 'var(--error)'
  const connLabel = (ok: boolean) => ok ? 'Connected' : 'Disconnected'

  const edges: GraphEdge[] = [
    { id: "e1", from: "panels", to: "bridge", label: connLabel(connected), color: connColor(connected) },
    { id: "e2", from: "bridge", to: "core", label: connLabel(connected), color: connColor(connected) },
    { id: "e3", from: "logs",   to: "bridge", label: connLabel(connected), color: connColor(connected) },
    { id: "e4", from: "logs",   to: "bridge", label: connLabel(connected), color: connColor(connected) },
  ];

  return (
    <div className="panel">
      <h2>Developer</h2>
      <h3>WebSocket Connections</h3>
      <GraphVisualizer2D nodes={nodes} edges={edges} height={200} />

      <Separator className="showcase-divider" />

      <h3>Store State</h3>
      <StoreTable />

      <Separator className="showcase-divider" />

      <ComponentShowcase />
    </div>
  );
}

render(App);
