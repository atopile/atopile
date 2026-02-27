import { render } from "../shared/render";
import { WebviewWebSocketClient } from "../shared/webviewWebSocketClient";
import { StoreState } from "../../shared/types";
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

function StoreRow({ storeKey }: { storeKey: keyof StoreState }) {
  const value = WebviewWebSocketClient.useSubscribe(storeKey);
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

const hubPort = (() => {
  try { return new URL(window.__ATOPILE_HUB_URL__).port; } catch { return ""; }
})();

function App() {
  const hubStatus = WebviewWebSocketClient.useSubscribe("hubStatus");
  const coreStatus = WebviewWebSocketClient.useSubscribe("coreStatus");

  return (
    <div className="panel">
      <h2>Developer</h2>
      <h3>Connections</h3>
      <div className="graph">
        <div className="graph-node">Webviews</div>
        <GraphEdge connected={hubStatus.connected} />
        <div className="graph-node">UI Hub{hubPort ? ` :${hubPort}` : ""}</div>
        <GraphEdge connected={coreStatus.connected} />
        <div className="graph-node">Core Server{coreStatus.coreServerPort ? ` :${coreStatus.coreServerPort}` : ""}</div>
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
