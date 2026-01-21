/**
 * SymbolNode - Displays a symbol in the build tree.
 * Used to show modules, interfaces, components in the build hierarchy.
 */

import { useState, memo } from 'react';
import { ChevronDown, ChevronRight, Play, Box, Zap, Cpu, CircuitBoard } from 'lucide-react';
import type { Selection, BuildSymbol } from './projectsTypes';
import './SymbolNode.css';

// Get icon for symbol type
export function getTypeIcon(type: BuildSymbol['type'], size: number = 12) {
  switch (type) {
    case 'module':
      return <Box size={size} className="type-icon module" />;
    case 'interface':
      return <Zap size={size} className="type-icon interface" />;
    case 'component':
      return <Cpu size={size} className="type-icon component" />;
    case 'parameter':
      return <CircuitBoard size={size} className="type-icon parameter" />;
  }
}

interface SymbolNodeProps {
  symbol: BuildSymbol;
  depth: number;
  projectId: string;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void;
}

export const SymbolNode = memo(function SymbolNode({
  symbol,
  depth,
  projectId,
  selection,
  onSelect,
  onBuild
}: SymbolNodeProps) {
  const [expanded, setExpanded] = useState(false);
  const [_hovered, setHovered] = useState(false);
  const hasChildren = symbol.children && symbol.children.length > 0;
  const isSelected = selection.type === 'symbol' && selection.symbolPath === symbol.path;

  return (
    <div className="symbol-node">
      <div
        className={`symbol-row ${hasChildren ? 'expandable' : ''} ${isSelected ? 'selected' : ''}`}
        style={{ paddingLeft: `${depth * 4}px` }}
        onClick={() => {
          if (hasChildren) setExpanded(!expanded);
          onSelect({
            type: 'symbol',
            projectId,
            symbolPath: symbol.path,
            label: symbol.name
          });
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {hasChildren ? (
          <button className="tree-expand" onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}>
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        ) : (
          <span className="tree-spacer" />
        )}
        {getTypeIcon(symbol.type)}
        <span className="symbol-name">{symbol.name}</span>
        {symbol.hasErrors && <span className="indicator error" />}
        {symbol.hasWarnings && !symbol.hasErrors && <span className="indicator warning" />}

        <button
          className="symbol-play-btn"
          onClick={(e) => {
            e.stopPropagation();
            onBuild('symbol', symbol.path, symbol.name);
          }}
          title={`Build ${symbol.name}`}
        >
          <Play size={10} />
        </button>
      </div>
      {expanded && hasChildren && (
        <div className="symbol-children">
          {symbol.children!.map((child, idx) => (
            <SymbolNode
              key={`${child.path}-${idx}`}
              symbol={child}
              depth={depth + 1}
              projectId={projectId}
              selection={selection}
              onSelect={onSelect}
              onBuild={onBuild}
            />
          ))}
        </div>
      )}
    </div>
  );
});
