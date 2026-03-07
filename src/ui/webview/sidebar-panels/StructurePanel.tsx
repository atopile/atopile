import { useState, useEffect, useMemo, useCallback } from "react";
import {
  GitBranch,
  ChevronRight,
  RefreshCw,
  FileCode,
} from "lucide-react";
import {
  EmptyState,
  CenteredSpinner,
  PanelSearchBox,
  Button,
  TreeRowHeader,
  typeIcon,
} from "../shared/components";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import type { StructureModule, ModuleChild } from "../../shared/types";
import "./StructurePanel.css";

function ChildNode({
  child,
  depth,
  expandedKeys,
  onToggle,
}: {
  child: ModuleChild;
  depth: number;
  expandedKeys: Set<string>;
  onToggle: (key: string) => void;
}) {
  const key = `${depth}-${child.name}`;
  const hasChildren = child.children.length > 0;
  const isExpanded = expandedKeys.has(key);

  return (
    <div>
      <div
        className="structure-child-row"
        onClick={hasChildren ? () => onToggle(key) : undefined}
        style={{ paddingLeft: `${depth * 12 + 8}px`, cursor: hasChildren ? "pointer" : "default" }}
      >
        {hasChildren ? (
          <span className={`structure-chevron${isExpanded ? " expanded" : ""}`}>
            <ChevronRight size={10} />
          </span>
        ) : (
          <span style={{ width: 10 }} />
        )}
        <span className={`type-icon type-${child.item_type}`}>
          {typeIcon(child.item_type)}
        </span>
        <span className="structure-child-name">{child.name}</span>
        {child.spec && <span className="structure-child-spec">{child.spec}</span>}
        <span className="structure-child-type">{child.type_name}</span>
      </div>
      {hasChildren && isExpanded && (
        <div>
          {child.children.map((c) => (
            <ChildNode
              key={c.name}
              child={c}
              depth={depth + 1}
              expandedKeys={expandedKeys}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ModuleNode({
  module,
  expandedKeys,
  onToggle,
}: {
  module: StructureModule;
  expandedKeys: Set<string>;
  onToggle: (key: string) => void;
}) {
  const key = `module-${module.entry}`;
  const isExpanded = expandedKeys.has(key);

  return (
    <div className="structure-module">
      <TreeRowHeader
        isExpandable
        isExpanded={isExpanded}
        onClick={() => onToggle(key)}
        label={module.name}
        secondaryLabel={module.super_type ?? undefined}
        className="structure-module-header"
      />
      {isExpanded && module.children.length > 0 && (
        <div className="structure-children">
          {module.children.map((child) => (
            <ChildNode
              key={child.name}
              child={child}
              depth={0}
              expandedKeys={expandedKeys}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function StructurePanel() {
  const { selectedProject: projectRoot, activeFilePath: activeFile } = WebviewRpcClient.useSubscribe("projectState");
  const structureData = WebviewRpcClient.useSubscribe("structureData");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());

  const isAtoFile = activeFile?.endsWith(".ato") ?? false;

  useEffect(() => {
    if (projectRoot && isAtoFile) {
      setLoading(true);
      rpcClient?.sendAction("getStructure", { projectRoot });
    }
  }, [projectRoot, activeFile]);

  useEffect(() => {
    if (structureData.modules.length > 0) setLoading(false);
  }, [structureData.modules]);

  const handleRefresh = useCallback(() => {
    if (projectRoot) {
      setLoading(true);
      rpcClient?.sendAction("getStructure", { projectRoot });
    }
  }, [projectRoot]);

  const toggleKey = useCallback((key: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const filtered = useMemo(() => {
    if (!search) return structureData.modules;
    const q = search.toLowerCase();
    return structureData.modules.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        m.type.toLowerCase().includes(q),
    );
  }, [structureData.modules, search]);

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<GitBranch size={24} />}
        title="No project selected"
        description="Select a project to view its structure"
      />
    );
  }

  if (!isAtoFile && structureData.modules.length === 0) {
    return (
      <EmptyState
        icon={<FileCode size={24} />}
        title="Open an .ato file"
        description="Open an .ato file to view its module structure"
      />
    );
  }

  return (
    <div className="sidebar-panel">
      <div className="sidebar-panel-header">
        <span className="structure-file-path">
          {activeFile ? activeFile.split("/").pop() : "Structure"}
        </span>
        <Button size="icon" variant="ghost" onClick={handleRefresh} title="Refresh">
          <RefreshCw size={12} />
        </Button>
      </div>
      <PanelSearchBox value={search} onChange={setSearch} placeholder="Search modules..." />
      <div className="sidebar-panel-scroll">
        {loading ? (
          <CenteredSpinner />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={search ? "No matches" : "No modules found"}
            description={search ? `No modules match "${search}"` : "No module definitions in this file"}
          />
        ) : (
          filtered.map((mod) => (
            <ModuleNode
              key={mod.entry}
              module={mod}
              expandedKeys={expandedKeys}
              onToggle={toggleKey}
            />
          ))
        )}
      </div>
    </div>
  );
}
