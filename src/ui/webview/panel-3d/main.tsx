import { useEffect, useState } from "react";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import { createWebviewLogger } from "../shared/logger";
import { ThreeDPreview } from "./threeDPreviewManager";
import {
  getSelectedThreeDBuild,
  resolveThreeDModel,
  type ResolvedThreeDModel,
} from "./threeDViewerState";
import "./panel-3d.css";

const logger = createWebviewLogger("Panel3D");

function App() {
  const projectState = WebviewRpcClient.useSubscribe("projectState");
  const currentBuilds = WebviewRpcClient.useSubscribe("currentBuilds");
  const previousBuilds = WebviewRpcClient.useSubscribe("previousBuilds");

  const [model, setModel] = useState<ResolvedThreeDModel | null>(null);
  const [isResolving, setIsResolving] = useState(false);

  const selectedProject = projectState.selectedProject;
  const selectedTarget = projectState.selectedTarget;
  const isSelected = Boolean(selectedProject && selectedTarget);
  const build = getSelectedThreeDBuild(
    selectedProject,
    selectedTarget,
    currentBuilds,
    previousBuilds,
  );
  const isBuilding = build?.status === "queued" || build?.status === "building";
  const resolvedModel = model?.exists && model.modelUri ? model : null;

  const startBuild = () => {
    if (!selectedProject || !selectedTarget) {
      return;
    }
    rpcClient?.sendAction("startBuild", {
      projectRoot: selectedProject,
      targets: [selectedTarget],
      includeTargets: ["glb-only"],
      excludeTargets: ["default"],
    });
  };

  const resolveModel = async () => {
    if (!selectedProject || !selectedTarget) {
      setModel(null);
      return;
    }

    setIsResolving(true);

    try {
      const result = await resolveThreeDModel(selectedProject, selectedTarget);
      setModel(result);
    } catch (error) {
      logger.error(
        `Failed to resolve 3D model: ${error instanceof Error ? error.message : String(error)}`,
      );
      setModel(null);
    } finally {
      setIsResolving(false);
    }
  };

  useEffect(() => {
    void resolveModel();
  }, [selectedProject, selectedTarget]);

  useEffect(() => {
    if (!isSelected) {
      return;
    }
    startBuild();
  }, [selectedProject, selectedTarget]);

  useEffect(() => {
    if (!isSelected || isBuilding) {
      return;
    }
    void resolveModel();
  }, [build?.buildId, build?.status, isBuilding, selectedProject, selectedTarget]);

  if (!isSelected) {
    return (
      <div className="panel-3d-state">
        <div className="panel-3d-state-title">3D Model</div>
        <p>Select a project and build target to generate a GLB preview.</p>
      </div>
    );
  }

  if (!resolvedModel) {
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
        key={`${resolvedModel.modelPath}:${resolvedModel.version ?? "missing"}`}
        modelUri={resolvedModel.modelUri}
      />
      {isBuilding && (
        <div className="panel-3d-badge">
          <span className="panel-3d-badge-spinner" />
          <span>Building...</span>
        </div>
      )}
    </div>
  );
}

render(App);
