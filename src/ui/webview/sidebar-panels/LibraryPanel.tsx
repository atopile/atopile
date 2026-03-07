import { useState, useEffect, useMemo, useCallback } from "react";
import { Library } from "lucide-react";
import {
  EmptyState,
  CenteredSpinner,
  PanelSearchBox,
  TreeRowHeader,
  CopyableCodeBlock,
  typeIcon,
} from "../shared/components";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import type { StdLibItem, StdLibChild } from "../../shared/types";
import "./LibraryPanel.css";

const TYPE_ORDER = ["interface", "module", "component", "trait", "parameter"] as const;

const TYPE_LABELS: Record<string, string> = {
  interface: "Interfaces",
  module: "Modules",
  component: "Components",
  trait: "Traits",
  parameter: "Parameters",
};

function ChildTree({ children, depth = 0 }: { children: StdLibChild[]; depth?: number }) {
  if (!children.length) return null;
  return (
    <div className="library-children">
      {children.map((child) => (
        <div key={child.name}>
          <div className="library-child-row">
            <span className={`type-icon type-${child.item_type}`}>
              {typeIcon(child.item_type)}
            </span>
            <span className="library-child-name">{child.name}</span>
            <span className="library-child-type">{child.type}</span>
          </div>
          {child.children.length > 0 && depth < 3 && (
            <ChildTree children={child.children} depth={depth + 1} />
          )}
        </div>
      ))}
    </div>
  );
}

function LibraryItem({ item }: { item: StdLibItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="library-item">
      <TreeRowHeader
        isExpandable
        isExpanded={expanded}
        onClick={() => setExpanded(!expanded)}
        label={item.name}
        className="library-item-header"
      />
      {expanded && (
        <div className="library-item-detail">
          {item.description && (
            <div className="library-item-description">{item.description}</div>
          )}
          {item.usage && (
            <CopyableCodeBlock code={item.usage} label="Usage" highlightAto />
          )}
          {item.children.length > 0 && <ChildTree children={item.children} />}
        </div>
      )}
    </div>
  );
}

export function LibraryPanel() {
  const stdlibData = WebviewRpcClient.useSubscribe("stdlibData");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    rpcClient?.sendAction("getStdlib", {});
    const timer = setTimeout(() => setLoading(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (stdlibData.items.length > 0) setLoading(false);
  }, [stdlibData.items]);

  const filtered = useMemo(() => {
    if (!search) return stdlibData.items;
    const q = search.toLowerCase();
    return stdlibData.items.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q),
    );
  }, [stdlibData.items, search]);

  const grouped = useMemo(() => {
    const groups = new Map<string, StdLibItem[]>();
    for (const item of filtered) {
      const key = item.type;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(item);
    }
    return groups;
  }, [filtered]);

  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const toggleGroup = useCallback((type: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  if (loading && stdlibData.items.length === 0) {
    return <CenteredSpinner />;
  }

  if (stdlibData.items.length === 0) {
    return (
      <EmptyState
        icon={<Library size={24} />}
        title="No library items"
        description="Standard library could not be loaded"
      />
    );
  }

  return (
    <div className="sidebar-panel">
      <PanelSearchBox value={search} onChange={setSearch} placeholder="Search library..." />
      <div className="sidebar-panel-scroll">
        {filtered.length === 0 ? (
          <EmptyState title="No matches" description={`No items match "${search}"`} />
        ) : (
          TYPE_ORDER.filter((t) => grouped.has(t)).map((type) => (
            <div key={type} className="library-group">
              <TreeRowHeader
                isExpandable
                isExpanded={!collapsed.has(type)}
                onClick={() => toggleGroup(type)}
                icon={typeIcon(type)}
                label={TYPE_LABELS[type] ?? type}
                count={grouped.get(type)!.length}
              />
              {!collapsed.has(type) &&
                grouped.get(type)!.map((item) => (
                  <LibraryItem key={item.id} item={item} />
                ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
