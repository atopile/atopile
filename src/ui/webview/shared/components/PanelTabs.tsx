import './PanelTabs.css'

export interface PanelTab {
  key: string
  label: string
}

interface PanelTabsProps {
  tabs: PanelTab[]
  activeTab: string
  onTabChange: (key: string) => void
}

/**
 * Shared tab bar for sidebar panels (Packages, Parts, etc.).
 */
export function PanelTabs({ tabs, activeTab, onTabChange }: PanelTabsProps) {
  return (
    <div className="panel-tabs">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          className={`panel-tab${activeTab === tab.key ? ' active' : ''}`}
          onClick={() => onTabChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
