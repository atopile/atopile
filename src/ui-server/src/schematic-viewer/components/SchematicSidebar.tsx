import { useMemo, useState } from 'react';
import {
  Cable,
  ChevronLeft,
  ChevronRight,
  Cpu,
  GitBranch,
  Layout,
  Target,
} from 'lucide-react';
import { useTheme } from '../lib/theme';
import { useCurrentSheet, useSchematicStore } from '../stores/schematicStore';
import { SelectionDetails } from './SelectionDetails';
import { StructureTree } from './StructureTree';
import './SchematicSidebar.css';

const TAB_STORAGE_KEY = 'schematic.viewer.sidebar.tab';

type SidebarTab = 'structure' | 'selection';

function readInitialTab(): SidebarTab {
  if (typeof window === 'undefined') return 'structure';
  const value = window.localStorage.getItem(TAB_STORAGE_KEY);
  return value === 'selection' ? 'selection' : 'structure';
}

interface SchematicSidebarProps {
  width: number;
  collapsed: boolean;
  onSetCollapsed: (collapsed: boolean) => void;
}

export function SchematicSidebar({
  width,
  collapsed,
  onSetCollapsed,
}: SchematicSidebarProps) {
  const theme = useTheme();
  const sheet = useCurrentSheet();
  const selectedComponentId = useSchematicStore((s) => s.selectedComponentId);
  const selectedNetId = useSchematicStore((s) => s.selectedNetId);

  const [activeTab, setActiveTab] = useState<SidebarTab>(readInitialTab);
  const hasSelection = !!selectedComponentId || !!selectedNetId;

  const statItems = useMemo(() => {
    if (!sheet) return [];
    return [
      { label: 'Modules', value: sheet.modules.length, icon: Layout },
      { label: 'Components', value: sheet.components.length, icon: Cpu },
      { label: 'Nets', value: sheet.nets.length, icon: Cable },
    ];
  }, [sheet]);

  const cssVars = {
    '--sv-bg': theme.bgSecondary,
    '--sv-bg-elev': theme.bgTertiary,
    '--sv-border': theme.borderColor,
    '--sv-hover': theme.bgHover,
    '--sv-text': theme.textPrimary,
    '--sv-muted': theme.textMuted,
    '--sv-secondary': theme.textSecondary,
    '--sv-accent': theme.accent,
  } as React.CSSProperties;

  const updateTab = (tab: SidebarTab) => {
    setActiveTab(tab);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(TAB_STORAGE_KEY, tab);
    }
  };

  const openTab = (tab: SidebarTab) => {
    updateTab(tab);
    if (collapsed) onSetCollapsed(false);
  };

  return (
    <aside
      className={`schematic-sidebar ${collapsed ? 'collapsed' : ''}`}
      style={{ ...cssVars, width: collapsed ? 46 : width }}
    >
      {collapsed ? (
        <div className="schematic-sidebar-rail">
          <div className="schematic-sidebar-rail-top">
            <button
              className={`sidebar-rail-btn ${activeTab === 'structure' ? 'active' : ''}`}
              onClick={() => openTab('structure')}
              title="Open structure navigator"
            >
              <GitBranch size={16} />
            </button>
            <button
              className={`sidebar-rail-btn ${activeTab === 'selection' ? 'active' : ''}`}
              onClick={() => openTab('selection')}
              title="Open selection details"
            >
              <Target size={16} />
            </button>
          </div>
          <button
            className="sidebar-rail-btn expand"
            onClick={() => onSetCollapsed(false)}
            title="Expand sidebar"
          >
            <ChevronLeft size={16} />
          </button>
        </div>
      ) : (
        <>
          <header className="schematic-sidebar-header">
            <div className="schematic-sidebar-kicker">Schematic Inspector</div>
            <div className="schematic-sidebar-title-row">
              <h2 className="schematic-sidebar-title">
                {activeTab === 'structure' ? 'Structure' : 'Selection'}
              </h2>
              <button
                className="schematic-sidebar-collapse-btn"
                onClick={() => onSetCollapsed(true)}
                title="Collapse sidebar"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </header>

          {statItems.length > 0 && (
            <div className="schematic-sidebar-summary">
              <div className="schematic-sidebar-summary-title">Sheet Summary</div>
              {statItems.map((item) => (
                <div className="schematic-summary-row" key={item.label}>
                  <item.icon size={14} className="schematic-summary-row-icon" />
                  <span className="schematic-summary-row-label">{item.label}</span>
                  <span className="schematic-summary-row-count">{item.value}</span>
                </div>
              ))}
            </div>
          )}

          <div className="schematic-sidebar-tabs">
            <button
              className={`schematic-sidebar-tab ${activeTab === 'structure' ? 'active' : ''}`}
              onClick={() => updateTab('structure')}
            >
              <GitBranch size={14} />
              <span>Structure</span>
            </button>
            <button
              className={`schematic-sidebar-tab ${activeTab === 'selection' ? 'active' : ''}`}
              onClick={() => updateTab('selection')}
            >
              <Target size={14} />
              <span>Selection</span>
            </button>
          </div>

          <div className="schematic-sidebar-content">
            {activeTab === 'structure' ? (
              <StructureTree />
            ) : hasSelection ? (
              <SelectionDetails showTopBorder={false} />
            ) : (
              <div className="schematic-sidebar-empty">
                <div className="schematic-sidebar-empty-title">No item selected</div>
                <div className="schematic-sidebar-empty-copy">
                  Pick a symbol or net from the canvas to inspect attributes, connected nets, and
                  hierarchy context.
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
