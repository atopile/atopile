import { useState, useEffect, useMemo, useCallback } from "react";
import {
  SlidersHorizontal,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
} from "lucide-react";
import {
  EmptyState,
  CenteredSpinner,
  PanelSearchBox,
  TreeRowHeader,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../shared/components";
import { WebviewWebSocketClient, webviewClient } from "../shared/webviewWebSocketClient";
import type { VariableNode, Variable } from "../../shared/types";
import "./ParametersPanel.css";

function StatusIcon({ status }: { status: string | null }) {
  switch (status) {
    case "ok":
    case "met":
      return <CheckCircle2 size={12} className="param-status-ok" />;
    case "error":
    case "unmet":
      return <AlertCircle size={12} className="param-status-error" />;
    default:
      return <HelpCircle size={12} className="param-status-unknown" />;
  }
}

function VariableTable({ variables }: { variables: Variable[] }) {
  if (variables.length === 0) return null;
  return (
    <Table className="parameters-table">
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Spec</TableHead>
          <TableHead>Actual</TableHead>
          <TableHead></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {variables.map((v) => (
          <TableRow key={v.name}>
            <TableCell className="param-name" title={v.name}>{v.name}</TableCell>
            <TableCell className="param-spec" title={v.spec ?? ""}>{v.spec ?? "-"}</TableCell>
            <TableCell className="param-actual" title={v.actual ?? ""}>
              {v.actual ?? "-"}
              {v.tolerance && ` ${v.tolerance}`}
            </TableCell>
            <TableCell><StatusIcon status={v.status} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function VariableNodeTree({
  node,
  expandedKeys,
  onToggle,
  depth,
  search,
}: {
  node: VariableNode;
  expandedKeys: Set<string>;
  onToggle: (key: string) => void;
  depth: number;
  search: string;
}) {
  const key = `${depth}-${node.name}`;
  const isExpanded = expandedKeys.has(key) || search.length > 0;
  const totalVars = node.variables.length + node.children.reduce(
    (sum, c) => sum + c.variables.length, 0,
  );

  return (
    <div className="parameters-node" style={{ paddingLeft: depth > 0 ? 'var(--spacing-md)' : undefined }}>
      <TreeRowHeader
        isExpandable
        isExpanded={isExpanded}
        onClick={() => onToggle(key)}
        label={node.name}
        count={totalVars}
      />
      {isExpanded && (
        <div className="parameters-children">
          <VariableTable variables={node.variables} />
          {node.children.map((child) => (
            <VariableNodeTree
              key={child.name}
              node={child}
              expandedKeys={expandedKeys}
              onToggle={onToggle}
              depth={depth + 1}
              search={search}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function filterNodes(nodes: VariableNode[], search: string): VariableNode[] {
  if (!search) return nodes;
  const q = search.toLowerCase();
  return nodes
    .map((node) => {
      const matchingVars = node.variables.filter(
        (v) =>
          v.name.toLowerCase().includes(q) ||
          (v.spec?.toLowerCase().includes(q) ?? false) ||
          (v.actual?.toLowerCase().includes(q) ?? false),
      );
      const matchingChildren = filterNodes(node.children, search);
      if (matchingVars.length === 0 && matchingChildren.length === 0) return null;
      return { ...node, variables: matchingVars, children: matchingChildren };
    })
    .filter(Boolean) as VariableNode[];
}

export function ParametersPanel() {
  const { selectedProject: projectRoot, selectedTarget } = WebviewWebSocketClient.useSubscribe("projectState");
  const variablesData = WebviewWebSocketClient.useSubscribe("variablesData");
  const currentBuilds = WebviewWebSocketClient.useSubscribe("currentBuilds");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());

  const target = selectedTarget ?? "default";

  useEffect(() => {
    if (projectRoot) {
      setLoading(true);
      webviewClient?.sendAction("getVariables", { projectRoot, target });
    }
  }, [projectRoot, target]);

  // Refresh after build completes
  useEffect(() => {
    if (
      projectRoot &&
      currentBuilds.every((b) => b.status !== "building" && b.status !== "queued")
    ) {
      webviewClient?.sendAction("getVariables", { projectRoot, target });
    }
  }, [currentBuilds, projectRoot, target]);

  useEffect(() => {
    if (variablesData.nodes.length > 0) setLoading(false);
  }, [variablesData.nodes]);

  const toggleKey = useCallback((key: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const filtered = useMemo(
    () => filterNodes(variablesData.nodes, search),
    [variablesData.nodes, search],
  );

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<SlidersHorizontal size={24} />}
        title="No project selected"
        description="Select a project to view parameters"
      />
    );
  }

  if (!loading && variablesData.nodes.length === 0) {
    return (
      <EmptyState
        icon={<SlidersHorizontal size={24} />}
        title="No parameters available"
        description="Run a build to generate parameter data"
      />
    );
  }

  return (
    <div className="sidebar-panel">
      <PanelSearchBox value={search} onChange={setSearch} placeholder="Search parameters..." />
      <div className="sidebar-panel-scroll">
        {loading ? (
          <CenteredSpinner />
        ) : filtered.length === 0 ? (
          <EmptyState title="No matches" description={`No parameters match "${search}"`} />
        ) : (
          filtered.map((node) => (
            <VariableNodeTree
              key={node.name}
              node={node}
              expandedKeys={expandedKeys}
              onToggle={toggleKey}
              depth={0}
              search={search}
            />
          ))
        )}
      </div>
    </div>
  );
}
