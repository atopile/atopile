import { useEffect, useMemo, useState } from "react";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../shared/components/Select";
import {
  createLogClient,
} from "./logRpcClient";
import { LogViewerScreen } from "./LogViewerScreen";

function LogViewer() {
  const [client] = useState(() => {
    if (!rpcClient) {
      throw new Error("VS Code RPC client is not connected");
    }
    return createLogClient({ mode: "vscode", rpcClient });
  });
  const projectState = WebviewRpcClient.useSubscribe("projectState");
  const selectedBuild = WebviewRpcClient.useSubscribe("selectedBuild");
  const buildsByProjectData = WebviewRpcClient.useSubscribe("buildsByProjectData");
  const [buildId, setBuildId] = useState("");
  const [stage, setStage] = useState("");
  const projectRoot = projectState.selectedProjectRoot;
  const selectedTarget = projectState.selectedTarget;

  useEffect(() => {
    return () => {
      client.dispose();
    };
  }, [client]);

  useEffect(() => {
    if (!projectRoot) {
      return;
    }
    rpcClient?.sendAction("getBuildsByProject", {
      projectRoot,
      target: selectedTarget,
      limit: 100,
    });
  }, [projectRoot, selectedTarget]);

  const projectBuilds = useMemo(() => {
    if (!projectRoot || buildsByProjectData.projectRoot !== projectRoot) {
      return [];
    }
    const builds = [...buildsByProjectData.builds];
    if (selectedBuild?.projectRoot === projectRoot && selectedBuild.buildId) {
      builds.unshift(selectedBuild);
    }
    return builds
      .filter((build, index, entries) =>
        index === entries.findIndex((entry) => entry.buildId === build.buildId),
      )
      .sort((left, right) => (right.startedAt ?? 0) - (left.startedAt ?? 0));
  }, [
    buildsByProjectData.builds,
    buildsByProjectData.projectRoot,
    projectRoot,
    selectedBuild,
  ]);

  useEffect(() => {
    const nextBuildId = projectState.logViewBuildId;
    const nextStage = projectState.logViewStage;
    if (nextBuildId) {
      setBuildId(nextBuildId);
      setStage(nextStage ?? "");
    }
  }, [projectState.logViewBuildId, projectState.logViewStage]);

  useEffect(() => {
    const selectedVisible = buildId && projectBuilds.some((build) => build.buildId === buildId);
    if (selectedVisible) {
      return;
    }
    setBuildId(projectBuilds[0]?.buildId ?? "");
    setStage("");
  }, [buildId, projectBuilds]);

  const buildItems = useMemo(
    () =>
      projectBuilds.map((build) => ({
        label: `${build.name || "default"} - ${build.status} ${
          build.startedAt
            ? new Date(build.startedAt * 1000).toLocaleTimeString()
            : ""
        }`,
        value: build.buildId || "",
      })),
    [projectBuilds],
  );

  const target = useMemo(
    () => (buildId ? { mode: "build" as const, buildId, stage: stage || null } : null),
    [buildId, stage],
  );

  return (
    <LogViewerScreen
      client={client}
      target={target}
      scopeValue={stage}
      onScopeChange={setStage}
      targetControl={
        <Select
          items={buildItems}
          value={buildId || null}
          onValueChange={(value) => {
            const nextBuildId = value || "";
            setBuildId(nextBuildId);
            setStage("");
            rpcClient?.sendAction("setLogViewCurrentId", {
              buildId: nextBuildId || null,
              stage: null,
            });
          }}
          className="lv-build-select"
        >
          <SelectTrigger className="lv-select-trigger">
            <SelectValue placeholder="Select build..." />
          </SelectTrigger>
          <SelectContent>
            {buildItems.map((item) => (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      }
    />
  );
}

render(LogViewer);
