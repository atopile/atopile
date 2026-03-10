import { useMemo, useState } from "react";
import "./main.css";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import { createWebviewLogger } from "../shared/logger";
import { STORE_KEYS } from "../../shared/types";
import { Button, GraphVisualizer2D, JsonView, SearchBar, Separator, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../shared/components";
import type { GraphNode, GraphEdge } from "../shared/components";
import { ComponentShowcase } from "../shared/components/ComponentShowcase";

const logger = createWebviewLogger("PanelDeveloper");

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

function DeveloperControls({ connected }: { connected: boolean }) {
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const requireClient = () => {
    if (!rpcClient || !connected) {
      throw new Error("Developer panel is not connected to the core server.");
    }
    return rpcClient;
  };

  const clearBuildDatabases = () => {
    logger.info(`clearBuildDatabases click connected=${connected}`);
    setStatusMessage(null);
    setErrorMessage(null);

    let client;
    try {
      client = requireClient();
    } catch (error) {
      logger.error(
        `clearBuildDatabases unavailable error=${error instanceof Error ? error.message : String(error)}`,
      );
      setErrorMessage(error instanceof Error ? error.message : String(error));
      return;
    }

    if (!client.sendAction("clearBuildDatabases")) {
      const message = "Developer panel is not connected to the core server.";
      logger.error(`clearBuildDatabases failed error=${message}`);
      setErrorMessage(message);
      return;
    }
    logger.info("clearBuildDatabases request sent");
  };

  const restartExtensionHost = async () => {
    setStatusMessage(null);
    setErrorMessage(null);
    try {
      await requireClient().requestAction("vscode.restartExtensionHost");
      setStatusMessage("Restarting extension host...");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error));
    }
  };

  return (
    <section className="panel-developer-section">
      <h3>Developer Controls</h3>
      <div className="panel-developer-actions">
        <Button
          variant="destructive"
          onClick={() => void clearBuildDatabases()}
          disabled={!connected}
        >
          Delete Log Directory
        </Button>
        <Button variant="outline" onClick={() => void restartExtensionHost()} disabled={!connected}>
          Restart Extension Host
        </Button>
      </div>
      {!connected ? (
        <p className="panel-developer-error">
          Developer panel is disconnected. Reconnect to the core server before using these actions.
        </p>
      ) : null}
      {statusMessage ? <p className="panel-developer-message">{statusMessage}</p> : null}
      {errorMessage ? <p className="panel-developer-error">{errorMessage}</p> : null}
    </section>
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
  ];

  return (
    <div className="panel panel-developer">
      <h2>Developer</h2>
      <div className="panel-developer-main">
        <div className="panel-developer-column">
          <DeveloperControls connected={connected} />
        </div>
        <div className="panel-developer-column">
          <section className="panel-developer-section">
            <h3>Connection Status</h3>
            <GraphVisualizer2D nodes={nodes} edges={edges} height={200} />
          </section>
          <section className="panel-developer-section">
            <h3>Store State</h3>
            <StoreTable />
          </section>
        </div>
      </div>

      <Separator className="showcase-divider" />

      <ComponentShowcase />
    </div>
  );
}

render(App);
