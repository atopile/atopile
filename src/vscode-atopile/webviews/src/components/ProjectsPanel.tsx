import { useState, useRef, useEffect, memo } from 'react'
import {
  ChevronDown, ChevronRight, Play, Layers, Package,
  FileCode, Box, Zap, Cpu, CircuitBoard, Check, X,
  AlertTriangle, AlertCircle, Search, Download,
  Plus, ArrowUpCircle, Grid3X3, Layout, Cuboid,
  Clock, SkipForward, Circle, Scale, History, Github, Globe, Square,
  Folder, FolderOpen, FileText
} from 'lucide-react'

// Selection type
interface Selection {
  type: 'none' | 'project' | 'build' | 'symbol'
  projectId?: string
  buildId?: string
  symbolPath?: string
  label?: string
}

// Symbol in a build
interface BuildSymbol {
  name: string
  type: 'module' | 'interface' | 'component' | 'parameter'
  path: string
  children?: BuildSymbol[]
  hasErrors?: boolean
  hasWarnings?: boolean
}

// Build stage timing
interface BuildStage {
  name: string
  displayName?: string  // User-friendly name
  status: 'pending' | 'running' | 'success' | 'warning' | 'error' | 'skipped'
  duration?: number  // in seconds (from summary)
  elapsedSeconds?: number  // in seconds (from live status)
  message?: string
}

// Timer component for running stages - isolated to prevent parent re-renders
// Uses 1 second interval instead of 100ms for better performance
function StageTimer() {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setSeconds(s => s + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  return <>{seconds}s</>
}

// Last build status (persisted)
interface LastBuildStatus {
  status: 'success' | 'warning' | 'failed' | 'error'
  timestamp: string  // ISO timestamp
  elapsedSeconds?: number
  warnings: number
  errors: number
  stages?: BuildStage[]
}

// Build target
interface BuildTarget {
  id: string
  name: string
  entry: string
  status: 'idle' | 'queued' | 'building' | 'success' | 'error' | 'warning' | 'cancelled'
  errors?: number
  warnings?: number
  duration?: number
  symbols?: BuildSymbol[]
  stages?: BuildStage[]
  // Active build tracking
  buildId?: string  // Active build ID for cancellation
  elapsedSeconds?: number  // Time elapsed since build started
  currentStage?: string  // Name of the currently running stage
  queuePosition?: number  // Position in build queue (1-indexed)
  // Persisted last build status
  lastBuild?: LastBuildStatus
}

// Project (or package)
interface Project {
  id: string
  name: string
  type: 'project' | 'package'
  path: string
  version?: string
  latestVersion?: string  // Latest available version (for update checking)
  installed?: boolean
  builds: BuildTarget[]
  description?: string
  summary?: string  // Short summary/tags from ato.yaml
  homepage?: string
  repository?: string
  keywords?: string[]  // For better searching
  publisher?: string  // Publisher/author of the package (e.g., 'atopile', 'community')
  // Package stats
  downloads?: number     // All-time downloads
  versionCount?: number  // Number of published versions
  license?: string       // License type (e.g., 'MIT', 'Apache-2.0')
  // Project-level last build status (aggregate of all targets)
  lastBuildStatus?: 'success' | 'warning' | 'failed' | 'error'
  lastBuildTimestamp?: string  // Most recent build across all targets
}

// Mock data - simulating a workspace with multiple projects/packages
// Exported for use in other components (BuildSelector, etc.)
export const mockProjects: Project[] = [
  {
    id: 'my-board',
    name: 'my-board',
    type: 'project',
    path: '~/projects/my-board',
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
    path: '~/projects/sensor-hub',
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
    path: '~/projects/power-module',
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
    path: 'packages/bosch-bme280',
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
    path: 'packages/espressif-esp32-s3',
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
    path: 'packages/ti-tlv75901',
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
    path: 'packages/adi-adxl345',
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
    path: 'packages/mps-mp2155',
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
    path: 'packages/buttons',
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
    path: 'packages/indicator-leds',
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
    path: 'packages/infineon-dps310',
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
    path: 'packages/rp2040-pico',
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

// Type for available projects in install dropdown
interface AvailableProject {
  id: string
  name: string
  path: string
  isActive: boolean
}

function getTypeIcon(type: BuildSymbol['type'], size: number = 12) {
  switch (type) {
    case 'module':
      return <Box size={size} className="type-icon module" />
    case 'interface':
      return <Zap size={size} className="type-icon interface" />
    case 'component':
      return <Cpu size={size} className="type-icon component" />
    case 'parameter':
      return <CircuitBoard size={size} className="type-icon parameter" />
  }
}

function getStatusIcon(status: BuildTarget['status'], size: number = 12, queuePosition?: number) {
  switch (status) {
    case 'building':
      return <Circle size={size} className="status-icon building" />
    case 'queued':
      return (
        <span className="status-icon queued" title={queuePosition ? `Queue position: ${queuePosition}` : 'Queued'}>
          <Clock size={size} />
          {queuePosition && <span className="queue-position">{queuePosition}</span>}
        </span>
      )
    case 'success':
      return <Check size={size} className="status-icon success" />
    case 'error':
      return <X size={size} className="status-icon error" />
    case 'warning':
      return <AlertTriangle size={size} className="status-icon warning" />
    default:
      return <div className="status-dot idle" />
  }
}

interface SelectedPackage {
  name: string
  fullName: string
  version?: string
  description?: string
  installed?: boolean
  availableVersions?: { version: string; released: string }[]
  homepage?: string
  repository?: string
}

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
  filterType?: 'all' | 'projects' | 'packages'
  projects?: Project[]  // Optional - if not provided, uses mockProjects
  projectModules?: Record<string, ModuleDefinition[]>  // Modules for each project root
  projectFiles?: Record<string, FileTreeNode[]>  // File tree for each project root
}

// Symbol node component - memoized to prevent unnecessary re-renders in lists
const SymbolNode = memo(function SymbolNode({ 
  symbol, 
  depth, 
  projectId,
  selection,
  onSelect,
  onBuild 
}: {
  symbol: BuildSymbol
  depth: number
  projectId: string
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [_hovered, setHovered] = useState(false)
  const hasChildren = symbol.children && symbol.children.length > 0
  const isSelected = selection.type === 'symbol' && selection.symbolPath === symbol.path
  
  return (
    <div className="symbol-node">
      <div 
        className={`symbol-row ${hasChildren ? 'expandable' : ''} ${isSelected ? 'selected' : ''}`}
        style={{ paddingLeft: `${depth * 4}px` }}
        onClick={() => {
          if (hasChildren) setExpanded(!expanded)
          onSelect({
            type: 'symbol',
            projectId,
            symbolPath: symbol.path,
            label: symbol.name
          })
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {hasChildren ? (
          <button className="tree-expand" onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}>
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
            e.stopPropagation()
            onBuild('symbol', symbol.path, symbol.name)
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
  )
})

// Get stage status icon
function getStageIcon(status: BuildStage['status'], size: number = 12) {
  switch (status) {
    case 'running':
      return <Circle size={size} className="stage-icon running" />
    case 'success':
      return <Check size={size} className="stage-icon success" />
    case 'warning':
      return <AlertTriangle size={size} className="stage-icon warning" />
    case 'error':
      return <X size={size} className="stage-icon error" />
    case 'skipped':
      return <SkipForward size={size} className="stage-icon skipped" />
    case 'pending':
    default:
      return <Circle size={size} className="stage-icon pending" />
  }
}

// Module definition from API
interface ModuleDefinition {
  name: string
  type: 'module' | 'interface' | 'component'
  file: string
  entry: string
  line?: number
  super_type?: string
}

// File tree node for file explorer
export interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'folder'
  extension?: string  // 'ato' | 'py'
  children?: FileTreeNode[]
}

// File icon component
function getFileIcon(extension: string | undefined, size: number = 12) {
  switch (extension) {
    case 'ato':
      return <FileCode size={size} className="file-icon ato" />
    case 'py':
      return <FileText size={size} className="file-icon python" />
    default:
      return <FileText size={size} className="file-icon" />
  }
}

// File tree node component - memoized for performance
const FileTreeNodeComponent = memo(function FileTreeNodeComponent({
  node,
  depth,
  onFileClick,
  defaultExpanded = false
}: {
  node: FileTreeNode
  depth: number
  onFileClick?: (path: string) => void
  defaultExpanded?: boolean
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const isFolder = node.type === 'folder'
  const hasChildren = isFolder && node.children && node.children.length > 0

  return (
    <div className="file-tree-node">
      <div
        className={`file-tree-row ${isFolder ? 'folder' : 'file'} ${node.extension || ''}`}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
        onClick={(e) => {
          e.stopPropagation()  // Prevent bubbling to parent card
          if (isFolder) {
            setExpanded(!expanded)
          } else if (onFileClick) {
            onFileClick(node.path)
          }
        }}
      >
        {isFolder ? (
          <>
            <span className="file-tree-expand">
              {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </span>
            {expanded ? (
              <FolderOpen size={14} className="folder-icon open" />
            ) : (
              <Folder size={14} className="folder-icon" />
            )}
          </>
        ) : (
          <>
            <span className="file-tree-spacer" />
            {getFileIcon(node.extension, 14)}
          </>
        )}
        <span className="file-tree-name">{node.name}</span>
      </div>
      {expanded && hasChildren && (
        <div className="file-tree-children">
          {[...node.children!]
            .sort((a, b) => {
              // Files come before folders
              if (a.type === 'file' && b.type === 'folder') return -1
              if (a.type === 'folder' && b.type === 'file') return 1
              // Then alphabetically by name
              return a.name.localeCompare(b.name)
            })
            .map((child) => (
              <FileTreeNodeComponent
                key={child.path}
                node={child}
                depth={depth + 1}
                onFileClick={onFileClick}
                defaultExpanded={false}
              />
            ))}
        </div>
      )}
    </div>
  )
})

// File Explorer component
const FileExplorer = memo(function FileExplorer({
  files,
  onFileClick
}: {
  files: FileTreeNode[]
  onFileClick?: (path: string) => void
}) {
  const [expanded, setExpanded] = useState(false)

  if (!files || files.length === 0) {
    return (
      <div className="file-explorer-empty">
        <span>No .ato or .py files found</span>
      </div>
    )
  }

  // Sort files before folders, then alphabetically
  const sortedFiles = [...files].sort((a, b) => {
    // Files come before folders
    if (a.type === 'file' && b.type === 'folder') return -1
    if (a.type === 'folder' && b.type === 'file') return 1
    // Then alphabetically by name
    return a.name.localeCompare(b.name)
  })

  return (
    <div className="file-explorer">
      <div
        className="file-explorer-header"
        onClick={(e) => {
          e.stopPropagation()
          setExpanded(!expanded)
        }}
      >
        <span className="file-explorer-chevron">
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <Folder size={12} />
        <span>Files</span>
      </div>
      {expanded && (
        <div className="file-explorer-tree">
          {sortedFiles.map((node) => (
            <FileTreeNodeComponent
              key={node.path}
              node={node}
              depth={0}
              onFileClick={onFileClick}
              defaultExpanded={false}
            />
          ))}
        </div>
      )}
    </div>
  )
})

// Format time in mm:ss or hh:mm:ss
function formatBuildTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// Parse timestamp that may be in format "YYYY-MM-DD_HH-MM-SS" or ISO format
function parseTimestamp(timestamp: string): Date {
  // Handle format "2026-01-20_09-27-03" -> "2026-01-20T09:27:03"
  const normalized = timestamp.replace(/_/g, 'T').replace(/-(\d{2})-(\d{2})$/, ':$1:$2')
  return new Date(normalized)
}

// Format relative time (e.g., "2m ago", "1h ago", "yesterday")
function formatRelativeTime(timestamp: string): string {
  const date = parseTimestamp(timestamp)
  if (isNaN(date.getTime())) return ''  // Invalid date

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

// Get status icon for last build (dimmed version)
function getLastBuildStatusIcon(status: string, size: number = 12) {
  switch (status) {
    case 'success':
      return <Check size={size} className="status-icon success dimmed" />
    case 'warning':
      return <AlertTriangle size={size} className="status-icon warning dimmed" />
    case 'error':
    case 'failed':
      return <AlertCircle size={size} className="status-icon error dimmed" />
    default:
      return <Circle size={size} className="status-icon idle dimmed" />
  }
}

// Build target card - similar to package cards
// Compact when not selected, expanded with details when selected
// Memoized to prevent unnecessary re-renders in lists
const BuildNode = memo(function BuildNode({
  build,
  projectId,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  onUpdateBuild,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  availableModules = []
}: {
  build: BuildTarget
  projectId: string
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  onUpdateBuild?: (projectId: string, buildId: string, updates: Partial<BuildTarget>) => void
  onOpenSource?: (projectId: string, entry: string) => void
  onOpenKiCad?: (projectId: string, buildId: string) => void
  onOpenLayout?: (projectId: string, buildId: string) => void
  onOpen3D?: (projectId: string, buildId: string) => void
  availableModules?: ModuleDefinition[]
}) {
  const [showStages, setShowStages] = useState(false)
  const [isEditingName, setIsEditingName] = useState(false)
  const [isEditingEntry, setIsEditingEntry] = useState(false)
  const [buildName, setBuildName] = useState(build.name)
  const [entryPoint, setEntryPoint] = useState(build.entry)
  const [searchQuery, setSearchQuery] = useState('')
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Timer state for live build time display
  const [elapsedTime, setElapsedTime] = useState(build.elapsedSeconds || 0)
  const isBuilding = build.status === 'building'

  // Track previous stage for animation
  const [prevStage, setPrevStage] = useState<string | null>(null)
  const [stageAnimating, setStageAnimating] = useState(false)

  // Update timer every second while building
  useEffect(() => {
    if (!isBuilding) {
      // Reset to the build's elapsed time when not building
      setElapsedTime(build.elapsedSeconds || build.duration || 0)
      return
    }

    // Start from the build's elapsed time
    setElapsedTime(build.elapsedSeconds || 0)

    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [isBuilding, build.elapsedSeconds, build.duration])

  // Calculate progress from stages
  // Use estimated total of 20 stages (typically ~19) since we don't know upfront
  // TODO: Once builds are defined in the graph, get actual stage count from backend
  const ESTIMATED_TOTAL_STAGES = 20
  const getProgress = () => {
    if (!build.stages || build.stages.length === 0) return 0
    const completed = build.stages.filter(s =>
      s.status === 'success' || s.status === 'warning' || s.status === 'error' || s.status === 'skipped'
    ).length
    const running = build.stages.filter(s => s.status === 'running').length
    // Add half credit for running stage, use estimated total for smoother progress
    const progress = ((completed + running * 0.5) / ESTIMATED_TOTAL_STAGES) * 100
    return Math.min(progress, 100) // Cap at 100% in case we exceed estimate
  }

  // Get current running stage name (use display_name if available)
  const getCurrentStage = () => {
    if (build.currentStage) return build.currentStage
    if (!build.stages) return null
    const running = build.stages.find(s => s.status === 'running')
    return running?.displayName || running?.name || null
  }

  // Trigger scroll-up animation when stage changes
  const currentStage = getCurrentStage()
  useEffect(() => {
    if (currentStage && currentStage !== prevStage) {
      setStageAnimating(true)
      setPrevStage(currentStage)
      // Reset animation after it completes
      const timer = setTimeout(() => setStageAnimating(false), 300)
      return () => clearTimeout(timer)
    }
  }, [currentStage, prevStage])

  // Filter modules based on search - only show modules (not interfaces)
  const filteredModules = availableModules
    .filter(m => m.type === 'module' || m.type === 'component')
    .filter(m => {
      if (!searchQuery) return true
      const query = searchQuery.toLowerCase()
      return (
        m.name.toLowerCase().includes(query) ||
        m.entry.toLowerCase().includes(query) ||
        m.file.toLowerCase().includes(query)
      )
    })

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isEditingEntry && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [isEditingEntry])

  const handleNameSave = () => {
    setIsEditingName(false)
    if (onUpdateBuild) {
      onUpdateBuild(projectId, build.id, { name: buildName })
    }
  }

  const handleEntrySearch = (value: string) => {
    setSearchQuery(value)
  }

  const handleSelectModule = (module: ModuleDefinition) => {
    setEntryPoint(module.entry)
    setIsEditingEntry(false)
    setSearchQuery('')
    if (onUpdateBuild) {
      onUpdateBuild(projectId, build.id, { entry: module.entry })
    }
  }
  const hasSymbols = build.symbols && build.symbols.length > 0
  const hasStages = build.stages && build.stages.length > 0
  const isSelected = selection.type === 'build' && selection.buildId === `${projectId}:${build.id}`
  
  return (
    <div
      className={`build-card ${isSelected ? 'selected' : ''} ${isBuilding ? 'building' : ''}`}
      onClick={(e) => {
        e.stopPropagation()
        onSelect({
          type: 'build',
          projectId,
          buildId: `${projectId}:${build.id}`,
          label: `${build.name}`
        })
      }}
    >
      {/* Header row - always visible */}
      <div className="build-card-header">
        <div className="build-header-left">
          <div className="build-status-icon">
            {getStatusIcon(build.status, 12, build.queuePosition)}
          </div>
          
          {/* Editable build name - only editable when selected */}
          {isEditingName && isSelected ? (
            <input
              type="text"
              className="build-name-input"
              value={buildName}
              onChange={(e) => setBuildName(e.target.value)}
              onBlur={handleNameSave}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleNameSave()
                if (e.key === 'Escape') {
                  setBuildName(build.name)
                  setIsEditingName(false)
                }
              }}
              autoFocus
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span
              className={`build-card-name ${isSelected ? 'editable' : ''}`}
              onClick={isSelected ? (e) => {
                e.stopPropagation()
                setIsEditingName(true)
              } : undefined}
              title={isSelected ? "Click to edit build name" : undefined}
            >
              {buildName}
            </span>
          )}

          {/* Current stage shown inline during building */}
          {isBuilding && currentStage && (
            <span className={`build-inline-stage ${stageAnimating ? 'animating' : ''}`}>
              {currentStage}
            </span>
          )}
        </div>
        
        <div className="build-header-right">
          {/* Indicators wrapper - slides left on hover to make room for play button */}
          <div className="build-indicators">
            {/* During build: show elapsed time on right */}
            {isBuilding && (
              <span className="build-elapsed-time-inline">{formatBuildTime(elapsedTime)}</span>
            )}
            {!isBuilding && (
              <>
                {/* Error/warning indicators - clickable to filter problems */}
                {build.errors !== undefined && build.errors > 0 && (
                  <span
                    className="error-indicator clickable"
                    onClick={(e) => {
                      e.stopPropagation()
                      onStageFilter?.('', build.id, projectId) // Empty stage = all problems for this build
                    }}
                    title="Click to filter problems for this build"
                  >
                    <AlertCircle size={12} />
                    <span>{build.errors}</span>
                  </span>
                )}
                {build.warnings !== undefined && build.warnings > 0 && (
                  <span
                    className="warning-indicator clickable"
                    onClick={(e) => {
                      e.stopPropagation()
                      onStageFilter?.('', build.id, projectId) // Empty stage = all problems for this build
                    }}
                    title="Click to filter problems for this build"
                  >
                    <AlertTriangle size={12} />
                    <span>{build.warnings}</span>
                  </span>
                )}

                {/* Time info - duration or relative time */}
                {build.duration ? (
                  <span className="build-duration">{build.duration.toFixed(1)}s</span>
                ) : build.lastBuild ? (
                  <span className="last-build-info" title={`Last build: ${build.lastBuild.status}`}>
                    {getLastBuildStatusIcon(build.lastBuild.status, 10)}
                    <span className="last-build-time">{formatRelativeTime(build.lastBuild.timestamp)}</span>
                  </span>
                ) : null}
              </>
            )}
          </div>

          {/* Build play/cancel button - slides in from right on hover */}
          {isBuilding ? (
            <button
              className="build-target-cancel-btn"
              onClick={(e) => {
                e.stopPropagation()
                if (build.buildId && onCancelBuild) {
                  onCancelBuild(build.buildId)
                }
              }}
              title={`Cancel build ${build.name}`}
            >
              <Square size={10} fill="currentColor" />
            </button>
          ) : (
            <button
              className="build-target-play-btn"
              onClick={(e) => {
                e.stopPropagation()
                onBuild('build', `${projectId}:${build.id}`, build.name)
              }}
              title={`Build ${build.name}`}
            >
              <Play size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Build progress bar - shown when building */}
      {isBuilding && (
        <div className="build-progress-container">
          <div className="build-progress-bar">
            <div
              className="build-progress-fill"
              style={{ width: `${getProgress()}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Expanded content - only when selected */}
      {isSelected && (
        <>
          {/* Entry point - editable with searchable module picker */}
          <div className="build-card-entry-row">
            <FileCode size={12} />
            {isEditingEntry ? (
              <div className="entry-picker" onClick={(e) => e.stopPropagation()}>
                <div className="entry-search-box">
                  <Search size={10} />
                  <input
                    ref={searchInputRef}
                    type="text"
                    className="entry-search-input"
                    value={searchQuery}
                    onChange={(e) => handleEntrySearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setSearchQuery('')
                        setIsEditingEntry(false)
                      }
                      if (e.key === 'Enter' && filteredModules.length === 1) {
                        handleSelectModule(filteredModules[0])
                      }
                    }}
                    placeholder="Search modules..."
                  />
                  <button
                    className="entry-close-btn"
                    onClick={() => {
                      setSearchQuery('')
                      setIsEditingEntry(false)
                    }}
                  >
                    <X size={10} />
                  </button>
                </div>
                <div className="entry-dropdown">
                  {filteredModules.length > 0 ? (
                    filteredModules.map(module => (
                      <div
                        key={module.entry}
                        className={`entry-option ${module.entry === entryPoint ? 'selected' : ''}`}
                        onClick={() => handleSelectModule(module)}
                      >
                        <Box size={10} className={`module-type-icon ${module.type}`} />
                        <span className="entry-option-name">{module.name}</span>
                        <span className="entry-option-file">{module.file}</span>
                      </div>
                    ))
                  ) : availableModules.length === 0 ? (
                    <div className="entry-empty">
                      <span>No modules found in project</span>
                    </div>
                  ) : (
                    <div className="entry-empty">
                      <span>No matching modules for "{searchQuery}"</span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <span
                className="entry-path editable"
                onClick={(e) => {
                  e.stopPropagation()
                  setIsEditingEntry(true)
                  setSearchQuery('')
                }}
                title="Click to change entry point"
              >
                {entryPoint}
              </span>
            )}
            {build.duration && (
              <span className="build-duration">
                <Clock size={10} />
                {build.duration.toFixed(1)}s
              </span>
            )}
          </div>
          
          {/* Build stages - expandable */}
          {hasStages && (
            <div className="build-stages-section">
              <button 
                className="stages-toggle"
                onClick={(e) => {
                  e.stopPropagation()
                  setShowStages(!showStages)
                }}
              >
                {showStages ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span>Build Stages</span>
                <span className="stages-summary">
                  {build.stages!.filter(s => s.status === 'success').length}/{build.stages!.length} complete
                </span>
              </button>
              
              {showStages && (
                <div className="build-stages-list">
                  {build.stages!.map((stage) => {
                    const isClickable = (stage.status === 'warning' || stage.status === 'error') && onStageFilter
                    const stageDuration = stage.duration ?? stage.elapsedSeconds
                    return (
                      <div
                        key={stage.name}
                        className={`stage-row ${stage.status} ${isClickable ? 'clickable' : ''}`}
                        onClick={isClickable ? (e) => {
                          e.stopPropagation()
                          onStageFilter(stage.name, build.id, projectId)
                        } : undefined}
                        title={isClickable ? `Filter problems to ${stage.displayName || stage.name} stage` : undefined}
                      >
                        {getStageIcon(stage.status)}
                        <span className="stage-name">{stage.displayName || stage.name}</span>
                        {stage.message && (
                          <span className="stage-message">{stage.message}</span>
                        )}
                        <span className="stage-duration">
                          {stage.status === 'running' ? (
                            <StageTimer />
                          ) : stageDuration != null ? (
                            `${stageDuration.toFixed(1)}s`
                          ) : (
                            ''
                          )}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
          
          {/* Action buttons */}
          <div className="build-card-actions">
            <button
              className="build-action-btn primary"
              onClick={(e) => {
                e.stopPropagation()
                onBuild('build', `${projectId}:${build.id}`, build.name)
              }}
              title={`Build ${build.name}`}
            >
              <Play size={12} />
              <span>Build</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation()
                onOpenSource?.(projectId, build.entry)
              }}
              title="Open Source Code"
            >
              <FileCode size={12} />
              <span>ato</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation()
                onOpenKiCad?.(projectId, build.id)
              }}
              title="Open in KiCad"
            >
              <Grid3X3 size={12} />
              <span>KiCad</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation()
                onOpenLayout?.(projectId, build.id)
              }}
              title="Edit Layout"
            >
              <Layout size={12} />
              <span>Layout</span>
            </button>
            <button
              className="build-action-btn"
              onClick={(e) => {
                e.stopPropagation()
                onOpen3D?.(projectId, build.id)
              }}
              title="3D Preview"
            >
              <Cuboid size={12} />
              <span>3D</span>
            </button>
          </div>
          
          {/* Entry point symbol - shown directly since there's always exactly one */}
          {hasSymbols && build.symbols![0] && (
            <div className="build-card-symbols">
              <SymbolNode
                key={build.symbols![0].path}
                symbol={build.symbols![0]}
                depth={0}
                projectId={projectId}
                selection={selection}
                onSelect={onSelect}
                onBuild={onBuild}
              />
            </div>
          )}
        </>
      )}
    </div>
  )
})

// Check if a package has an update available
function hasUpdate(project: Project): boolean {
  if (!project.installed || !project.version || !project.latestVersion) return false
  return project.version !== project.latestVersion
}

// Format download count for display (e.g., 12847 -> "12.8k")
function formatDownloads(count: number | null | undefined): string {
  if (count == null) return '0'
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
  }
  return count.toString()
}

// Check if package is installed in a specific project
// Uses the package's installed_in array which contains project roots/paths
function isInstalledInProject(
  pkg: Project,
  targetProjectPath: string,
  _allProjects: Project[]
): { installed: boolean; version?: string; needsUpdate?: boolean; latestVersion?: string } {
  // The package has an 'installed_in' property with project paths where it's installed
  // We need to check if targetProjectPath matches any of them
  // Note: installed_in may be undefined for packages from mock data

  // For packages from real data, check installed_in array
  const installedIn = (pkg as any).installedIn || []
  const isInstalled = installedIn.some((path: string) =>
    path === targetProjectPath || path.endsWith(`/${targetProjectPath}`) || targetProjectPath.endsWith(path)
  )

  if (!isInstalled) return { installed: false }

  const needsUpdate = pkg.latestVersion && pkg.version && pkg.version !== pkg.latestVersion

  return {
    installed: true,
    version: pkg.version,
    needsUpdate: !!needsUpdate,
    latestVersion: pkg.latestVersion
  }
}

// Install dropdown component - redesigned
function InstallDropdown({
  project,
  onInstall,
  availableProjects
}: {
  project: Project
  onInstall: (projectId: string, targetProject: string) => void
  availableProjects: AvailableProject[]
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedTargetId, setSelectedTargetId] = useState<string>(() => {
    // Default to active project
    return availableProjects.find(p => p.isActive)?.id || availableProjects[0]?.id || ''
  })
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  
  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  
  // Focus search input when dropdown opens (if many projects)
  useEffect(() => {
    if (isOpen && availableProjects.length > 5 && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [isOpen])
  
  const selectedTarget = availableProjects.find(p => p.id === selectedTargetId)
  const installStatus = isInstalledInProject(project, selectedTarget?.path || selectedTargetId, [])
  
  const handleInstall = (e: React.MouseEvent) => {
    e.stopPropagation()
    onInstall(project.id, selectedTargetId)
  }
  
  const handleSelectTarget = (targetId: string) => {
    setSelectedTargetId(targetId)
    setIsOpen(false)
  }
  
  // Determine button state based on selected target
  const isInstalled = installStatus.installed
  const needsUpdate = installStatus.needsUpdate
  
  return (
    <div className="install-dropdown" ref={dropdownRef}>
      <button 
        className={`install-btn ${isInstalled ? (needsUpdate ? 'update-available' : 'installed') : ''}`}
        onClick={handleInstall}
        title={needsUpdate ? `Update to v${installStatus.latestVersion} in ${selectedTarget?.name}` : `Install to ${selectedTarget?.name}`}
      >
        {isInstalled ? (
          needsUpdate ? (
            <>
              <ArrowUpCircle size={12} />
              <span>Update</span>
            </>
          ) : (
            <>
              <Check size={12} />
              <span>Installed</span>
            </>
          )
        ) : (
          <>
            <Download size={12} />
            <span>Install</span>
          </>
        )}
      </button>
      <button 
        className="install-dropdown-toggle"
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        title={`Target: ${selectedTarget?.name}`}
      >
        <ChevronDown size={12} />
      </button>
      {isOpen && (
        <div className={`install-dropdown-menu ${availableProjects.length > 5 ? 'scrollable' : ''}`}>
          <div className="dropdown-header">Install to project:</div>
          {availableProjects.length > 5 && (
            <div className="dropdown-search">
              <Search size={10} />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Filter projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          )}
          <div className="dropdown-items">
            {availableProjects
              .filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()))
              .map(p => {
                const status = isInstalledInProject(project, p.path, [])
                return (
                  <button
                    key={p.id}
                    className={`dropdown-item ${p.id === selectedTargetId ? 'selected' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectTarget(p.id)
                    }}
                  >
                    <Layers size={12} />
                    <span>{p.name}</span>
                    {status.installed && (
                      <span className={`status-badge ${status.needsUpdate ? 'outdated' : 'installed'}`}>
                        {status.needsUpdate ? `v${status.version}→${status.latestVersion}` : `v${status.version}`}
                      </span>
                    )}
                    {p.id === selectedTargetId && <Check size={12} className="selected-check" />}
                  </button>
                )
              })}
            {availableProjects.filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase())).length === 0 && (
              <div className="dropdown-empty">No projects match "{searchQuery}"</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Package card component (larger, with summary)
// Memoized to prevent unnecessary re-renders in lists
const PackageCard = memo(function PackageCard({
  project,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  onOpenPackageDetail: _onOpenPackageDetail,
  onInstall,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  availableProjects
}: {
  project: Project
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  onOpenPackageDetail?: (pkg: SelectedPackage) => void
  onInstall: (projectId: string, targetProject: string) => void
  onOpenSource?: (projectId: string, entry: string) => void
  onOpenKiCad?: (projectId: string, buildId: string) => void
  onOpenLayout?: (projectId: string, buildId: string) => void
  onOpen3D?: (projectId: string, buildId: string) => void
  availableProjects: AvailableProject[]
}) {
  const [expanded, setExpanded] = useState(false)
  const [descExpanded, setDescExpanded] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState(project.version || '')
  const isSelected = selection.type === 'project' && selection.projectId === project.id

  const totalWarnings = project.builds.reduce((sum, b) => sum + (b.warnings || 0), 0)

  // Mock available versions - in real implementation this would come from the package data
  const availableVersions = project.latestVersion && project.version && project.latestVersion !== project.version
    ? [project.latestVersion, project.version]
    : project.version ? [project.version] : []

  return (
    <div
      className={`package-card ${isSelected ? 'selected' : ''} ${expanded ? 'expanded' : ''}`}
      onClick={() => {
        setExpanded(!expanded)
        if (expanded) setDescExpanded(false) // Reset desc when collapsing
        onSelect({
          type: 'project',
          projectId: project.id,
          label: project.name
        })
      }}
    >
      {/* Row 1: Package name */}
      <div className="package-card-name-row">
        <span className="tree-expand">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        <Package size={18} className="package-icon" />
        <span className="package-name">{project.name}</span>
        {totalWarnings > 0 && <span className="warn-badge">{totalWarnings}</span>}
      </div>

      {/* Row 2: Description (summary when collapsed, full when expanded) */}
      {(project.summary || project.description) && (
        <div
          className={`package-card-description ${expanded && !descExpanded ? 'clamped' : ''}`}
          onClick={(e) => {
            if (expanded) {
              e.stopPropagation()
              setDescExpanded(!descExpanded)
            }
          }}
          title={expanded && !descExpanded ? 'Click to expand description' : ''}
        >
          {expanded ? (project.description || project.summary) : project.summary}
        </div>
      )}

      {/* Row 3: Compact actions bar - version, publisher, downloads, github, install */}
      <div className="package-actions-bar">
        {/* Version dropdown */}
        <select
          className="package-version-select"
          value={selectedVersion}
          onChange={(e) => {
            e.stopPropagation()
            setSelectedVersion(e.target.value)
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {availableVersions.map((v, idx) => (
            <option key={v} value={v}>
              {v}{idx === 0 && hasUpdate(project) ? ' (latest)' : ''}
            </option>
          ))}
        </select>

        {/* Publisher badge */}
        {project.publisher && (
          <span
            className={`package-publisher-badge ${project.publisher === 'atopile' ? 'official' : 'community'}`}
            title={`Published by ${project.publisher}`}
          >
            {project.publisher.toLowerCase()}
          </span>
        )}

        {/* Downloads count */}
        {project.downloads !== undefined && project.downloads > 0 && (
          <span className="package-downloads" title={`${project.downloads.toLocaleString()} downloads`}>
            <Download size={10} />
            {formatDownloads(project.downloads)}
          </span>
        )}

        {/* GitHub button */}
        {project.repository && (
          <a
            href={project.repository}
            className="package-link-btn"
            onClick={(e) => e.stopPropagation()}
            target="_blank"
            rel="noopener noreferrer"
            title="View on GitHub"
          >
            <Github size={12} />
          </a>
        )}

        {/* Install dropdown (pushed to right) */}
        <div className="package-install-wrapper" onClick={(e) => e.stopPropagation()}>
          <InstallDropdown project={project} onInstall={onInstall} availableProjects={availableProjects} />
        </div>
      </div>
      
      {/* Expanded content */}
      {expanded && (
        <>
          {/* Package Stats Bar with Links */}
          <div className="package-stats-bar">
            {project.publisher && (
              <div className={`package-stat publisher ${project.publisher === 'atopile' ? 'official' : 'community'}`}>
                <span>{project.publisher.toLowerCase()}</span>
              </div>
            )}
            {project.downloads !== undefined && project.downloads > 0 && (
              <div className="package-stat">
                <Download size={11} />
                <span>{formatDownloads(project.downloads)}</span>
              </div>
            )}
            {project.versionCount !== undefined && project.versionCount > 0 && (
              <div className="package-stat">
                <History size={11} />
                <span>{project.versionCount} releases</span>
              </div>
            )}
            {project.license && (
              <div className="package-stat license">
                <Scale size={11} />
                <span>{project.license}</span>
              </div>
            )}
            
            {/* Links on right side */}
            <div className="package-stat-links">
              {project.homepage && (
                <a 
                  href={project.homepage} 
                  className="package-stat-link"
                  onClick={(e) => e.stopPropagation()}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Homepage"
                >
                  <Globe size={12} />
                </a>
              )}
              {project.repository && (
                <a 
                  href={project.repository} 
                  className="package-stat-link"
                  onClick={(e) => e.stopPropagation()}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="GitHub Repository"
                >
                  <Github size={12} />
                </a>
              )}
            </div>
          </div>
          
          {/* Build targets */}
          <div className="package-card-builds">
            {project.builds.map((build, idx) => (
              <BuildNode
                key={`${build.id}-${idx}`}
                build={build}
                projectId={project.id}
                selection={selection}
                onSelect={onSelect}
                onBuild={onBuild}
                onCancelBuild={onCancelBuild}
                onStageFilter={onStageFilter}
                onOpenSource={onOpenSource}
                onOpenKiCad={onOpenKiCad}
                onOpenLayout={onOpenLayout}
                onOpen3D={onOpen3D}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
})

// Project card (for local projects - styled like package cards)
// Memoized to prevent unnecessary re-renders in lists
const ProjectNode = memo(function ProjectNode({
  project,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  onOpenPackageDetail: _onOpenPackageDetail,
  isExpanded,
  onExpandChange,
  onUpdateProject,
  onAddBuild,
  onUpdateBuild,
  onProjectExpand,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  onFileClick,
  availableModules = [],
  projectFiles = []
}: {
  project: Project
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  onOpenPackageDetail?: (pkg: SelectedPackage) => void
  isExpanded: boolean
  onExpandChange: (projectId: string, expanded: boolean) => void
  onUpdateProject?: (projectId: string, updates: Partial<Project>) => void
  onAddBuild?: (projectId: string) => void
  onUpdateBuild?: (projectId: string, buildId: string, updates: Partial<BuildTarget>) => void
  onProjectExpand?: (projectRoot: string) => void
  onOpenSource?: (projectId: string, entry: string) => void
  onOpenKiCad?: (projectId: string, buildId: string) => void
  onOpenLayout?: (projectId: string, buildId: string) => void
  onOpen3D?: (projectId: string, buildId: string) => void
  onFileClick?: (projectId: string, filePath: string) => void
  availableModules?: ModuleDefinition[]
  projectFiles?: FileTreeNode[]
}) {
  const expanded = isExpanded
  const [isEditingName, setIsEditingName] = useState(false)
  const [isEditingDesc, setIsEditingDesc] = useState(false)
  const [projectName, setProjectName] = useState(project.name)
  const [description, setDescription] = useState(project.summary || '')
  const isSelected = selection.type === 'project' && selection.projectId === project.id
  
  const totalErrors = project.builds.reduce((sum, b) => sum + (b.errors || 0), 0)
  const totalWarnings = project.builds.reduce((sum, b) => sum + (b.warnings || 0), 0)
  const isBuilding = project.builds.some(b => b.status === 'building')
  const successCount = project.builds.filter(b => b.status === 'success').length

  
  const defaultDescription = "A new atopile project!"
  const displayDescription = description || defaultDescription
  const isDefaultDesc = !description
  
  const handleNameSave = () => {
    setIsEditingName(false)
    if (onUpdateProject) {
      onUpdateProject(project.id, { name: projectName })
    }
    console.log('Saving name:', projectName)
  }
  
  const handleDescriptionSave = () => {
    setIsEditingDesc(false)
    if (onUpdateProject) {
      onUpdateProject(project.id, { summary: description })
    }
    console.log('Saving description:', description)
  }
  
  return (
    <div
      className={`project-card ${isSelected ? 'selected' : ''} ${expanded ? 'expanded' : 'collapsed'} ${isBuilding ? 'building' : ''}`}
      onClick={() => {
        const willExpand = !expanded
        onExpandChange(project.id, willExpand)
        onSelect({
          type: 'project',
          projectId: project.id,
          label: project.name
        })
        // Fetch modules when expanding (for entry point picker)
        if (willExpand && onProjectExpand) {
          onProjectExpand(project.path)
        }
      }}
    >
      {/* Row 1: Project name - always visible */}
      <div className="project-card-name-row">
        <span className="tree-expand">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        <Layers size={18} className="project-icon" />
        
        {/* Editable project name - only editable when expanded */}
        {isEditingName && expanded ? (
          <input
            type="text"
            className="project-name-input"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            onBlur={handleNameSave}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleNameSave()
              if (e.key === 'Escape') {
                setProjectName(project.name)
                setIsEditingName(false)
              }
            }}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span 
            className={`project-card-name ${expanded ? 'editable' : ''}`}
            onClick={expanded ? (e) => {
              e.stopPropagation()
              setIsEditingName(true)
            } : undefined}
            title={expanded ? "Click to edit name" : undefined}
          >
            {projectName}
          </span>
        )}
        
        {/* Status indicators and build button - right aligned */}
        <div className="project-card-actions-row">
          {/* Indicators wrapper - slides left on hover to make room for play button */}
          <div className="project-indicators">
            {/* Show errors/warnings/last build when not building (stop button handles building state) */}
            {!isBuilding && (
              <>
                {totalErrors > 0 && (
                  <span className="error-indicator">
                    <AlertCircle size={12} />
                    <span>{totalErrors}</span>
                  </span>
                )}
                {totalWarnings > 0 && (
                  <span className="warning-indicator">
                    <AlertTriangle size={12} />
                    <span>{totalWarnings}</span>
                  </span>
                )}
                {project.lastBuildTimestamp && (
                  <span className="last-build-info" title={`Last build: ${project.lastBuildStatus || 'unknown'}`}>
                    {project.lastBuildStatus && getLastBuildStatusIcon(project.lastBuildStatus, 10)}
                    <span className="last-build-time">{formatRelativeTime(project.lastBuildTimestamp)}</span>
                  </span>
                )}
              </>
            )}
          </div>

          {/* Play button or Stop button depending on build state */}
          {isBuilding ? (
            <button
              className="project-build-btn-icon stop"
              onClick={(e) => {
                e.stopPropagation()
                // Cancel all running builds in this project
                project.builds
                  .filter(b => b.status === 'building' && b.buildId)
                  .forEach(b => onCancelBuild?.(b.buildId!))
              }}
              title={`Stop all builds in ${project.name}`}
            >
              <Square size={12} fill="currentColor" />
            </button>
          ) : (
            <button
              className="project-build-btn-icon"
              onClick={(e) => {
                e.stopPropagation()
                onBuild('project', project.id, project.name)
              }}
              title={`Build all targets in ${project.name}`}
            >
              <Play size={14} fill="currentColor" />
            </button>
          )}
        </div>
      </div>
      
      {/* Expanded content */}
      {expanded && (
        <>
          {/* Row 2: Editable description */}
          <div className="project-card-description">
            {isEditingDesc ? (
              <input
                type="text"
                className="description-input"
                value={description}
                placeholder={defaultDescription}
                onChange={(e) => setDescription(e.target.value)}
                onBlur={handleDescriptionSave}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleDescriptionSave()
                  if (e.key === 'Escape') {
                    setDescription(project.summary || '')
                    setIsEditingDesc(false)
                  }
                }}
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span 
                className={`description-text ${isDefaultDesc ? 'placeholder' : ''}`}
                onClick={(e) => {
                  e.stopPropagation()
                  setIsEditingDesc(true)
                }}
                title="Click to edit description"
              >
                {displayDescription}
              </span>
            )}
          </div>
          
          {/* Row 3: Build summary */}
          <div className="project-card-footer">
            <div className="project-build-summary">
              <span className="build-count">{project.builds.length} build{project.builds.length !== 1 ? 's' : ''}</span>
              {successCount > 0 && (
                <span className="success-indicator">
                  <Check size={10} />
                  {successCount} passed
                </span>
              )}
            </div>
          </div>
          
          {/* Build targets */}
          <div className="project-card-builds">
            {project.builds.map((build, idx) => (
              <BuildNode
                key={`${build.id}-${idx}`}
                build={build}
                projectId={project.id}
                selection={selection}
                onSelect={onSelect}
                onBuild={onBuild}
                onCancelBuild={onCancelBuild}
                onStageFilter={onStageFilter}
                onUpdateBuild={onUpdateBuild}
                onOpenSource={onOpenSource}
                onOpenKiCad={onOpenKiCad}
                onOpenLayout={onOpenLayout}
                onOpen3D={onOpen3D}
                availableModules={availableModules}
              />
            ))}
            
            {/* Add new build button */}
            <button
              className="add-build-btn"
              onClick={(e) => {
                e.stopPropagation()
                if (onAddBuild) {
                  onAddBuild(project.id)
                }
              }}
              title="Add new build target"
            >
              <Plus size={12} />
              <span>Add build</span>
            </button>
          </div>

          {/* File Explorer */}
          <FileExplorer
            files={projectFiles}
            onFileClick={onFileClick ? (path) => onFileClick(project.id, path) : undefined}
          />
        </>
      )}
    </div>
  )
})

export function ProjectsPanel({ selection, onSelect, onBuild, onCancelBuild, onStageFilter, onOpenPackageDetail, onPackageInstall, onCreateProject, onProjectExpand, onOpenSource, onOpenKiCad, onOpenLayout, onOpen3D, onFileClick, filterType = 'all', projects: externalProjects, projectModules = {}, projectFiles = {} }: ProjectsPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [publisherFilter, setPublisherFilter] = useState<string | null>(null)
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
      path: `~/projects/${newId}`,
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
  
  // Get unique publishers for filter
  const publishers = [...new Set(
    localProjects
      .filter(p => p.type === 'package' && p.publisher)
      .map(p => p.publisher!)
  )].sort()

  // Create available projects list for install dropdown (only actual projects, not packages)
  const availableProjects: AvailableProject[] = localProjects
    .filter(p => p.type === 'project')
    .map((p, idx) => ({
      id: p.id,
      name: p.name,
      path: p.path,
      isActive: idx === 0  // First project is active by default
    }))
  
  // Handle install action
  const handleInstall = (packageId: string, targetProjectId: string) => {
    console.log(`Installing ${packageId} to ${targetProjectId}`)
    if (onPackageInstall) {
      // Find the project root for the target project
      const targetProject = localProjects.find(p => p.id === targetProjectId)
      const projectRoot = targetProject?.path || targetProjectId
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
    
    // Filter by publisher (only for packages)
    if (filterType === 'packages' && publisherFilter && project.publisher !== publisherFilter) {
      return false
    }
    
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
        
        {/* Publisher filter (only for packages) */}
        {filterType === 'packages' && publishers.length > 0 && (
          <div className="publisher-filter">
            <button 
              className={`publisher-filter-btn ${publisherFilter === null ? 'active' : ''}`}
              onClick={() => setPublisherFilter(null)}
            >
              All
            </button>
            {publishers.map(pub => (
              <button 
                key={pub}
                className={`publisher-filter-btn ${publisherFilter === pub ? 'active' : ''} ${pub === 'atopile' ? 'official' : 'community'}`}
                onClick={() => setPublisherFilter(pub)}
              >
                {pub}
              </button>
            ))}
          </div>
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
              onProjectExpand={onProjectExpand}
              onOpenSource={onOpenSource}
              onOpenKiCad={onOpenKiCad}
              onOpenLayout={onOpenLayout}
              onOpen3D={onOpen3D}
              onFileClick={onFileClick}
              availableModules={projectModules[project.path] || []}
              projectFiles={projectFiles[project.path] || []}
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
