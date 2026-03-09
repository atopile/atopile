import { useEffect, useState } from "react";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";

declare global {
  interface Window {
    __ATOPILE_LAYOUT_SERVER_URL__?: string;
  }
}

type OpenLayoutResult = {
  path: string;
};

type LayoutSelection = {
  projectRoot: string;
  target: string;
};

const layoutServerUrl = window.__ATOPILE_LAYOUT_SERVER_URL__ ?? "";

function App() {
  const projectState = WebviewRpcClient.useSubscribe("projectState");
  const [error, setError] = useState<string | null>(null);
  const [layoutPath, setLayoutPath] = useState<string | null>(null);

  const selection: LayoutSelection | null =
    projectState.selectedProject && projectState.selectedTarget
      ? {
          projectRoot: projectState.selectedProject,
          target: projectState.selectedTarget,
        }
      : null;
  const selectionKey = selection ? `${selection.projectRoot}\n${selection.target}` : null;

  useEffect(() => {
    if (!layoutServerUrl || !selection) {
      setError(null);
      setLayoutPath(null);
      return;
    }

    let cancelled = false;
    setError(null);
    setLayoutPath(null);

    void rpcClient
      ?.requestAction<OpenLayoutResult>("openLayout", selection)
      .then((result) => {
        if (!cancelled) {
          setLayoutPath(result.path);
          setError(null);
        }
      })
      .catch((nextError) => {
        if (!cancelled) {
          setLayoutPath(null);
          setError(nextError instanceof Error ? nextError.message : String(nextError));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectionKey]);

  if (!layoutServerUrl) {
    return (
      <div className="panel">
        <h2>Layout</h2>
        <p>Layout server is unavailable.</p>
      </div>
    );
  }

  if (!selection) {
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
        <p>{error ?? "Opening PCB layout..."}</p>
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
