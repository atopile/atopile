import { render, AppProps } from "../shared/render";
import { useWebSocket } from "../shared/webSocket";
import { Separator } from "../shared/components";
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

function App({ hubUrl }: AppProps) {
  const { connected, state } = useWebSocket(hubUrl, ["core"]);
  const core = state.core as { connected?: boolean } | undefined;
  const coreConnected = Boolean(core?.connected);

  return (
    <div className="panel">
      <h2>Developer</h2>
      <h3>Connections</h3>
      <div className="graph">
        <div className="graph-node">Webviews</div>
        <GraphEdge connected={connected} />
        <div className="graph-node">UI Hub</div>
        <GraphEdge connected={coreConnected} />
        <div className="graph-node">Core Server</div>
      </div>

      <Separator className="showcase-divider" />

      <ComponentShowcase />
    </div>
  );
}

render(App);
