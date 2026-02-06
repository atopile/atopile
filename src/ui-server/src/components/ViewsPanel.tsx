/**
 * Views panel - Launcher for all design visualizers.
 *
 * Provides quick access to pop-out viewers (Power Tree, I2C Tree,
 * Layout, 3D Model) and the inline Structure panel.
 */

import { useState } from 'react'
import {
  Zap,
  GitBranch,
  LayoutGrid,
  Box,
  Cpu,
  Eye,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from 'lucide-react'
import { postToExtension } from '../api/vscodeApi'
import { StructurePanel } from './StructurePanel'
import type { Project } from '../types/build'
import './ViewsPanel.css'

interface ViewerItem {
  id: string
  label: string
  icon: React.ReactNode
  description: string
  messageType: string
  available: boolean
  badge?: string
}

interface ViewsPanelProps {
  activeFilePath: string | null
  lastAtoFile: string | null
  projects: Project[]
  onRefreshStructure: () => void
  isExpanded?: boolean
  hasActiveProject: boolean
}

export function ViewsPanel({
  activeFilePath,
  lastAtoFile,
  projects,
  onRefreshStructure,
  isExpanded,
  hasActiveProject,
}: ViewsPanelProps) {
  const [structureExpanded, setStructureExpanded] = useState(true)

  const viewers: ViewerItem[] = [
    {
      id: 'powerTree',
      label: 'Power Tree',
      icon: <Zap size={14} />,
      description: 'Power supply hierarchy and current flow',
      messageType: 'openPowerTree',
      available: hasActiveProject,
    },
    {
      id: 'i2cTree',
      label: 'I2C Tree',
      icon: <GitBranch size={14} />,
      description: 'I2C bus topology with addresses',
      messageType: 'openI2CTree',
      available: hasActiveProject,
    },
    {
      id: 'layout',
      label: 'Layout',
      icon: <LayoutGrid size={14} />,
      description: 'PCB layout preview',
      messageType: 'openLayoutPreview',
      available: hasActiveProject,
    },
    {
      id: '3d',
      label: '3D Model',
      icon: <Box size={14} />,
      description: '3D board preview',
      messageType: 'open3DPreview',
      available: hasActiveProject,
    },
    {
      id: 'pinout',
      label: 'Pinout',
      icon: <Cpu size={14} />,
      description: 'IC pinout visualization with bus highlighting',
      messageType: 'openPinoutExplorer',
      available: hasActiveProject,
    },
  ]

  const handleOpenViewer = (viewer: ViewerItem) => {
    if (!viewer.available) return
    postToExtension({ type: viewer.messageType })
  }

  return (
    <div className="views-panel">
      {/* Viewer launchers */}
      <div className="views-launchers">
        <div className="views-section-header">
          <Eye size={12} />
          <span>Viewers</span>
        </div>
        {viewers.map((viewer) => (
          <button
            key={viewer.id}
            className={`views-launcher-row ${!viewer.available ? 'disabled' : ''}`}
            onClick={() => handleOpenViewer(viewer)}
            title={viewer.description}
          >
            <span className="views-launcher-icon">{viewer.icon}</span>
            <span className="views-launcher-label">{viewer.label}</span>
            <ExternalLink size={10} className="views-launcher-external" />
          </button>
        ))}
      </div>

      {/* Structure (inline, collapsible) */}
      <div className="views-structure-section">
        <button
          className="views-section-header clickable"
          onClick={() => setStructureExpanded(!structureExpanded)}
        >
          {structureExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <span>Structure</span>
        </button>
        {structureExpanded && (
          <div className="views-structure-content">
            <StructurePanel
              activeFilePath={activeFilePath}
              lastAtoFile={lastAtoFile}
              projects={projects}
              onRefreshStructure={onRefreshStructure}
              isExpanded={isExpanded}
            />
          </div>
        )}
      </div>
    </div>
  )
}
