import { useState, memo, useCallback, useMemo } from 'react'
import {
  ChevronDown, ChevronRight, Search, Package,
  Hash, Layers,
  ExternalLink, Copy, Check, AlertTriangle,
  RefreshCw, Cpu, Plug, Lightbulb, Radio
} from 'lucide-react'
import { BuildSelector } from './BuildSelector'
import type { Selection, Project } from './BuildSelector'
import type {
  BOMComponent as BOMComponentAPI,
  BOMData,
  BOMComponentType
} from '../types/build'

// Component types (local type alias for UI)
type ComponentType = BOMComponentType

// Parameter with optional constraint info for UI display
interface BOMParameterUI {
  name: string
  value: string
  unit?: string
  constraint?: string       // Design constraint (what user asked for)
  constraintUnit?: string   // Unit for constraint (if different)
}

// Transform API BOM component to UI component format
interface BOMComponentUI {
  id: string
  designators: string[]  // e.g., ['R1', 'R2', 'R5']
  type: ComponentType
  value: string          // e.g., '10kΩ', '100nF', 'STM32F405'
  package: string        // e.g., '0402', 'QFP-48'
  manufacturer?: string
  mpn?: string           // Manufacturer Part Number
  lcsc?: string          // LCSC Part Number
  description?: string
  quantity: number
  unitCost?: number      // in USD
  totalCost?: number
  inStock?: boolean
  stockQuantity?: number
  parameters?: BOMParameterUI[]
  source?: string        // 'picked' | 'specified' | 'manual'
  path?: string          // Design path (primary/declaration)
  usages?: { path: string; designator: string; line?: number }[]
}

// Where a component is used in the design
interface UsageLocation {
  path: string           // Full atopile path e.g., "main.ato:App.power_supply.decoupling[0]"
  designator: string     // e.g., "C3"
  line?: number          // Line number in file
}

// Grouped usage for tree view
interface UsageGroup {
  parentPath: string      // e.g., "App.power_supply"
  parentLabel: string     // e.g., "power_supply"
  instances: UsageLocation[]
}

// Transform API response to UI format
function transformBOMComponent(apiComp: BOMComponentAPI): BOMComponentUI {
  const designators = apiComp.usages.map(u => u.designator)
  const unitCost = apiComp.unitCost ?? undefined
  const totalCost = unitCost !== undefined ? unitCost * apiComp.quantity : undefined
  const stock = apiComp.stock

  return {
    id: apiComp.id,
    designators,
    type: apiComp.type as ComponentType,
    value: apiComp.value,
    package: apiComp.package,
    manufacturer: apiComp.manufacturer ?? undefined,
    mpn: apiComp.mpn ?? undefined,
    lcsc: apiComp.lcsc ?? undefined,
    description: apiComp.description ?? undefined,
    quantity: apiComp.quantity,
    unitCost,
    totalCost,
    inStock: stock !== undefined && stock !== null ? stock > 0 : undefined,
    stockQuantity: stock ?? undefined,
    parameters: apiComp.parameters,
    source: apiComp.source,
    path: apiComp.usages[0]?.address,
    usages: apiComp.usages.map(u => ({
      path: u.address,
      designator: u.designator,
    })),
  }
}

// Mock BOM data - exported for use in parent components
export const mockBOM: BOMComponentUI[] = [
  {
    id: 'r1',
    designators: ['R1', 'R2', 'R5', 'R8'],
    type: 'resistor',
    value: '10kΩ ±1%',
    package: '0402',
    manufacturer: 'Yageo',
    mpn: 'RC0402FR-0710KL',
    lcsc: 'C25744',
    description: 'Thick Film Resistor',
    quantity: 4,
    unitCost: 0.002,
    totalCost: 0.008,
    inStock: true,
    stockQuantity: 50000,
    parameters: [
      { name: 'Resistance', value: '10', unit: 'kΩ', constraint: '10 ±5%' },
      { name: 'Tolerance', value: '±1', unit: '%', constraint: '±5' },
      { name: 'Power Rating', value: '62.5', unit: 'mW', constraint: '> 0.1' },
    ],
    source: 'picked',
    path: 'main.ato:App.feedback_divider.r_top',
    usages: [
      { path: 'App.power_supply.feedback_divider.r_top', designator: 'R1', line: 45 },
      { path: 'App.power_supply.feedback_divider.r_bot', designator: 'R2', line: 46 },
      { path: 'App.leds.led_resistor', designator: 'R5', line: 78 },
      { path: 'App.sensors.pulldown', designator: 'R8', line: 92 },
    ],
  },
  {
    id: 'r2',
    designators: ['R3', 'R4'],
    type: 'resistor',
    value: '4.7kΩ ±1%',
    package: '0402',
    manufacturer: 'Yageo',
    mpn: 'RC0402FR-074K7L',
    lcsc: 'C25900',
    description: 'Thick Film Resistor - I2C Pull-up',
    quantity: 2,
    unitCost: 0.002,
    totalCost: 0.004,
    inStock: true,
    stockQuantity: 45000,
    parameters: [
      { name: 'Resistance', value: '4.7', unit: 'kΩ' },
    ],
    source: 'picked',
    path: 'main.ato:App.i2c_pullups',
    usages: [
      { path: 'App.sensors.i2c_pullups.scl_pullup', designator: 'R3', line: 55 },
      { path: 'App.sensors.i2c_pullups.sda_pullup', designator: 'R4', line: 56 },
    ],
  },
  {
    id: 'r3',
    designators: ['R6', 'R7'],
    type: 'resistor',
    value: '100kΩ ±1%',
    package: '0402',
    manufacturer: 'Yageo',
    mpn: 'RC0402FR-07100KL',
    lcsc: 'C25741',
    description: 'Thick Film Resistor',
    quantity: 2,
    unitCost: 0.002,
    totalCost: 0.004,
    inStock: true,
    stockQuantity: 38000,
    parameters: [
      { name: 'Resistance', value: '100', unit: 'kΩ' },
    ],
    source: 'picked',
    path: 'main.ato:App.voltage_divider',
    usages: [
      { path: 'App.mcu.nrst_pullup', designator: 'R6', line: 102 },
      { path: 'App.mcu.boot0_pulldown', designator: 'R7', line: 105 },
    ],
  },
  {
    id: 'c1',
    designators: ['C1', 'C2', 'C5', 'C6'],
    type: 'capacitor',
    value: '100nF',
    package: '0402',
    manufacturer: 'Samsung',
    mpn: 'CL05B104KO5NNNC',
    lcsc: 'C1525',
    description: 'MLCC - Decoupling',
    quantity: 4,
    unitCost: 0.003,
    totalCost: 0.012,
    inStock: true,
    stockQuantity: 120000,
    parameters: [
      { name: 'Capacitance', value: '100', unit: 'nF', constraint: '100 ±20%' },
      { name: 'Voltage Rating', value: '16', unit: 'V', constraint: '> 5' },
    ],
    source: 'picked',
    path: 'main.ato:App.decoupling',
    usages: [
      { path: 'App.mcu.decoupling[0]', designator: 'C1', line: 120 },
      { path: 'App.mcu.decoupling[1]', designator: 'C2', line: 120 },
      { path: 'App.sensors.bme280.decoupling', designator: 'C5', line: 145 },
      { path: 'App.power_supply.ldo.decoupling', designator: 'C6', line: 88 },
    ],
  },
  {
    id: 'c2',
    designators: ['C3', 'C4'],
    type: 'capacitor',
    value: '10µF',
    package: '0603',
    manufacturer: 'Samsung',
    mpn: 'CL10A106KP8NNNC',
    lcsc: 'C19702',
    description: 'MLCC - Bulk',
    quantity: 2,
    unitCost: 0.015,
    totalCost: 0.030,
    inStock: true,
    stockQuantity: 85000,
    parameters: [
      { name: 'Capacitance', value: '10', unit: 'µF', constraint: '10 ±20%' },
      { name: 'Voltage Rating', value: '10', unit: 'V', constraint: '> 6.3' },
    ],
    source: 'picked',
    path: 'main.ato:App.power_supply.output_cap',
    usages: [
      { path: 'App.power_supply.output_cap', designator: 'C3', line: 112 },
      { path: 'App.power_supply.input_cap', designator: 'C4', line: 108 },
    ],
  },
  {
    id: 'c3',
    designators: ['C7', 'C8'],
    type: 'capacitor',
    value: '22pF',
    package: '0402',
    manufacturer: 'Murata',
    mpn: 'GRM1555C1H220JA01D',
    lcsc: 'C1653',
    description: 'MLCC - Crystal Load',
    quantity: 2,
    unitCost: 0.005,
    totalCost: 0.010,
    inStock: true,
    stockQuantity: 25000,
    parameters: [
      { name: 'Capacitance', value: '22', unit: 'pF' },
    ],
    source: 'picked',
    path: 'main.ato:App.mcu.crystal_caps',
    usages: [
      { path: 'App.mcu.crystal_caps[0]', designator: 'C7', line: 130 },
      { path: 'App.mcu.crystal_caps[1]', designator: 'C8', line: 130 },
    ],
  },
  {
    id: 'u1',
    designators: ['U1'],
    type: 'ic',
    value: 'STM32F405RGT6',
    package: 'LQFP-64',
    manufacturer: 'STMicroelectronics',
    mpn: 'STM32F405RGT6',
    lcsc: 'C15742',
    description: 'ARM Cortex-M4 MCU, 168MHz, 1MB Flash',
    quantity: 1,
    unitCost: 8.50,
    totalCost: 8.50,
    inStock: true,
    stockQuantity: 1200,
    parameters: [
      { name: 'Core', value: 'ARM Cortex-M4', unit: '' },
      { name: 'Flash', value: '1', unit: 'MB' },
      { name: 'RAM', value: '192', unit: 'KB' },
    ],
    source: 'specified',
    path: 'main.ato:App.mcu',
    usages: [
      { path: 'App.mcu', designator: 'U1', line: 15 },
    ],
  },
  {
    id: 'u2',
    designators: ['U2'],
    type: 'ic',
    value: 'TLV75901PDRVR',
    package: 'SOT-23-6',
    manufacturer: 'Texas Instruments',
    mpn: 'TLV75901PDRVR',
    lcsc: 'C181829',
    description: '300mA LDO, 3.3V Fixed Output',
    quantity: 1,
    unitCost: 0.45,
    totalCost: 0.45,
    inStock: true,
    stockQuantity: 5600,
    parameters: [
      { name: 'Output Voltage', value: '3.3', unit: 'V' },
      { name: 'Output Current', value: '300', unit: 'mA' },
    ],
    source: 'picked',
    path: 'main.ato:App.power_supply.ldo',
    usages: [
      { path: 'App.power_supply.ldo', designator: 'U2', line: 82 },
    ],
  },
  {
    id: 'u3',
    designators: ['U3'],
    type: 'ic',
    value: 'BME280',
    package: 'LGA-8',
    manufacturer: 'Bosch',
    mpn: 'BME280',
    lcsc: 'C92489',
    description: 'Temp/Humidity/Pressure Sensor',
    quantity: 1,
    unitCost: 3.20,
    totalCost: 3.20,
    inStock: true,
    stockQuantity: 890,
    parameters: [
      { name: 'Interface', value: 'I2C/SPI', unit: '' },
      { name: 'Supply Voltage', value: '1.71-3.6', unit: 'V' },
    ],
    source: 'specified',
    path: 'main.ato:App.sensors.bme280',
    usages: [
      { path: 'App.sensors.bme280', designator: 'U3', line: 140 },
    ],
  },
  {
    id: 'y1',
    designators: ['Y1'],
    type: 'crystal',
    value: '8MHz',
    package: '3215',
    manufacturer: 'Abracon',
    mpn: 'ABM8-8.000MHZ-B2-T',
    lcsc: 'C115962',
    description: 'Crystal Oscillator',
    quantity: 1,
    unitCost: 0.25,
    totalCost: 0.25,
    inStock: true,
    stockQuantity: 3400,
    parameters: [
      { name: 'Frequency', value: '8', unit: 'MHz' },
    ],
    source: 'picked',
    path: 'main.ato:App.mcu.crystal',
    usages: [
      { path: 'App.mcu.crystal', designator: 'Y1', line: 125 },
    ],
  },
  {
    id: 'd1',
    designators: ['D1', 'D2'],
    type: 'led',
    value: 'Green LED',
    package: '0603',
    manufacturer: 'Everlight',
    mpn: '19-217/GHC-YR1S2/3T',
    lcsc: 'C72043',
    description: 'Status LED - Green',
    quantity: 2,
    unitCost: 0.02,
    totalCost: 0.04,
    inStock: true,
    stockQuantity: 18000,
    parameters: [
      { name: 'Color', value: 'Green', unit: '' },
      { name: 'Forward Voltage', value: '2.0-2.4', unit: 'V' },
    ],
    source: 'picked',
    path: 'main.ato:App.leds.status',
    usages: [
      { path: 'App.leds.power_led', designator: 'D1', line: 160 },
      { path: 'App.leds.status_led', designator: 'D2', line: 165 },
    ],
  },
  {
    id: 'j1',
    designators: ['J1'],
    type: 'connector',
    value: 'USB-C',
    package: 'SMD',
    manufacturer: 'Korean Hroparts',
    mpn: 'TYPE-C-31-M-12',
    lcsc: 'C165948',
    description: 'USB Type-C Receptacle',
    quantity: 1,
    unitCost: 0.35,
    totalCost: 0.35,
    inStock: false,
    stockQuantity: 0,
    parameters: [
      { name: 'Type', value: 'USB-C 2.0', unit: '' },
    ],
    source: 'specified',
    path: 'main.ato:App.usb_connector',
    usages: [
      { path: 'App.usb_connector', designator: 'J1', line: 8 },
    ],
  },
]

// Get short type label
function getTypeLabel(type: ComponentType): string {
  switch (type) {
    case 'resistor': return 'R'
    case 'capacitor': return 'C'
    case 'inductor': return 'L'
    case 'ic': return 'IC'
    case 'connector': return 'J'
    case 'led': return 'LED'
    case 'diode': return 'D'
    case 'transistor': return 'Q'
    case 'crystal': return 'Y'
    default: return 'X'
  }
}

// Format currency
function formatCurrency(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`
  if (value < 1) return `$${value.toFixed(3)}`
  return `$${value.toFixed(2)}`
}

// Group usages by a common module prefix for cleaner tree display
function groupUsagesByModule(usages: UsageLocation[]): UsageGroup[] {
  const groups: Map<string, UsageGroup> = new Map()

  for (const usage of usages) {
    // Extract the parent module path for grouping
    // e.g., "passives.ato::App.ad1938.decoupling[0]|Cap" -> group by "ad1938"
    const parts = usage.path.split('::')
    const addressPart = parts.length > 1 ? parts[1] : usage.path
    const withoutType = addressPart.split('|')[0]
    const segments = withoutType.split('.')

    let parentPath: string
    let parentLabel: string

    if (segments.length >= 3) {
      // Group by the module before the leaf (e.g., "App.ad1938" for "App.ad1938.cap")
      parentPath = segments.slice(0, -1).join('.')
      parentLabel = segments[segments.length - 2]
    } else if (segments.length === 2) {
      parentPath = segments[0]
      parentLabel = segments[0]
    } else {
      parentPath = usage.path
      parentLabel = usage.path
    }

    if (!groups.has(parentPath)) {
      groups.set(parentPath, {
        parentPath,
        parentLabel,
        instances: []
      })
    }
    groups.get(parentPath)!.instances.push(usage)
  }

  return Array.from(groups.values())
}

// Format stock number with K/M suffixes
function formatStock(stock: number): string {
  if (stock >= 1000000) {
    return `${(stock / 1000000).toFixed(1)}M`
  }
  if (stock >= 1000) {
    return `${(stock / 1000).toFixed(0)}K`
  }
  return stock.toString()
}

// Component row - cleaner table layout with improved tree structure
// Memoized to prevent unnecessary re-renders in list
const BOMRow = memo(function BOMRow({
  component,
  isExpanded,
  onToggle,
  onCopy,
  onGoToSource
}: {
  component: BOMComponentUI
  isExpanded: boolean
  onToggle: () => void
  onCopy: (text: string) => void
  onGoToSource: (path: string, line?: number) => void
}) {
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => new Set())

  const handleCopy = (field: string, value: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onCopy(value)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 1500)
  }

  const handleUsageClick = (e: React.MouseEvent, usage: UsageLocation) => {
    e.stopPropagation()
    onGoToSource(usage.path, usage.line)
  }

  const toggleGroup = (groupPath: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(groupPath)) {
        next.delete(groupPath)
      } else {
        next.add(groupPath)
      }
      return next
    })
  }

  const usageGroups = component.usages ? groupUsagesByModule(component.usages) : []

  return (
    <div className={`bom-row ${isExpanded ? 'expanded' : ''}`} onClick={onToggle}>
      {/* Compact header row: Type | Value | MPN | Qty | Cost */}
      <div className="bom-row-header">
        <span className="bom-expand">
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className={`bom-type-badge type-${component.type}`}>{getTypeLabel(component.type)}</span>
        <span className="bom-value">{component.value}</span>
        {component.mpn && (
          <span className="bom-mpn" title={component.mpn}>{component.mpn}</span>
        )}
        <span className="bom-quantity">×{component.quantity}</span>
        {component.totalCost !== undefined && (
          <span className="bom-cost">{formatCurrency(component.totalCost)}</span>
        )}
        {component.inStock === false && (
          <AlertTriangle size={12} className="bom-stock-warning" />
        )}
      </div>

      {isExpanded && (
        <div className="bom-row-details">
          {/* Part details - single column table layout */}
          <table className="bom-detail-table">
            <tbody>
              <tr>
                <td className="detail-cell-label">Manufacturer</td>
                <td className="detail-cell-value">{component.manufacturer || '-'}</td>
              </tr>
              <tr>
                <td className="detail-cell-label">Package</td>
                <td className="detail-cell-value">{component.package}</td>
              </tr>
              <tr>
                <td className="detail-cell-label">LCSC</td>
                <td className="detail-cell-value">
                  {component.lcsc ? (
                    <span
                      className="lcsc-link"
                      onClick={(e) => handleCopy('lcsc', component.lcsc!, e)}
                    >
                      <span className="mono">{component.lcsc}</span>
                      <a
                        href={`https://www.lcsc.com/product-detail/${component.lcsc}.html`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="external-link"
                      >
                        <ExternalLink size={10} />
                      </a>
                      {copiedField === 'lcsc' ? (
                        <Check size={10} className="copy-icon copied" />
                      ) : (
                        <Copy size={10} className="copy-icon" />
                      )}
                    </span>
                  ) : '-'}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Stock</td>
                <td className={`detail-cell-value ${component.inStock === false ? 'out-of-stock' : 'in-stock'}`}>
                  {component.inStock === false ? (
                    <span className="stock-out"><AlertTriangle size={10} /> Out of stock</span>
                  ) : (
                    component.stockQuantity ? formatStock(component.stockQuantity) : 'In stock'
                  )}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Unit Cost</td>
                <td className="detail-cell-value cost">{component.unitCost ? formatCurrency(component.unitCost) : '-'}</td>
              </tr>
              <tr>
                <td className="detail-cell-label">Source</td>
                <td className="detail-cell-value">
                  <span className={`source-badge source-${component.source}`}>
                    {component.source === 'picked' ? 'Auto-picked' :
                     component.source === 'specified' ? 'Specified' : 'Manual'}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>

          {/* Where used - tree view grouped by module */}
          {usageGroups.length > 0 && (
            <div className="bom-usages-tree">
              <div className="usages-header">
                <span>Used in design</span>
                <span className="usages-count">{component.quantity} instance{component.quantity !== 1 ? 's' : ''}</span>
              </div>
              <div className="usage-groups">
                {usageGroups.map((group) => (
                  <div key={group.parentPath} className="usage-group">
                    {group.instances.length > 1 ? (
                      <>
                        <div
                          className="usage-group-header"
                          onClick={(e) => toggleGroup(group.parentPath, e)}
                        >
                          <span className="usage-expand">
                            {expandedGroups.has(group.parentPath) ?
                              <ChevronDown size={11} /> : <ChevronRight size={11} />}
                          </span>
                          <span className="usage-module-name">{group.parentLabel}</span>
                          <span className="usage-count-badge">×{group.instances.length}</span>
                        </div>
                        {expandedGroups.has(group.parentPath) && (
                          <div className="usage-instances">
                            {group.instances.map((usage, idx) => {
                              // Extract just the leaf name (e.g., "decoupling[0]" from full path)
                              const leafName = usage.path.split('.').pop()?.split('|')[0] || usage.path
                              return (
                                <div
                                  key={idx}
                                  className="usage-instance"
                                  onClick={(e) => handleUsageClick(e, usage)}
                                  title={usage.path}
                                >
                                  <span className="usage-designator">{usage.designator}</span>
                                  <span className="usage-leaf">{leafName}</span>
                                  <ExternalLink size={9} className="usage-goto" />
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </>
                    ) : (
                      <div
                        className="usage-single"
                        onClick={(e) => handleUsageClick(e, group.instances[0])}
                        title={group.instances[0].path}
                      >
                        <span className="usage-designator">{group.instances[0].designator}</span>
                        <span className="usage-module-path">{group.parentPath}</span>
                        <ExternalLink size={10} className="usage-goto" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
})

// Type filter options
type TypeFilter = 'all' | ComponentType

interface BOMPanelProps {
  selection: Selection
  onSelectionChange: (selection: Selection) => void
  projects: Project[]
  // API data props
  bomData?: BOMData | null
  isLoading?: boolean
  error?: string | null
  onRefresh?: () => void
  onGoToSource?: (path: string, line?: number) => void
}

export function BOMPanel({
  selection,
  onSelectionChange,
  projects,
  bomData,
  isLoading = false,
  error = null,
  onRefresh,
  onGoToSource: externalGoToSource,
}: BOMPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [copiedValue, setCopiedValue] = useState<string | null>(null)

  // Memoize API data transformation
  const bomComponents = useMemo((): BOMComponentUI[] => {
    return bomData?.components
      ? bomData.components.map(transformBOMComponent)
      : mockBOM
  }, [bomData?.components])

  // Memoize callbacks to prevent child re-renders
  const handleToggle = useCallback((id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const handleCopy = useCallback((value: string) => {
    navigator.clipboard.writeText(value)
    setCopiedValue(value)
    setTimeout(() => setCopiedValue(null), 2000)
  }, [])

  const handleGoToSource = useCallback((path: string, line?: number) => {
    if (externalGoToSource) {
      externalGoToSource(path, line)
    } else {
      console.log(`Navigate to: ${path}${line ? `:${line}` : ''}`)
    }
  }, [externalGoToSource])

  // Loading state
  if (isLoading) {
    return (
      <div className="bom-panel">
        <div className="bom-loading">
          <RefreshCw size={24} className="loading-spinner" />
          <span>Loading BOM...</span>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bom-panel">
        <div className="bom-error">
          <AlertTriangle size={24} />
          <span>{error}</span>
          {onRefresh && (
            <button className="refresh-btn" onClick={onRefresh}>
              <RefreshCw size={12} />
              Retry
            </button>
          )}
        </div>
      </div>
    )
  }

  // Pre-compute lowercase search for performance
  const searchLower = useMemo(() => searchQuery.toLowerCase(), [searchQuery])

  // Memoize filtered and sorted components
  const filteredComponents = useMemo(() => {
    return bomComponents
      .filter(c => {
        // Type filter
        if (typeFilter !== 'all' && c.type !== typeFilter) return false

        // Search filter
        if (searchLower) {
          return (
            c.value.toLowerCase().includes(searchLower) ||
            c.mpn?.toLowerCase().includes(searchLower) ||
            c.lcsc?.toLowerCase().includes(searchLower) ||
            c.manufacturer?.toLowerCase().includes(searchLower) ||
            c.description?.toLowerCase().includes(searchLower)
          )
        }
        return true
      })
      .sort((a, b) => (b.totalCost || 0) - (a.totalCost || 0))
  }, [bomComponents, typeFilter, searchLower])

  // Memoize totals calculation - single pass for efficiency
  const { totalComponents, totalCost, uniqueParts, outOfStock } = useMemo(() => {
    let total = 0
    let cost = 0
    let oos = 0
    for (const c of bomComponents) {
      total += c.quantity
      cost += c.totalCost || 0
      if (c.inStock === false) oos++
    }
    return {
      totalComponents: total,
      totalCost: cost,
      uniqueParts: bomComponents.length,
      outOfStock: oos
    }
  }, [bomComponents])
  
  return (
    <div className="bom-panel">
      {/* Summary bar */}
      <div className="bom-summary">
        <div className="bom-summary-item">
          <span className="summary-value">{uniqueParts}</span>
          <span className="summary-label">unique</span>
        </div>
        <div className="bom-summary-item">
          <span className="summary-value">{totalComponents}</span>
          <span className="summary-label">total</span>
        </div>
        <div className="bom-summary-item primary">
          <span className="summary-value">{formatCurrency(totalCost)}</span>
          <span className="summary-label">cost</span>
        </div>
        {outOfStock > 0 && (
          <div className="bom-summary-item warning">
            <AlertTriangle size={12} />
            <span className="summary-value">{outOfStock}</span>
            <span className="summary-label">out of stock</span>
          </div>
        )}
      </div>
      
      {/* Unified toolbar */}
      <div className="panel-toolbar">
        <div className="panel-toolbar-row">
          <div className="search-box">
            <Search size={14} />
            <input
              type="text"
              placeholder="Search value, MPN..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <BuildSelector
            selection={selection}
            onSelectionChange={onSelectionChange}
            projects={projects}
            showSymbols={true}
            compact
          />
        </div>
        
        {/* Type filters with icons */}
        <div className="filter-group">
          <button 
            className={`filter-btn ${typeFilter === 'all' ? 'active' : ''}`}
            onClick={() => setTypeFilter('all')}
            title="All components"
          >
            All
          </button>
          <button 
            className={`filter-btn icon-filter ${typeFilter === 'resistor' ? 'active' : ''}`}
            onClick={() => setTypeFilter('resistor')}
            title="Resistors"
          >
            <Hash size={12} />
          </button>
          <button 
            className={`filter-btn icon-filter ${typeFilter === 'capacitor' ? 'active' : ''}`}
            onClick={() => setTypeFilter('capacitor')}
            title="Capacitors"
          >
            <Layers size={12} />
          </button>
          <button 
            className={`filter-btn icon-filter ${typeFilter === 'ic' ? 'active' : ''}`}
            onClick={() => setTypeFilter('ic')}
            title="ICs / Chips"
          >
            <Cpu size={12} />
          </button>
          <button 
            className={`filter-btn icon-filter ${typeFilter === 'connector' ? 'active' : ''}`}
            onClick={() => setTypeFilter('connector')}
            title="Connectors"
          >
            <Plug size={12} />
          </button>
          <button 
            className={`filter-btn icon-filter ${typeFilter === 'led' ? 'active' : ''}`}
            onClick={() => setTypeFilter('led')}
            title="LEDs"
          >
            <Lightbulb size={12} />
          </button>
          <button 
            className={`filter-btn icon-filter ${typeFilter === 'crystal' ? 'active' : ''}`}
            onClick={() => setTypeFilter('crystal')}
            title="Crystals / Oscillators"
          >
            <Radio size={12} />
          </button>
        </div>
      </div>
      
      {/* Component list */}
      <div className="bom-list">
        {filteredComponents.map(component => (
          <BOMRow
            key={component.id}
            component={component}
            isExpanded={expandedIds.has(component.id)}
            onToggle={() => handleToggle(component.id)}
            onCopy={handleCopy}
            onGoToSource={handleGoToSource}
          />
        ))}
        
        {filteredComponents.length === 0 && (
          <div className="bom-empty">
            <Package size={24} />
            <span>No components found</span>
          </div>
        )}
      </div>
      
      {/* Toast */}
      {copiedValue && (
        <div className="bom-toast">
          <Check size={10} />
          Copied: {copiedValue}
        </div>
      )}
    </div>
  )
}
