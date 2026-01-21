import { useState, useEffect } from 'react'
import { Search, Plus } from 'lucide-react'
import { type ProjectDependency } from './DependencyCard'
import { type FileTreeNode } from './FileExplorer'
import { PackageCard } from './PackageCard'
import { ProjectNode } from './ProjectNode'
import type {
  Selection,
  BuildTarget,
  Project,
  ModuleDefinition,
  AvailableProject,
  SelectedPackage
} from './projectsTypes'

// Types are now imported from ./projectsTypes

// Mock data - simulating a workspace with multiple projects/packages
// Exported for use in other components (BuildSelector, etc.)
export const mockProjects: Project[] = [
  {
    id: 'my-board',
    name: 'my-board',
    type: 'project',
    root: '~/projects/my-board',
    summary: 'Main development board with sensors and connectivity',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'main.ato:App',
        status: 'success',
        warnings: 2,
        duration: 3.4,
        stages: [
          { name: 'Parse', status: 'success', duration: 0.12 },
          { name: 'Type Check', status: 'warning', duration: 0.45, message: '1 warning' },
          { name: 'Solve Constraints', status: 'warning', duration: 1.8, message: '2 warnings' },
          { name: 'Pick Parts', status: 'success', duration: 0.65 },
          { name: 'Generate Netlist', status: 'success', duration: 0.18 },
          { name: 'Export KiCad', status: 'success', duration: 0.2 },
        ],
        symbols: [
          {
            name: 'App',
            type: 'module',
            path: 'main.ato:App',
            children: [
              { name: 'power_supply', type: 'module', path: 'main.ato:App.power_supply' },
              { name: 'mcu', type: 'module', path: 'main.ato:App.mcu', hasWarnings: true },
              { name: 'sensors', type: 'module', path: 'main.ato:App.sensors' },
              { name: 'amplifier', type: 'module', path: 'main.ato:App.amplifier' },
            ]
          }
        ]
      },
      {
        id: 'debug',
        name: 'debug',
        entry: 'main.ato:DebugBoard',
        status: 'error',
        errors: 3,
        warnings: 1,
        duration: 2.1,
        stages: [
          { name: 'Parse', status: 'success', duration: 0.08 },
          { name: 'Type Check', status: 'error', duration: 0.32, message: '3 type errors' },
          { name: 'Solve Constraints', status: 'skipped' },
          { name: 'Pick Parts', status: 'skipped' },
          { name: 'Generate Netlist', status: 'skipped' },
          { name: 'Export KiCad', status: 'skipped' },
        ],
        symbols: [
          {
            name: 'DebugBoard',
            type: 'module',
            path: 'main.ato:DebugBoard',
            hasErrors: true,
            children: [
              { name: 'debug_leds', type: 'module', path: 'main.ato:DebugBoard.debug_leds', hasErrors: true },
              { name: 'test_points', type: 'module', path: 'main.ato:DebugBoard.test_points' },
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'sensor-hub',
    name: 'sensor-hub',
    type: 'project',
    root: '~/projects/sensor-hub',
    summary: 'Multi-sensor aggregation board with I2C hub',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'sensor-hub.ato:SensorHub',
        status: 'success',
        duration: 2.1,
        symbols: [
          {
            name: 'SensorHub',
            type: 'module',
            path: 'sensor-hub.ato:SensorHub',
            children: [
              { name: 'bme280', type: 'module', path: 'sensor-hub.ato:SensorHub.bme280' },
              { name: 'accelerometer', type: 'module', path: 'sensor-hub.ato:SensorHub.accelerometer' },
              { name: 'i2c_hub', type: 'interface', path: 'sensor-hub.ato:SensorHub.i2c_hub' },
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'power-module',
    name: 'power-module',
    type: 'project',
    root: '~/projects/power-module',
    summary: 'High-efficiency power supply with USB-C input',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'power-module.ato:PowerSupply',
        status: 'success',
        duration: 1.8,
        symbols: [
          {
            name: 'PowerSupply',
            type: 'module',
            path: 'power-module.ato:PowerSupply',
            children: [
              { name: 'buck_3v3', type: 'module', path: 'power-module.ato:PowerSupply.buck_3v3' },
              { name: 'ldo_1v8', type: 'module', path: 'power-module.ato:PowerSupply.ldo_1v8' },
              { name: 'usb_input', type: 'interface', path: 'power-module.ato:PowerSupply.usb_input' },
            ]
          }
        ]
      },
      {
        id: 'high-power',
        name: 'high-power',
        entry: 'power-module.ato:HighPowerSupply',
        status: 'warning',
        warnings: 1,
        duration: 2.3,
        symbols: [
          {
            name: 'HighPowerSupply',
            type: 'module',
            path: 'power-module.ato:HighPowerSupply',
            hasWarnings: true,
          }
        ]
      }
    ]
  },
  // Real packages from the packages repo with actual summaries
  {
    id: 'atopile/bosch-bme280',
    name: 'bosch-bme280',
    type: 'package',
    root: 'packages/bosch-bme280',
    version: '0.1.2',
    latestVersion: '0.2.0',  // Update available!
    installed: true,
    publisher: 'atopile',
    summary: 'Temperature, humidity & pressure sensor with I2C',
    description: 'Bosch BME280 environmental sensor. Measures temperature (-40 to +85°C), humidity (0-100%), and barometric pressure (300-1100 hPa).',
    keywords: ['temperature', 'humidity', 'pressure', 'sensor', 'i2c', 'weather', 'environmental', 'bosch', 'adafruit', 'qwiic', 'stemma'],
    homepage: 'https://packages.atopile.io/atopile/bosch-bme280',
    repository: 'https://github.com/atopile/packages/tree/main/packages/bosch-bme280',
    downloads: 12847,
    versionCount: 8,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'bosch-bme280.ato:Bosch_BME280',
        status: 'success',
        duration: 0.9,
        symbols: [
          { 
            name: 'Bosch_BME280', 
            type: 'module', 
            path: 'bosch-bme280.ato:Bosch_BME280',
            children: [
              { name: 'i2c', type: 'interface', path: 'bosch-bme280.ato:Bosch_BME280.i2c' },
              { name: 'power', type: 'interface', path: 'bosch-bme280.ato:Bosch_BME280.power' },
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'atopile/espressif-esp32-s3',
    name: 'espressif-esp32-s3',
    type: 'package',
    root: 'packages/espressif-esp32-s3',
    version: '0.1.0',
    latestVersion: '0.1.3',  // Newer version available
    installed: true,
    publisher: 'atopile',
    summary: 'ESP32-S3 WiFi+BLE module with touch support',
    description: 'Espressif ESP32-S3-WROOM module. Dual-core 240MHz, WiFi 802.11 b/g/n, Bluetooth 5.0 LE, 512KB SRAM, AI acceleration.',
    keywords: ['esp32', 'wifi', 'bluetooth', 'ble', 'microcontroller', 'mcu', 'iot', 'espressif', 'wireless'],
    homepage: 'https://packages.atopile.io/atopile/espressif-esp32-s3',
    repository: 'https://github.com/atopile/packages/tree/main/packages/espressif-esp32-s3',
    downloads: 8432,
    versionCount: 4,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'espressif-esp32-s3.ato:Espressif_ESP32_S3',
        status: 'success',
        duration: 2.1,
        symbols: [
          {
            name: 'Espressif_ESP32_S3',
            type: 'module',
            path: 'espressif-esp32-s3.ato:Espressif_ESP32_S3',
            children: [
              { name: 'power_3v3', type: 'interface', path: 'espressif-esp32-s3.ato:Espressif_ESP32_S3.power_3v3' },
              { name: 'usb', type: 'interface', path: 'espressif-esp32-s3.ato:Espressif_ESP32_S3.usb' },
              { name: 'uart', type: 'interface', path: 'espressif-esp32-s3.ato:Espressif_ESP32_S3.uart' },
              { name: 'spi', type: 'interface', path: 'espressif-esp32-s3.ato:Espressif_ESP32_S3.spi' },
              { name: 'i2c', type: 'interface', path: 'espressif-esp32-s3.ato:Espressif_ESP32_S3.i2c' },
              { name: 'gpio', type: 'interface', path: 'espressif-esp32-s3.ato:Espressif_ESP32_S3.gpio' },
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'atopile/ti-tlv75901',
    name: 'ti-tlv75901',
    type: 'package',
    root: 'packages/ti-tlv75901',
    version: '0.2.0',
    installed: false,
    publisher: 'atopile',
    summary: '300mA LDO voltage regulator, ultra-low noise',
    description: 'Texas Instruments TLV75901 low-dropout linear regulator. 300mA output, 1.5-6.0V input, ultra-low noise (6.5µVRMS), fast transient response.',
    keywords: ['ldo', 'regulator', 'voltage', 'power', 'linear', 'ti', 'texas instruments', 'low noise', '3.3v', '1.8v'],
    downloads: 5621,
    versionCount: 6,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'ti-tlv75901.ato:TI_TLV75901',
        status: 'success',
        duration: 0.5,
        symbols: [
          { name: 'TI_TLV75901', type: 'module', path: 'ti-tlv75901.ato:TI_TLV75901' }
        ]
      }
    ]
  },
  {
    id: 'atopile/adi-adxl345',
    name: 'adi-adxl345',
    type: 'package',
    root: 'packages/adi-adxl345',
    version: '0.1.2',
    installed: false,
    publisher: 'atopile',
    summary: '3-axis digital accelerometer, I2C/SPI',
    description: 'Analog Devices ADXL345 MEMS accelerometer. ±2g/4g/8g/16g range, 13-bit resolution, I2C and SPI interface, tap/double-tap detection.',
    keywords: ['accelerometer', 'motion', 'sensor', 'mems', 'i2c', 'spi', 'adi', 'analog devices', 'imu', 'tilt'],
    downloads: 3215,
    versionCount: 3,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'adi-adxl345.ato:ADI_ADXL345',
        status: 'warning',
        warnings: 1,
        duration: 0.7,
        symbols: [
          { name: 'ADI_ADXL345', type: 'module', path: 'adi-adxl345.ato:ADI_ADXL345', hasWarnings: true }
        ]
      }
    ]
  },
  {
    id: 'atopile/mps-mp2155',
    name: 'mps-mp2155',
    type: 'package',
    root: 'packages/mps-mp2155',
    version: '0.1.0',
    installed: false,
    publisher: 'atopile',
    summary: '1A synchronous step-down converter',
    description: 'MPS MP2155 buck converter. 1A output, 4.5-16V input, 600kHz switching, integrated MOSFETs, high efficiency.',
    keywords: ['buck', 'converter', 'regulator', 'voltage', 'power', 'switching', 'dcdc', 'mps', 'step-down', 'smps'],
    downloads: 1847,
    versionCount: 2,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'mps-mp2155.ato:MPS_MP2155',
        status: 'idle',
      }
    ]
  },
  {
    id: 'atopile/buttons',
    name: 'buttons',
    type: 'package',
    root: 'packages/buttons',
    version: '0.4.0',
    latestVersion: '0.5.1',  // Update available!
    installed: true,
    publisher: 'atopile',
    summary: 'Tactile push buttons with debounce',
    description: 'Tactile push buttons with optional hardware debounce circuit. Multiple footprint options available.',
    keywords: ['button', 'switch', 'tactile', 'push', 'debounce', 'input', 'ui', 'user interface'],
    downloads: 9823,
    versionCount: 12,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'buttons.ato:Button',
        status: 'success',
        duration: 0.4,
        symbols: [
          { name: 'Button', type: 'module', path: 'buttons.ato:Button' },
          { name: 'DebouncedButton', type: 'module', path: 'buttons.ato:DebouncedButton' },
        ]
      }
    ]
  },
  {
    id: 'atopile/indicator-leds',
    name: 'indicator-leds',
    type: 'package',
    root: 'packages/indicator-leds',
    version: '0.2.5',
    installed: true,
    publisher: 'atopile',
    summary: 'LED indicators with current limiting',
    description: 'LED indicators with integrated current-limiting resistors. Single color and RGB options.',
    keywords: ['led', 'indicator', 'light', 'rgb', 'status', 'display', 'output'],
    downloads: 15432,
    versionCount: 9,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'indicator-leds.ato:LED_Indicator',
        status: 'success',
        duration: 0.3,
        symbols: [
          { name: 'LED_Indicator', type: 'module', path: 'indicator-leds.ato:LED_Indicator' },
          { name: 'RGB_LED', type: 'module', path: 'indicator-leds.ato:RGB_LED' },
        ]
      }
    ]
  },
  {
    id: 'atopile/infineon-dps310',
    name: 'infineon-dps310',
    type: 'package',
    root: 'packages/infineon-dps310',
    version: '0.1.0',
    installed: false,
    publisher: 'atopile',
    summary: 'Barometric pressure sensor, high precision',
    description: 'Infineon DPS310 digital barometric pressure sensor. ±0.002 hPa precision, altitude tracking, I2C/SPI interface.',
    keywords: ['pressure', 'barometric', 'altitude', 'sensor', 'i2c', 'spi', 'infineon', 'weather'],
    downloads: 2156,
    versionCount: 2,
    license: 'MIT',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'infineon-dps310.ato:Infineon_DPS310',
        status: 'idle',
      }
    ]
  },
  // Community package example
  {
    id: 'community/rp2040-pico',
    name: 'rp2040-pico',
    type: 'package',
    root: 'packages/rp2040-pico',
    version: '0.3.1',
    installed: false,
    publisher: 'community',
    summary: 'Raspberry Pi Pico RP2040 module',
    description: 'Community-maintained Raspberry Pi Pico with RP2040 dual-core ARM Cortex-M0+, 264KB SRAM, USB 1.1.',
    keywords: ['rp2040', 'pico', 'raspberry pi', 'arm', 'microcontroller', 'mcu', 'usb', 'community'],
    downloads: 4521,
    versionCount: 7,
    license: 'Apache-2.0',
    builds: [
      {
        id: 'default',
        name: 'default',
        entry: 'rp2040-pico.ato:RP2040_Pico',
        status: 'idle',
      }
    ]
  },
]

// Types AvailableProject, SelectedPackage imported from ./projectsTypes
// Helper functions getTypeIcon, getStatusIcon imported from components

interface ProjectsPanelProps {
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void  // Cancel a running build
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  onOpenPackageDetail?: (pkg: SelectedPackage) => void
  onPackageInstall?: (packageId: string, targetProjectRoot: string) => void
  onCreateProject?: (parentDirectory?: string, name?: string) => void  // Creates a new project
  onProjectExpand?: (projectRoot: string) => void  // Called when a project is expanded (for module fetching)
  onOpenSource?: (projectId: string, entry: string) => void  // Open source file (ato button)
  onOpenKiCad?: (projectId: string, buildId: string) => void  // Open in KiCad
  onOpenLayout?: (projectId: string, buildId: string) => void  // Open layout preview
  onOpen3D?: (projectId: string, buildId: string) => void  // Open 3D viewer
  onFileClick?: (projectId: string, filePath: string) => void  // Open a file in the editor
  onDependencyVersionChange?: (projectId: string, identifier: string, newVersion: string) => void  // Change dependency version
  onRemoveDependency?: (projectId: string, identifier: string) => void  // Remove a dependency
  onDeleteBuild?: (projectId: string, buildId: string) => void  // Delete a build target
  filterType?: 'all' | 'projects' | 'packages'
  projects?: Project[]  // Optional - if not provided, uses mockProjects
  projectModules?: Record<string, ModuleDefinition[]>  // Modules for each project root
  projectFiles?: Record<string, FileTreeNode[]>  // File tree for each project root
  projectDependencies?: Record<string, ProjectDependency[]>  // Dependencies for each project root
}

export function ProjectsPanel({ selection, onSelect, onBuild, onCancelBuild, onStageFilter, onOpenPackageDetail, onPackageInstall, onCreateProject, onProjectExpand, onOpenSource, onOpenKiCad, onOpenLayout, onOpen3D, onFileClick, onDependencyVersionChange, onRemoveDependency, onDeleteBuild, filterType = 'all', projects: externalProjects, projectModules = {}, projectFiles = {}, projectDependencies = {} }: ProjectsPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedProjectId, setExpandedProjectId] = useState<string | null>(null)
  const [localProjects, setLocalProjects] = useState<Project[]>(externalProjects || mockProjects)
  
  // Update local projects when external projects change
  useEffect(() => {
    if (externalProjects && externalProjects.length > 0) {
      setLocalProjects(externalProjects)
    }
  }, [externalProjects])
  
  // Handler to add a new project
  const handleAddProject = () => {
    // If callback is provided, use it (real implementation)
    if (onCreateProject) {
      onCreateProject()
      return
    }

    // Fallback to mock implementation for dev/testing
    const newId = `new-project-${Date.now()}`
    const newProject: Project = {
      id: newId,
      name: 'new-project',
      type: 'project',
      root: `~/projects/${newId}`,
      summary: '',
      builds: [
        {
          id: 'default',
          name: 'default',
          entry: 'main.ato:App',
          status: 'idle',
          symbols: [
            {
              name: 'App',
              type: 'module',
              path: 'App'
            }
          ],
          stages: []
        }
      ]
    }
    setLocalProjects([newProject, ...localProjects])
    setExpandedProjectId(newId)
    onSelect({
      type: 'project',
      projectId: newId,
      label: newProject.name
    })
  }
  
  // Handler to update a project
  const handleUpdateProject = (projectId: string, updates: Partial<Project>) => {
    setLocalProjects(projects => 
      projects.map(p => p.id === projectId ? { ...p, ...updates } : p)
    )
  }
  
  // Handler to add a new build to a project
  const handleAddBuild = (projectId: string) => {
    const newBuildId = `build-${Date.now()}`
    setLocalProjects(projects => 
      projects.map(p => {
        if (p.id === projectId) {
          // Find the next available "new-build-N" number
          const existingNewBuilds = p.builds
            .map(b => b.name)
            .filter(name => /^new-build-\d+$/.test(name))
            .map(name => parseInt(name.replace('new-build-', ''), 10))
          const nextNum = existingNewBuilds.length > 0 
            ? Math.max(...existingNewBuilds) + 1 
            : 1
          const newBuildName = `new-build-${nextNum}`
          
          return {
            ...p,
            builds: [
              ...p.builds,
              {
                id: newBuildId,
                name: newBuildName,
                entry: 'main.ato:App',
                status: 'idle' as const,
                symbols: [],
                stages: []
              }
            ]
          }
        }
        return p
      })
    )
  }
  
  // Handler to update a build
  const handleUpdateBuild = (projectId: string, buildId: string, updates: Partial<BuildTarget>) => {
    setLocalProjects(projects =>
      projects.map(p => {
        if (p.id === projectId) {
          return {
            ...p,
            builds: p.builds.map(b =>
              b.id === buildId ? { ...b, ...updates } : b
            )
          }
        }
        return p
      })
    )
  }

  // Handler to delete a build
  const handleDeleteBuild = (projectId: string, buildId: string) => {
    // If external callback is provided, use it
    if (onDeleteBuild) {
      onDeleteBuild(projectId, buildId)
      return
    }

    // Fallback local state update for development/testing
    setLocalProjects(projects =>
      projects.map(p => {
        if (p.id === projectId) {
          return {
            ...p,
            builds: p.builds.filter(b => b.id !== buildId)
          }
        }
        return p
      })
    )

    // Clear selection if the deleted build was selected
    if (selection.type === 'build' && selection.buildId === `${projectId}:${buildId}`) {
      onSelect({ type: 'none' })
    }
  }
  
  // Create available projects list for install dropdown (only actual projects, not packages)
  const availableProjects: AvailableProject[] = localProjects
    .filter(p => p.type === 'project')
    .map((p, idx) => ({
      id: p.id,
      name: p.name,
      path: p.root,
      isActive: idx === 0  // First project is active by default
    }))
  
  // Handle install action
  const handleInstall = (packageId: string, targetProjectId: string) => {
    console.log(`Installing ${packageId} to ${targetProjectId}`)
    if (onPackageInstall) {
      // Find the project root for the target project
      const targetProject = localProjects.find(p => p.id === targetProjectId)
      const projectRoot = targetProject?.root || targetProjectId
      onPackageInstall(packageId, projectRoot)
    } else {
      // Fallback for development/testing
      alert(`Installing ${packageId} to ${targetProjectId}`)
    }
  }
  
  // Filter projects based on external filterType prop
  const filteredProjects = localProjects.filter(project => {
    // Filter by type
    if (filterType === 'projects' && project.type !== 'project') return false
    if (filterType === 'packages' && project.type !== 'package') return false
    
    
    // Filter by search - include name, description, summary, and keywords
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const searchableText = [
        project.name,
        project.id,
        project.publisher || '',
        project.description || '',
        project.summary || '',
        ...(project.keywords || [])
      ].join(' ').toLowerCase()
      
      return searchableText.includes(query)
    }
    
    return true
  })

  const placeholder = filterType === 'packages' 
    ? 'Search packages (e.g. "regulator", "sensor")...' 
    : 'Search projects...'

  return (
    <div className="projects-panel">
      {/* Search */}
      <div className="projects-toolbar">
        <div className="search-box">
          <Search size={12} />
          <input
            type="text"
            placeholder={placeholder}
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              // Clear selection and collapse expanded project when user starts typing
              if (e.target.value) {
                if (selection.type !== 'none') {
                  onSelect({ type: 'none' })
                }
                // Collapse any expanded project so search results show all matches
                if (expandedProjectId !== null) {
                  setExpandedProjectId(null)
                }
              }
            }}
          />
        </div>
        
        {/* Add new project button (only for projects) */}
        {filterType === 'projects' && (
          <button 
            className="add-project-btn"
            onClick={handleAddProject}
            title="Create new project"
          >
            <Plus size={14} />
          </button>
        )}
        
      </div>
      
      {/* Project/Package list */}
      <div className="projects-tree">
        {filteredProjects
          .filter(project => {
            // For projects panel: hide other projects when one is expanded
            if (filterType === 'projects' && expandedProjectId !== null) {
              return project.id === expandedProjectId
            }
            return true
          })
          .map(project => (
          project.type === 'package' ? (
            <PackageCard
              key={project.id}
              project={project}
              selection={selection}
              onSelect={onSelect}
              onBuild={onBuild}
              onCancelBuild={onCancelBuild}
              onStageFilter={onStageFilter}
              onOpenPackageDetail={onOpenPackageDetail}
              onInstall={handleInstall}
              onOpenSource={onOpenSource}
              onOpenKiCad={onOpenKiCad}
              onOpenLayout={onOpenLayout}
              onOpen3D={onOpen3D}
              availableProjects={availableProjects}
            />
          ) : (
            <ProjectNode
              key={project.id}
              project={project}
              selection={selection}
              onSelect={onSelect}
              onBuild={onBuild}
              onCancelBuild={onCancelBuild}
              onStageFilter={onStageFilter}
              onOpenPackageDetail={onOpenPackageDetail}
              isExpanded={expandedProjectId === project.id}
              onExpandChange={(projectId, expanded) => {
                setExpandedProjectId(expanded ? projectId : null)
              }}
              onUpdateProject={handleUpdateProject}
              onAddBuild={handleAddBuild}
              onUpdateBuild={handleUpdateBuild}
              onDeleteBuild={handleDeleteBuild}
              onProjectExpand={onProjectExpand}
              onOpenSource={onOpenSource}
              onOpenKiCad={onOpenKiCad}
              onOpenLayout={onOpenLayout}
              onOpen3D={onOpen3D}
              onFileClick={onFileClick}
              onDependencyVersionChange={onDependencyVersionChange}
              onRemoveDependency={onRemoveDependency}
              availableModules={projectModules[project.root] || []}
              projectFiles={projectFiles[project.root] || []}
              projectDependencies={projectDependencies[project.root] || []}
            />
          )
        ))}
        
        {filteredProjects.length === 0 && (
          <div className="empty-state">
            <span>No {filterType === 'packages' ? 'packages' : 'projects'} found</span>
            {searchQuery && filterType === 'packages' && (
              <span className="empty-hint">Try searching for "sensor", "regulator", or "mcu"</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
