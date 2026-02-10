/**
 * StructureTree — hierarchical tree view of the schematic structure.
 *
 * Reads the module/component hierarchy from SchematicData.root and renders
 * it as an expandable tree. Syncs selection and navigation with the schematic store.
 *
 * - Single click: selectComponent(id) — highlights on canvas + shows details
 * - Double click on module: navigateInto(moduleId) — drills into that module's sheet
 * - Current navigation path is auto-expanded and visually highlighted
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useSchematicStore } from '../stores/schematicStore';
import { getRootSheet } from '../types/schematic';
import type { SchematicSheet } from '../types/schematic';
import { useTheme } from '../lib/theme';
import type { ThemeColors } from '../lib/theme';
import { componentColor, moduleColor } from './SymbolInspector';

// ── Tree node types ─────────────────────────────────────────────

interface ModuleNode {
  kind: 'module';
  id: string;
  name: string;
  typeName: string;
  componentCount: number;
  sheet: SchematicSheet;
}

interface ComponentNode {
  kind: 'component';
  id: string;
  name: string;
  designator: string;
  reference: string;
}

type TreeNode = ModuleNode | ComponentNode;

// ── Build tree nodes from a sheet ───────────────────────────────

function sheetToNodes(sheet: SchematicSheet): TreeNode[] {
  const nodes: TreeNode[] = [];
  for (const mod of sheet.modules) {
    nodes.push({
      kind: 'module',
      id: mod.id,
      name: mod.name,
      typeName: mod.typeName,
      componentCount: mod.componentCount,
      sheet: mod.sheet,
    });
  }
  for (const comp of sheet.components) {
    nodes.push({
      kind: 'component',
      id: comp.id,
      name: comp.name,
      designator: comp.designator,
      reference: comp.reference,
    });
  }
  return nodes;
}

// ── Chevron icon ────────────────────────────────────────────────

function Chevron({ expanded, color }: { expanded: boolean; color: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 14,
        height: 14,
        flexShrink: 0,
        fontSize: 10,
        color,
        transition: 'transform 120ms ease',
        transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
      }}
    >
      &#9654;
    </span>
  );
}

// ── Single tree row ─────────────────────────────────────────────

function TreeRow({
  node,
  depth,
  expanded,
  onToggle,
  isSelected,
  isOnCurrentPath,
  theme,
  onSelect,
  onNavigate,
  rowRef,
}: {
  node: TreeNode;
  depth: number;
  expanded?: boolean;
  onToggle?: () => void;
  isSelected: boolean;
  isOnCurrentPath: boolean;
  theme: ThemeColors;
  onSelect: (id: string) => void;
  onNavigate?: (id: string) => void;
  rowRef?: React.Ref<HTMLDivElement>;
}) {
  const isModule = node.kind === 'module';
  const color = isModule
    ? moduleColor((node as ModuleNode).typeName)
    : componentColor((node as ComponentNode).reference);

  return (
    <div
      ref={rowRef}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        margin: '0 6px',
        borderRadius: 3,
        paddingLeft: 8 + depth * 14,
        paddingRight: 8,
        paddingTop: 4,
        paddingBottom: 4,
        cursor: 'pointer',
        fontSize: 12,
        background: isSelected
          ? `${color}22`
          : isOnCurrentPath
            ? `${theme.textMuted}10`
            : 'transparent',
        fontWeight: isOnCurrentPath ? 600 : 400,
        userSelect: 'none',
        transition: 'background 120ms ease',
      }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node.id);
      }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        if (isModule && onNavigate) {
          onNavigate(node.id);
        }
      }}
      onMouseEnter={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background = theme.bgHover;
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background = isOnCurrentPath
            ? `${theme.textMuted}10`
            : 'transparent';
        }
      }}
    >
      {/* Expand/collapse chevron (modules only) */}
      {isModule ? (
        <span
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
          style={{ display: 'inline-flex', cursor: 'pointer' }}
        >
          <Chevron expanded={!!expanded} color={theme.textMuted} />
        </span>
      ) : (
        <span style={{ width: 14, flexShrink: 0 }} />
      )}

      {/* Color swatch */}
      <span
        style={{
          width: 8,
          height: 8,
          flexShrink: 0,
          borderRadius: isModule ? 2 : '50%',
          backgroundColor: color,
        }}
      />

      {/* Label */}
      {isModule ? (
        <>
          <span
            style={{
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              color: theme.textPrimary,
            }}
          >
            {node.name}
          </span>
          <span
            style={{
              fontSize: 9,
              color: theme.textMuted,
              fontFamily: 'monospace',
              flexShrink: 0,
            }}
          >
            {(node as ModuleNode).componentCount}p
          </span>
        </>
      ) : (
        <>
          <span
            style={{
              fontFamily: 'monospace',
              color: theme.textMuted,
              fontSize: 10,
              flexShrink: 0,
              minWidth: 20,
            }}
          >
            {(node as ComponentNode).designator}
          </span>
          <span
            style={{
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              color: theme.textPrimary,
            }}
          >
            {node.name}
          </span>
        </>
      )}
    </div>
  );
}

// ── Recursive subtree ───────────────────────────────────────────

function SubTree({
  sheet,
  depth,
  expandedSet,
  toggleExpand,
  selectedId,
  currentPathSet,
  theme,
  onSelect,
  onNavigate,
  selectedRef,
}: {
  sheet: SchematicSheet;
  depth: number;
  expandedSet: Set<string>;
  toggleExpand: (id: string) => void;
  selectedId: string | null;
  currentPathSet: Set<string>;
  theme: ThemeColors;
  onSelect: (id: string) => void;
  onNavigate: (id: string) => void;
  selectedRef: React.MutableRefObject<HTMLDivElement | null>;
}) {
  const nodes = sheetToNodes(sheet);

  return (
    <>
      {nodes.map((node) => {
        const isExpanded = expandedSet.has(node.id);
        const isSelected = selectedId === node.id;
        const isOnPath = currentPathSet.has(node.id);

        return (
          <div key={node.id}>
            <TreeRow
              node={node}
              depth={depth}
              expanded={node.kind === 'module' ? isExpanded : undefined}
              onToggle={
                node.kind === 'module' ? () => toggleExpand(node.id) : undefined
              }
              isSelected={isSelected}
              isOnCurrentPath={isOnPath}
              theme={theme}
              onSelect={onSelect}
              onNavigate={onNavigate}
              rowRef={isSelected ? selectedRef : undefined}
            />
            {node.kind === 'module' && isExpanded && (
              <SubTree
                sheet={(node as ModuleNode).sheet}
                depth={depth + 1}
                expandedSet={expandedSet}
                toggleExpand={toggleExpand}
                selectedId={selectedId}
                currentPathSet={currentPathSet}
                theme={theme}
                onSelect={onSelect}
                onNavigate={onNavigate}
                selectedRef={selectedRef}
              />
            )}
          </div>
        );
      })}
    </>
  );
}

// ── Main StructureTree component ────────────────────────────────

export function StructureTree() {
  const schematic = useSchematicStore((s) => s.schematic);
  const currentPath = useSchematicStore((s) => s.currentPath);
  const selectedComponentId = useSchematicStore((s) => s.selectedComponentId);
  const selectComponent = useSchematicStore((s) => s.selectComponent);
  const navigateInto = useSchematicStore((s) => s.navigateInto);
  const theme = useTheme();

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const selectedRowRef = useRef<HTMLDivElement | null>(null);

  // Auto-expand nodes along the current navigation path
  useEffect(() => {
    if (currentPath.length > 0) {
      setExpandedIds((prev) => {
        const next = new Set(prev);
        for (const id of currentPath) {
          next.add(id);
        }
        return next;
      });
    }
  }, [currentPath]);

  // Scroll selected row into view when selection changes from canvas
  useEffect(() => {
    if (selectedComponentId && selectedRowRef.current) {
      selectedRowRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedComponentId]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback(
    (id: string) => {
      selectComponent(id);
    },
    [selectComponent],
  );

  const handleNavigate = useCallback(
    (id: string) => {
      navigateInto(id);
    },
    [navigateInto],
  );

  if (!schematic) {
    return (
      <div style={{ padding: 12, fontSize: 11, color: theme.textMuted }}>
        Loading...
      </div>
    );
  }

  const rootSheet = getRootSheet(schematic);
  const currentPathSet = new Set(currentPath);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', paddingBottom: 8 }}>
      <div
        style={{
          fontSize: 10,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          padding: '12px 14px 8px',
          color: theme.textMuted,
        }}
      >
        Structure
      </div>
      <SubTree
        sheet={rootSheet}
        depth={0}
        expandedSet={expandedIds}
        toggleExpand={toggleExpand}
        selectedId={selectedComponentId}
        currentPathSet={currentPathSet}
        theme={theme}
        onSelect={handleSelect}
        onNavigate={handleNavigate}
        selectedRef={selectedRowRef}
      />
    </div>
  );
}
