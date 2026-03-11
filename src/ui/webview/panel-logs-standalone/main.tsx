import { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import "../shared/index.css";
import {
  createLogClient,
  type LogTarget,
} from "../panel-logs/logRpcClient";
import { LogViewerScreen } from "../panel-logs/LogViewerScreen";

declare global {
  interface Window {
    __ATOPILE_API_URL__?: string;
  }
}

function getParam(search: URLSearchParams, ...names: string[]): string {
  for (const name of names) {
    const value = search.get(name);
    if (value) {
      return value;
    }
  }
  return "";
}

function parseTarget(): LogTarget | null {
  const search = new URLSearchParams(window.location.search);
  const buildId = getParam(search, "build_id", "buildId");
  const stage = getParam(search, "stage");
  const testRunId = getParam(search, "test_run_id", "testRunId");
  const testName = getParam(search, "test_name", "testName");

  if (buildId && testRunId) {
    return null;
  }

  if (testRunId) {
    return {
      mode: "test",
      testRunId,
      testName: testName || null,
    };
  }

  if (buildId) {
    return {
      mode: "build",
      buildId,
      stage: stage || null,
    };
  }

  return null;
}

function StandaloneTargetControl({ target }: { target: LogTarget | null }) {
  const text = useMemo(() => {
    if (!target) {
      return "No build_id or test_run_id provided";
    }

    if (target.mode === "test") {
      return target.testName
        ? `Test: ${target.testName}`
        : `Test run: ${target.testRunId}`;
    }

    return target.stage ? `Build stage: ${target.stage}` : `Build: ${target.buildId}`;
  }, [target]);

  const title = useMemo(() => {
    if (!target) {
      return text;
    }

    if (target.mode === "test") {
      return `${target.testRunId}${target.testName ? ` • ${target.testName}` : ""}`;
    }

    return `${target.buildId}${target.stage ? ` • ${target.stage}` : ""}`;
  }, [target, text]);

  return (
    <div className="lv-target-summary" title={title}>
      {text}
    </div>
  );
}

function StandaloneApp() {
  const initialTarget = useMemo(() => parseTarget(), []);
  const apiUrl = window.__ATOPILE_API_URL__ || window.location.origin;
  const [client] = useState(() => createLogClient({ mode: "standalone", apiUrl }));
  const [stage, setStage] = useState(
    initialTarget?.mode === "build" ? initialTarget.stage ?? "" : "",
  );
  const [testName, setTestName] = useState(
    initialTarget?.mode === "test" ? initialTarget.testName ?? "" : "",
  );

  const target = useMemo((): LogTarget | null => {
    if (!initialTarget) {
      return null;
    }
    if (initialTarget.mode === "test") {
      return {
        mode: "test",
        testRunId: initialTarget.testRunId,
        testName: testName || null,
      };
    }
    return {
      mode: "build",
      buildId: initialTarget.buildId,
      stage: stage || null,
    };
  }, [initialTarget, stage, testName]);

  useEffect(() => {
    return () => {
      client.dispose();
    };
  }, [client]);

  useEffect(() => {
    if (!target) {
      document.title = "Log Viewer";
      return;
    }

    document.title = target.mode === "test" ? "Test Logs" : "Build Logs";
  }, [target]);

  return (
    <LogViewerScreen
      client={client}
      target={target}
      scopeValue={target?.mode === "test" ? testName : stage}
      onScopeChange={target?.mode === "test" ? setTestName : setStage}
      targetControl={<StandaloneTargetControl target={target} />}
    />
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(<StandaloneApp />);
