import { useEffect, useState } from "react";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import { createWebviewLogger } from "../shared/logger";
import { ThreeDPreview } from "./threeDPreviewManager";
import "./panel-3d.css";

const logger = createWebviewLogger("Panel3D");

function App() {
  const projectState = WebviewRpcClient.useSubscribe("projectState");
  const selectedBuild = WebviewRpcClient.useSubscribe("selectedBuild");
  const projectRoot = projectState.selectedProjectRoot;
  const selectedTarget = projectState.selectedTarget;

  const [model, setModel] = useState<{
    exists: boolean;
    modelPath: string;
    modelUri: string;
    version: number | null;
  } | null>(null);

  const resolveModel = async () => {
    if (!selectedBuild?.projectRoot || !selectedBuild.target) {
      setModel(null);
      return;
    }

    try {
      if (!rpcClient) {
        throw new Error("RPC client is not initialized");
      }
      const result = await rpcClient.requestAction<{
        exists: boolean;
        modelPath: string;
        modelUri: string;
        version: number | null;
      }>("vscode.resolveThreeDModel", {
        projectRoot: selectedBuild.projectRoot,
        target: selectedBuild.target,
      });
      setModel(result);
    } catch (error) {
      logger.error(
        `Failed to resolve 3D model: ${error instanceof Error ? error.message : String(error)}`,
      );
      setModel(null);
    }
  };

  useEffect(() => {
    void resolveModel();
  }, [selectedBuild?.projectRoot, selectedBuild?.target]);

  useEffect(() => {
    if (!projectRoot || !selectedTarget) {
      return;
    }
    rpcClient?.sendAction("startBuild", {
      projectRoot,
      targets: [selectedTarget],
      includeTargets: ["glb-only"],
      excludeTargets: ["default"],
    });
  }, [projectRoot, selectedTarget]);

  useEffect(() => {
    if (
      !projectRoot
      || !selectedTarget
      || selectedBuild?.status === "queued"
      || selectedBuild?.status === "building"
    ) {
      return;
    }
    void resolveModel();
  }, [
    selectedBuild?.buildId,
    selectedBuild?.status,
    selectedBuild?.projectRoot,
    selectedBuild?.target,
    projectRoot,
    selectedTarget,
  ]);

  if (!projectRoot || !selectedTarget) {
    return (
      <div className="panel-3d-state">
        <div className="panel-3d-state-title">3D Model</div>
        <p>Select a project and build target to generate a GLB preview.</p>
      </div>
    );
  }

  if (!model?.exists || !model.modelUri) {
    return (
      <div className="panel-3d-state">
        <div className="panel-3d-spinner" aria-label="Loading" />
        <div className="panel-3d-state-title">Generating 3D model</div>
      </div>
    );
  }

  return (
    <div className="panel-3d-container">
      <ThreeDPreview
        key={`${model.modelPath}:${model.version ?? "missing"}`}
        modelUri={model.modelUri}
      />
      {(selectedBuild?.status === "queued" || selectedBuild?.status === "building") && (
        <div className="panel-3d-badge">
          <span className="panel-3d-badge-spinner" />
          <span>Building...</span>
        </div>
      )}
    </div>
  );
}

render(App);
