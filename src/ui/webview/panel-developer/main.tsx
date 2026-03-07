import { render } from "../shared/render";
import { WebviewRpcClient } from "../shared/rpcClient";
import { StoreState } from "../../shared/types";
import { Separator, JsonView, Table, TableHeader, TableBody, TableRow, TableHead, TableCell, GraphVisualizer2D } from "../shared/components";
import type { GraphNode, GraphEdge } from "../shared/components";
import { ComponentShowcase } from "../shared/components/ComponentShowcase";

function StoreRow({ storeKey }: { storeKey: keyof StoreState }) {
  const value = WebviewRpcClient.useSubscribe(storeKey);
  return (
    <TableRow>
      <TableCell><code>{storeKey}</code></TableCell>
      <TableCell><JsonView value={value} defaultOpen={true} /></TableCell>
    </TableRow>
  );
}

function StoreTable() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead style={{ width: "1%", whiteSpace: "nowrap" }}>Key</TableHead>
          <TableHead>Value</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {(Object.keys(new StoreState()) as (keyof StoreState)[]).map((key) => (
          <StoreRow key={key} storeKey={key} />
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
