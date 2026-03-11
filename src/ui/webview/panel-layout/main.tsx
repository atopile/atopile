import { useEffect } from "react";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";

declare global {
  interface Window {
    __ATOPILE_LAYOUT_SERVER_URL__?: string;
  }
}

const layoutServerUrl = window.__ATOPILE_LAYOUT_SERVER_URL__ ?? "";

function App() {
  const projectState = WebviewRpcClient.useSubscribe("projectState");
  const layoutData = WebviewRpcClient.useSubscribe("layoutData");
  const projectRoot = projectState.selectedProjectRoot;
  const selectedTarget = projectState.selectedTarget;

  useEffect(() => {
    if (!layoutServerUrl || !projectRoot || !selectedTarget) {
      return;
    }
    rpcClient?.sendAction("openLayout", {
      projectRoot,
      target: selectedTarget,
    });
  }, [projectRoot, selectedTarget]);

  const { path: layoutPath, error, loading: isLoading } = layoutData;

  if (!layoutServerUrl) {
    return (
      <div className="panel">
        <h2>Layout</h2>
        <p>Layout server is unavailable.</p>
      </div>
    );
  }

  if (!projectRoot || !selectedTarget) {
    return (
      <div className="panel">
        <h2>Layout</h2>
        <p>Select a project and build target to open the PCB layout.</p>
      </div>
    );
  }

  if (!layoutPath) {
    return (
      <div className="panel">
        <h2>Layout</h2>
        <p>{error ?? (isLoading ? "Opening PCB layout..." : "Select a project and build target to open the PCB layout.")}</p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100vh", position: "relative" }}>
      <iframe
        key={layoutPath}
        src={`${layoutServerUrl}/?path=${encodeURIComponent(layoutPath)}`}
        title="Layout"
        style={{ width: "100%", height: "100%", border: "0", display: "block" }}
      />
      {error ? (
        <div
          style={{
            position: "absolute",
            top: 16,
            left: 16,
            right: 16,
            padding: "12px 14px",
            background: "rgba(20, 24, 34, 0.92)",
            border: "1px solid rgba(255,255,255,0.12)",
            color: "#f3f4f6",
            fontSize: 12,
            lineHeight: 1.4,
          }}
        >
          {error}
        </div>
      ) : null}
    </div>
  );
}

render(App);
