import { render } from "../shared/render";
import { useSubscribe } from "../shared/webSocketProvider";
import { Separator, JsonView, Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../shared/components";
import { ComponentShowcase } from "../shared/components/ComponentShowcase";

function GraphEdge({ connected }: { connected: boolean }) {
  return (
    <div
      className={`graph-edge ${connected ? "is-connected" : "is-disconnected"}`}
      aria-label={connected ? "Connected link" : "Disconnected link"}
    >
      <span className="graph-edge-line" aria-hidden="true" />
      <span className="graph-edge-label">{connected ? "Connected" : "Disconnected"}</span>
    </div>
  );
}

function StoreTable() {
  const hubStatus = useSubscribe("hub_status");
  const coreStatus = useSubscribe("core_status");
  const projectState = useSubscribe("project_state");
  const entries: [string, unknown][] = [
    ["HubStatus", hubStatus],
    ["CoreStatus", coreStatus],
    ["ProjectState", projectState],
  ];

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead style={{ width: "1%", whiteSpace: "nowrap" }}>Key</TableHead>
          <TableHead>Value</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map(([key, value]) => (
          <TableRow key={key}>
            <TableCell><code>{key}</code></TableCell>
            <TableCell><JsonView value={value} defaultOpen={true} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function App() {
  const hubStatus = useSubscribe("hub_status");
  const coreStatus = useSubscribe("core_status");

  return (
    <div className="panel">
      <h2>Developer</h2>
      <h3>Connections</h3>
      <div className="graph">
        <div className="graph-node">Webviews</div>
        <GraphEdge connected={hubStatus.connected} />
        <div className="graph-node">UI Hub</div>
        <GraphEdge connected={coreStatus.connected} />
        <div className="graph-node">Core Server</div>
      </div>

      <Separator className="showcase-divider" />

      <h3>Store State</h3>
      <StoreTable />

      <Separator className="showcase-divider" />

      <ComponentShowcase />
    </div>
  );
}

render(App);
