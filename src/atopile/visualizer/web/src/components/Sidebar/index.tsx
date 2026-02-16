/**
 * Main sidebar component with filter and stats panels.
 */

import { useState } from 'react';
import { FilterPanel } from './FilterPanel';
import { StatsPanel } from '../StatsPanel';
import { useGraphStore } from '../../stores/graphStore';

type Tab = 'filter' | 'stats';

export function Sidebar() {
  const [activeTab, setActiveTab] = useState<Tab>('filter');
  const { data } = useGraphStore();

  if (!data) {
    return (
      <div className="w-72 flex-shrink-0 bg-panel-bg border-r border-panel-border flex flex-col">
        <div className="p-4 text-text-secondary text-sm">No graph loaded</div>
      </div>
    );
  }

  return (
    <div className="w-72 flex-shrink-0 bg-panel-bg border-r border-panel-border flex flex-col">
      {/* Tab buttons */}
      <div className="flex border-b border-panel-border">
        <TabButton
          active={activeTab === 'filter'}
          onClick={() => setActiveTab('filter')}
          title="Filter nodes and edges"
        >
          Filters
        </TabButton>
        <TabButton
          active={activeTab === 'stats'}
          onClick={() => setActiveTab('stats')}
          title="Graph statistics"
        >
          Stats
        </TabButton>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'filter' && <FilterPanel />}
        {activeTab === 'stats' && <StatsPanel />}
      </div>
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  title?: string;
}

function TabButton({ active, onClick, children, title }: TabButtonProps) {
  return (
    <button
      className={`flex-1 py-2 px-3 text-xs font-medium transition-colors ${
        active
          ? 'bg-panel-border text-text-primary'
          : 'text-text-secondary hover:text-text-primary hover:bg-panel-border/50'
      }`}
      onClick={onClick}
      title={title}
    >
      {children}
    </button>
  );
}
