import { render, AppProps } from "../shared/render";
import { useWebSocket } from "../shared/webSocket";

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`status-dot ${ok ? "status-dot--ok" : "status-dot--error"}`} />;
}

function App({ hubUrl }: AppProps) {
  const { connected, state } = useWebSocket(hubUrl, ["core"]);
  const core = state.core as { connected?: boolean } | undefined;
  const coreConnected = Boolean(core?.connected);

  return (
    <div className="panel">
      <h2>Developer</h2>
      <h3>Connections</h3>
      <table className="connection-table">
        <tbody>
          <tr>
            <td>Webview &rarr; Hub</td>
            <td>
              <StatusDot ok={connected} />
              {connected ? "Connected" : "Disconnected"}
            </td>
          </tr>
          <tr>
            <td>Hub &rarr; Core Server</td>
            <td>
              <StatusDot ok={coreConnected} />
              {coreConnected ? "Connected" : "Disconnected"}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

render(App);
