/**
 * Filter panel for controlling node and edge visibility.
 */

import { useMemo, useState } from 'react';
import * as Checkbox from '@radix-ui/react-checkbox';
import * as Collapsible from '@radix-ui/react-collapsible';
import { useGraphStore } from '../../stores/graphStore';
import { useFilterStore } from '../../stores/filterStore';
import { useCollapseStore } from '../../stores/collapseStore';
import { useNavigationStore } from '../../stores/navigationStore';
import { computeVisibleNodesWithNavigation } from '../../lib/filterEngine';
import type { EdgeTypeKey } from '../../types/graph';

const EDGE_TYPE_LABELS: Record<EdgeTypeKey, string> = {
  composition: 'Composition',
  trait: 'Trait',
  pointer: 'Pointer',
  connection: 'Connection',
  operand: 'Operand',
  type: 'Type',
  next: 'Next',
};

const ALL_EDGE_TYPES: EdgeTypeKey[] = [
  'composition',
  'trait',
  'pointer',
  'connection',
  'operand',
  'type',
  'next',
];

export function FilterPanel() {
  const { data, index } = useGraphStore();
  const {
    config,
    toggleNodeType,
    toggleEdgeTypeVisible,
    resetFilters,
    setAllNodeTypesExcluded,
    setAllEdgeTypesVisible,
    setHideAnonNodes,
    setHideOrphans,
    toggleTraitRequired,
  } = useFilterStore();
  const { state: collapseState, toggleTraits } = useCollapseStore();
  const { currentRootId, viewDepth, depthEnabled } = useNavigationStore();

  const [nodeTypesOpen, setNodeTypesOpen] = useState(true);
  const [edgeTypesOpen, setEdgeTypesOpen] = useState(true);
  const [traitsOpen, setTraitsOpen] = useState(false);
  const [nodeTypeSearch, setNodeTypeSearch] = useState('');
  const [traitSearch, setTraitSearch] = useState('');

  // Compute currently visible nodes
  const visibleNodes = useMemo(() => {
    if (!data || !index) return new Set<string>();
    const navigation = { currentRootId, viewDepth, depthEnabled };
    return computeVisibleNodesWithNavigation(data, index, config, collapseState, navigation);
  }, [data, index, config, collapseState, currentRootId, viewDepth, depthEnabled]);

  // Get available types with both total and filtered counts, sorted by filtered count (descending)
  const nodeTypesWithCounts = useMemo(() => {
    if (!index || !data) return [];
    const types: Array<{ name: string; total: number; filtered: number }> = [];
    for (const [typeName, nodeIds] of index.nodesByType.entries()) {
      // Count how many are visible
      let filtered = 0;
      for (const nodeId of nodeIds) {
        if (visibleNodes.has(nodeId)) {
          filtered++;
        }
      }
      types.push({ name: typeName, total: nodeIds.size, filtered });
    }
    return types.sort((a, b) => b.filtered - a.filtered);
  }, [index, data, visibleNodes]);

  // Get all unique traits with counts
  const traitsWithCounts = useMemo(() => {
    if (!index || !data) return [];
    const traits: Array<{ name: string; total: number; filtered: number }> = [];
    for (const [traitName, nodeIds] of index.nodesByTrait.entries()) {
      let filtered = 0;
      for (const nodeId of nodeIds) {
        if (visibleNodes.has(nodeId)) {
          filtered++;
        }
      }
      traits.push({ name: traitName, total: nodeIds.size, filtered });
    }
    return traits.sort((a, b) => b.filtered - a.filtered);
  }, [index, data, visibleNodes]);

  // Filter node types by search
  const filteredNodeTypes = useMemo(() => {
    if (!nodeTypeSearch.trim()) return nodeTypesWithCounts;
    const search = nodeTypeSearch.toLowerCase();
    return nodeTypesWithCounts.filter((t) =>
      t.name.toLowerCase().includes(search)
    );
  }, [nodeTypesWithCounts, nodeTypeSearch]);

  // Filter traits by search
  const filteredTraits = useMemo(() => {
    if (!traitSearch.trim()) return traitsWithCounts;
    const search = traitSearch.toLowerCase();
    return traitsWithCounts.filter((t) =>
      t.name.toLowerCase().includes(search)
    );
  }, [traitsWithCounts, traitSearch]);

  // Total visible nodes count for header
  const totalVisible = visibleNodes.size;

  if (!data || !index) return null;

  // Count stats for buttons
  const allTypesVisible =
    nodeTypesWithCounts.length > 0 &&
    nodeTypesWithCounts.every((t) => !config.nodeTypes.excluded.has(t.name));
  const noTypesVisible =
    nodeTypesWithCounts.length > 0 &&
    nodeTypesWithCounts.every((t) => config.nodeTypes.excluded.has(t.name));
  const allEdgesVisible = ALL_EDGE_TYPES.every((t) =>
    config.edgeTypes.visible.has(t)
  );
  const noEdgesVisible = ALL_EDGE_TYPES.every(
    (t) => !config.edgeTypes.visible.has(t)
  );

  return (
    <div className="space-y-4">
      {/* Reset button */}
      <button
        onClick={resetFilters}
        className="w-full py-1.5 px-3 text-xs bg-panel-border rounded hover:bg-panel-border/80 transition-colors"
      >
        Reset All Filters
      </button>

      {/* Hide options */}
      <div className="space-y-2">
        {/* Hide anonymous nodes toggle */}
        <div className="flex items-center gap-2 px-1">
          <Checkbox.Root
            id="hide-anon"
            checked={config.hideAnonNodes ?? false}
            onCheckedChange={(checked) => setHideAnonNodes(checked === true)}
            className="checkbox-root"
          >
            <Checkbox.Indicator className="checkbox-indicator">
              <CheckIcon />
            </Checkbox.Indicator>
          </Checkbox.Root>
          <label
            htmlFor="hide-anon"
            className="text-xs text-text-secondary cursor-pointer hover:text-text-primary"
          >
            Hide anonymous nodes
          </label>
        </div>

        {/* Hide trait nodes toggle (moved from CollapsePanel) */}
        <div className="flex items-center gap-2 px-1">
          <Checkbox.Root
            id="hide-traits"
            checked={collapseState.collapsedTraits}
            onCheckedChange={() => toggleTraits()}
            className="checkbox-root"
          >
            <Checkbox.Indicator className="checkbox-indicator">
              <CheckIcon />
            </Checkbox.Indicator>
          </Checkbox.Root>
          <label
            htmlFor="hide-traits"
            className="text-xs text-text-secondary cursor-pointer hover:text-text-primary"
          >
            Hide trait nodes
          </label>
        </div>

        {/* Hide orphans toggle */}
        <div className="flex items-center gap-2 px-1">
          <Checkbox.Root
            id="hide-orphans"
            checked={config.hideOrphans ?? false}
            onCheckedChange={(checked) => setHideOrphans(checked === true)}
            className="checkbox-root"
          >
            <Checkbox.Indicator className="checkbox-indicator">
              <CheckIcon />
            </Checkbox.Indicator>
          </Checkbox.Root>
          <label
            htmlFor="hide-orphans"
            className="text-xs text-text-secondary cursor-pointer hover:text-text-primary"
          >
            Hide orphans
          </label>
        </div>
      </div>

      {/* Edge Types */}
      <CollapsibleSection
        title="Edge Types"
        open={edgeTypesOpen}
        onOpenChange={setEdgeTypesOpen}
      >
        <div className="space-y-2">
          {/* Select/Unselect all buttons */}
          <div className="flex gap-1 mb-2">
            <button
              onClick={() => setAllEdgeTypesVisible(true)}
              disabled={allEdgesVisible}
              className="flex-1 py-1 px-2 text-[10px] bg-panel-border rounded hover:bg-panel-border/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Select All
            </button>
            <button
              onClick={() => setAllEdgeTypesVisible(false)}
              disabled={noEdgesVisible}
              className="flex-1 py-1 px-2 text-[10px] bg-panel-border rounded hover:bg-panel-border/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Unselect All
            </button>
          </div>
          <div className="space-y-1">
            {ALL_EDGE_TYPES.map((edgeType) => (
              <CheckboxItem
                key={edgeType}
                id={`edge-${edgeType}`}
                label={EDGE_TYPE_LABELS[edgeType]}
                checked={config.edgeTypes.visible.has(edgeType)}
                onCheckedChange={() => toggleEdgeTypeVisible(edgeType)}
              />
            ))}
          </div>
        </div>
      </CollapsibleSection>

      {/* Traits Filter */}
      <CollapsibleSection
        title={`Traits (${config.traits.required.size} required)`}
        open={traitsOpen}
        onOpenChange={setTraitsOpen}
      >
        <div className="space-y-2">
          <div className="text-[10px] text-text-secondary mb-2">
            Check traits to filter nodes that must have them
          </div>

          {/* Search box */}
          <input
            type="text"
            placeholder="Search traits..."
            value={traitSearch}
            onChange={(e) => setTraitSearch(e.target.value)}
            className="w-full px-2 py-1 text-xs bg-graph-bg border border-panel-border rounded text-text-primary placeholder:text-text-secondary/50"
          />

          {/* Clear all button */}
          {config.traits.required.size > 0 && (
            <button
              onClick={() => {
                // Clear all required traits
                for (const trait of config.traits.required) {
                  toggleTraitRequired(trait);
                }
              }}
              className="w-full py-1 px-2 text-[10px] bg-panel-border rounded hover:bg-panel-border/80 transition-colors"
            >
              Clear All Required
            </button>
          )}

          {/* Trait list */}
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {filteredTraits.map(({ name, total, filtered }) => (
              <CheckboxItem
                key={name}
                id={`trait-${name}`}
                label={name}
                count={total}
                filteredCount={filtered}
                checked={config.traits.required.has(name)}
                onCheckedChange={() => toggleTraitRequired(name)}
              />
            ))}
            {filteredTraits.length === 0 && traitSearch && (
              <div className="text-xs text-text-secondary py-2 text-center">
                No traits match "{traitSearch}"
              </div>
            )}
          </div>
        </div>
      </CollapsibleSection>

      {/* Node Types */}
      <CollapsibleSection
        title={`Node Types (${totalVisible} visible)`}
        open={nodeTypesOpen}
        onOpenChange={setNodeTypesOpen}
      >
        <div className="space-y-2">
          {/* Search box */}
          <input
            type="text"
            placeholder="Search types..."
            value={nodeTypeSearch}
            onChange={(e) => setNodeTypeSearch(e.target.value)}
            className="w-full px-2 py-1 text-xs bg-graph-bg border border-panel-border rounded text-text-primary placeholder:text-text-secondary/50"
          />

          {/* Select/Unselect all buttons */}
          <div className="flex gap-1">
            <button
              onClick={() => setAllNodeTypesExcluded(false)}
              disabled={allTypesVisible}
              className="flex-1 py-1 px-2 text-[10px] bg-panel-border rounded hover:bg-panel-border/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Select All
            </button>
            <button
              onClick={() =>
                setAllNodeTypesExcluded(
                  true,
                  nodeTypesWithCounts.map((t) => t.name)
                )
              }
              disabled={noTypesVisible}
              className="flex-1 py-1 px-2 text-[10px] bg-panel-border rounded hover:bg-panel-border/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Unselect All
            </button>
          </div>

          {/* Type list - show ALL items */}
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {filteredNodeTypes.map(({ name, total, filtered }) => (
              <CheckboxItem
                key={name}
                id={`type-${name}`}
                label={name}
                count={total}
                filteredCount={filtered}
                checked={!config.nodeTypes.excluded.has(name)}
                onCheckedChange={() => toggleNodeType(name)}
              />
            ))}
            {filteredNodeTypes.length === 0 && nodeTypeSearch && (
              <div className="text-xs text-text-secondary py-2 text-center">
                No types match "{nodeTypeSearch}"
              </div>
            )}
          </div>
        </div>
      </CollapsibleSection>
    </div>
  );
}

interface CollapsibleSectionProps {
  title: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

function CollapsibleSection({
  title,
  open,
  onOpenChange,
  children,
}: CollapsibleSectionProps) {
  return (
    <Collapsible.Root open={open} onOpenChange={onOpenChange}>
      <Collapsible.Trigger className="flex items-center gap-2 w-full text-left text-sm font-medium text-text-primary hover:text-white transition-colors">
        <span className="text-xs">{open ? '▼' : '▶'}</span>
        {title}
      </Collapsible.Trigger>
      <Collapsible.Content className="mt-2 pl-4">
        {children}
      </Collapsible.Content>
    </Collapsible.Root>
  );
}

interface CheckboxItemProps {
  id: string;
  label: string;
  count?: number;
  filteredCount?: number;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

function CheckboxItem({ id, label, count, filteredCount, checked, onCheckedChange }: CheckboxItemProps) {
  return (
    <div className="flex items-center gap-2">
      <Checkbox.Root
        id={id}
        checked={checked}
        onCheckedChange={(checked) => onCheckedChange(checked === true)}
        className="checkbox-root"
      >
        <Checkbox.Indicator className="checkbox-indicator">
          <CheckIcon />
        </Checkbox.Indicator>
      </Checkbox.Root>
      <label
        htmlFor={id}
        className="flex-1 flex items-center justify-between text-xs text-text-secondary cursor-pointer hover:text-text-primary truncate gap-2"
      >
        <span className="truncate">{label}</span>
        {count !== undefined && (
          <span className="text-text-secondary/60 text-[10px] tabular-nums flex-shrink-0">
            {filteredCount !== undefined ? (
              <span>
                <span className={filteredCount > 0 ? 'text-green-400' : ''}>{filteredCount}</span>
                <span className="text-text-secondary/40">/{count}</span>
              </span>
            ) : (
              count
            )}
          </span>
        )}
      </label>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M2 6L5 9L10 3"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
