import { render, AppProps } from "../shared/render";
import { useWebSocket } from "../shared/webSocket";

function App({ hubUrl, panelId, logoUrl }: AppProps) {
  const { connected, state, sendAction } = useWebSocket(hubUrl);

  return (
    <div style={{ padding: "1rem", fontFamily: "system-ui, sans-serif" }}>
      {logoUrl && (
        <img
          src={logoUrl}
          alt="atopile"
          style={{ width: 48, height: 48, marginBottom: "0.5rem" }}
        />
      )}
      <h2 style={{ marginTop: 0 }}>atopile &mdash; {panelId}</h2>
      <p>
        Hub:{" "}
        <strong style={{ color: connected ? "#4caf50" : "#f44336" }}>
          {connected ? "Connected" : "Disconnected"}
        </strong>
      </p>
      <h3>State</h3>
      <pre style={{ background: "#1e1e1e", color: "#d4d4d4", padding: "0.5rem", borderRadius: "4px", overflow: "auto" }}>
        {JSON.stringify(state, null, 2) || "{}"}
      </pre>
      <button
        onClick={() => sendAction("ping", { ts: Date.now() })}
        style={{ marginTop: "0.5rem", padding: "0.4rem 1rem", cursor: "pointer" }}
      >
        Send Ping
      </button>
    </div>
  );
}

render(App);
