import { useMemo, useState, type CSSProperties } from 'react';
import {
  Cable,
  ChevronRight,
  Cpu,
  GitBranch,
  Layout,
  Target,
} from 'lucide-react';
import { useTheme } from '../lib/theme';
import { useCurrentSheet, useSchematicStore } from '../stores/schematicStore';
import type { SchematicBOMData, SchematicVariablesData } from '../types/artifacts';
import { componentColor, moduleColor, netTypeColor } from './SymbolInspector';
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
  onSetCollapsed: (collapsed: boolean) => void;
  bomData?: SchematicBOMData | null;
  variablesData?: SchematicVariablesData | null;
}

export function SchematicSidebar({
  width,
  onSetCollapsed,
  bomData = null,
  variablesData = null,
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
      {
        label: 'Modules',
        value: sheet.modules.length,
        icon: Layout,
        accent: moduleColor('sensor'),
      },
      {
        label: 'Components',
        value: sheet.components.length,
        icon: Cpu,
        accent: componentColor('R'),
      },
      {
        label: 'Nets',
        value: sheet.nets.length,
        icon: Cable,
        accent: netTypeColor('bus', theme),
      },
    ];
  }, [sheet, theme]);

  const cssVars = {
    '--sv-bg': theme.bgSecondary,
    '--sv-bg-elev': theme.bgTertiary,
    '--sv-border': theme.borderColor,
    '--sv-hover': theme.bgHover,
    '--sv-text': theme.textPrimary,
    '--sv-muted': theme.textMuted,
    '--sv-secondary': theme.textSecondary,
    '--sv-accent': theme.accent,
    '--sv-mono': 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace)',
  } as React.CSSProperties;

  const updateTab = (tab: SidebarTab) => {
    setActiveTab(tab);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(TAB_STORAGE_KEY, tab);
    }
  };

  return (
    <aside
      className="schematic-sidebar"
      style={{ ...cssVars, width }}
    >
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
            <div
              className="schematic-summary-row"
              key={item.label}
              style={{ '--summary-accent': item.accent } as CSSProperties}
            >
              <span className="schematic-summary-row-icon-wrap">
                <item.icon size={13} className="schematic-summary-row-icon" />
              </span>
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
          style={{ '--tab-accent': moduleColor('sensor') } as CSSProperties}
        >
          <GitBranch size={14} className="schematic-sidebar-tab-icon" />
          <span>Structure</span>
        </button>
        <button
          className={`schematic-sidebar-tab ${activeTab === 'selection' ? 'active' : ''}`}
          onClick={() => updateTab('selection')}
          style={{ '--tab-accent': componentColor('R') } as CSSProperties}
        >
          <Target size={14} className="schematic-sidebar-tab-icon" />
          <span>Selection</span>
        </button>
      </div>

      <div className="schematic-sidebar-content">
        {activeTab === 'structure' ? (
          <StructureTree />
        ) : hasSelection ? (
          <SelectionDetails
            showTopBorder={false}
            bomData={bomData}
            variablesData={variablesData}
          />
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
    </aside>
  );
}
