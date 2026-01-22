import { useState } from 'react'
import {
  ChevronDown, ChevronRight, Search, Box, Zap, Cpu,
  Cable, Copy, Hash
} from 'lucide-react'

// Standard library item types
type StdLibType = 'interface' | 'module' | 'component' | 'trait' | 'parameter'

// Child/field in an interface or module
// Backend uses to_frontend_dict() which converts snake_case to camelCase
interface StdLibChild {
  name: string
  type: string  // The type name (e.g., "Electrical", "ElectricLogic")
  itemType?: StdLibType  // Whether it's interface, parameter, etc.
  children?: StdLibChild[]
  enumValues?: string[] // For EnumParameter types, the possible values
}

// Helper to get item type from child
function getChildItemType(child: StdLibChild): StdLibType {
  // Backend sends camelCase via to_frontend_dict()
  return child.itemType || 'interface'
}

interface StdLibItem {
  id: string
  name: string
  type: StdLibType
  description: string
  usage?: string | null
  children?: StdLibChild[]  // Nested structure
  parameters?: { name: string; type: string }[]
}

// Mock standard library data with nested structure
const mockStdLib: StdLibItem[] = [
  // Interfaces
  {
    id: 'Electrical',
    name: 'Electrical',
    type: 'interface',
    description: 'Base electrical connection point. Represents a single electrical node.',
    usage: `signal my_signal = new Electrical
resistor.p1 ~ my_signal`,
  },
  {
    id: 'ElectricPower',
    name: 'ElectricPower',
    type: 'interface',
    description: 'Power supply interface with high and low voltage rails. Use for VCC/GND connections.',
    usage: `power = new ElectricPower
power.hv ~ vcc_pin
power.lv ~ gnd_pin
assert power.voltage within 3.0V to 3.6V`,
    children: [
      { name: 'hv', type: 'Electrical', itemType: 'interface' },
      { name: 'lv', type: 'Electrical', itemType: 'interface' },
      { name: 'voltage', type: 'V', itemType: 'parameter' },
      { name: 'current', type: 'A', itemType: 'parameter' },
    ],
  },
  {
    id: 'ElectricLogic',
    name: 'ElectricLogic',
    type: 'interface',
    description: 'Digital logic signal with voltage reference. For GPIO, digital inputs/outputs.',
    usage: `gpio = new ElectricLogic
gpio.line ~ mcu.PA0
gpio.reference ~ power_3v3`,
    children: [
      { name: 'line', type: 'Electrical', itemType: 'interface' },
      { name: 'reference', type: 'ElectricPower', itemType: 'interface', children: [
        { name: 'hv', type: 'Electrical', itemType: 'interface' },
        { name: 'lv', type: 'Electrical', itemType: 'interface' },
      ]},
    ],
  },
  {
    id: 'ElectricSignal',
    name: 'ElectricSignal',
    type: 'interface',
    description: 'Analog signal with voltage domain reference. For ADC inputs, analog sensors.',
    usage: `analog_in = new ElectricSignal
analog_in.line ~ sensor.output
analog_in.reference ~ power_3v3`,
    children: [
      { name: 'line', type: 'Electrical', itemType: 'interface' },
      { name: 'reference', type: 'ElectricPower', itemType: 'interface', children: [
        { name: 'hv', type: 'Electrical', itemType: 'interface' },
        { name: 'lv', type: 'Electrical', itemType: 'interface' },
      ]},
    ],
  },
  {
    id: 'DifferentialPair',
    name: 'DifferentialPair',
    type: 'interface',
    description: 'Differential signal pair for high-speed communication (USB, Ethernet, LVDS).',
    usage: `usb_data = new DifferentialPair
usb_data.p ~ usb_connector.DP
usb_data.n ~ usb_connector.DN`,
    children: [
      { name: 'p', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'n', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
    ],
  },
  {
    id: 'I2C',
    name: 'I2C',
    type: 'interface',
    description: 'I²C bus interface with clock and data lines. Supports address configuration.',
    usage: `i2c_bus = new I2C
i2c_bus ~ sensor.i2c
assert i2c_bus.frequency within 100kHz to 400kHz`,
    children: [
      { name: 'scl', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'sda', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'frequency', type: 'Hz', itemType: 'parameter' },
      { name: 'address', type: 'dimensionless', itemType: 'parameter' },
    ],
  },
  {
    id: 'SPI',
    name: 'SPI',
    type: 'interface',
    description: 'SPI bus interface with clock, data in/out, and chip select.',
    usage: `spi_bus = new SPI
spi_bus ~ flash.spi
assert spi_bus.frequency <= 10MHz`,
    children: [
      { name: 'sclk', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'mosi', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'miso', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'cs', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'frequency', type: 'Hz', itemType: 'parameter' },
    ],
  },
  {
    id: 'UART',
    name: 'UART',
    type: 'interface',
    description: 'Serial UART interface with TX and RX lines.',
    usage: `uart = new UART
uart.tx ~ mcu.TX
uart.rx ~ mcu.RX
assert uart.baud_rate is 115200`,
    children: [
      { name: 'tx', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'rx', type: 'ElectricLogic', itemType: 'interface', children: [
        { name: 'line', type: 'Electrical', itemType: 'interface' },
        { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
      ]},
      { name: 'baud_rate', type: 'dimensionless', itemType: 'parameter' },
    ],
  },
  {
    id: 'Ethernet',
    name: 'Ethernet',
    type: 'interface',
    description: '10/100/1000 Ethernet interface with MDI pairs for PHY connection.',
    usage: `eth = new Ethernet
eth ~ phy.mdi
assert eth.speed within 100Mbps to 1000Mbps`,
    children: [
      { name: 'tx_p', type: 'DifferentialPair', itemType: 'interface', children: [
        { name: 'p', type: 'ElectricLogic', itemType: 'interface', children: [
          { name: 'line', type: 'Electrical', itemType: 'interface' },
          { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
        ]},
        { name: 'n', type: 'ElectricLogic', itemType: 'interface', children: [
          { name: 'line', type: 'Electrical', itemType: 'interface' },
          { name: 'reference', type: 'ElectricPower', itemType: 'interface' },
        ]},
      ]},
      { name: 'tx_n', type: 'DifferentialPair', itemType: 'interface', children: [
        { name: 'p', type: 'ElectricLogic', itemType: 'interface' },
        { name: 'n', type: 'ElectricLogic', itemType: 'interface' },
      ]},
      { name: 'rx_p', type: 'DifferentialPair', itemType: 'interface', children: [
        { name: 'p', type: 'ElectricLogic', itemType: 'interface' },
        { name: 'n', type: 'ElectricLogic', itemType: 'interface' },
      ]},
      { name: 'rx_n', type: 'DifferentialPair', itemType: 'interface', children: [
        { name: 'p', type: 'ElectricLogic', itemType: 'interface' },
        { name: 'n', type: 'ElectricLogic', itemType: 'interface' },
      ]},
      { name: 'speed', type: 'bps', itemType: 'parameter' },
    ],
  },
  {
    id: 'USB2',
    name: 'USB2',
    type: 'interface',
    description: 'USB 2.0 interface with differential data pair and power.',
    usage: `usb = new USB2
usb.data ~ connector.dp_dn
usb.power ~ connector.vbus`,
    children: [
      { name: 'data', type: 'DifferentialPair', itemType: 'interface', children: [
        { name: 'p', type: 'ElectricLogic', itemType: 'interface' },
        { name: 'n', type: 'ElectricLogic', itemType: 'interface' },
      ]},
      { name: 'power', type: 'ElectricPower', itemType: 'interface', children: [
        { name: 'hv', type: 'Electrical', itemType: 'interface' },
        { name: 'lv', type: 'Electrical', itemType: 'interface' },
        { name: 'voltage', type: 'V', itemType: 'parameter' },
      ]},
    ],
  },
  // Modules
  {
    id: 'Resistor',
    name: 'Resistor',
    type: 'module',
    description: 'Generic resistor with automatic part selection based on constraints.',
    usage: `r1 = new Resistor
r1.resistance = 10kohm +/- 5%
r1.package = "0402"
power.hv ~> r1 ~> led.anode`,
    children: [
      { name: 'p1', type: 'Electrical', itemType: 'interface' },
      { name: 'p2', type: 'Electrical', itemType: 'interface' },
      { name: 'resistance', type: 'ohm', itemType: 'parameter' },
      { name: 'max_power', type: 'W', itemType: 'parameter' },
      { name: 'max_voltage', type: 'V', itemType: 'parameter' },
      { name: 'package', type: 'string', itemType: 'parameter' },
    ],
  },
  {
    id: 'Capacitor',
    name: 'Capacitor',
    type: 'module',
    description: 'Generic capacitor with automatic part selection. Supports ceramic, electrolytic.',
    usage: `c1 = new Capacitor
c1.capacitance = 100nF +/- 20%
c1.package = "0402"
power.hv ~> c1 ~> power.lv`,
    children: [
      { name: 'p1', type: 'Electrical', itemType: 'interface' },
      { name: 'p2', type: 'Electrical', itemType: 'interface' },
      { name: 'capacitance', type: 'F', itemType: 'parameter' },
      { name: 'max_voltage', type: 'V', itemType: 'parameter' },
      { name: 'package', type: 'string', itemType: 'parameter' },
    ],
  },
  {
    id: 'Inductor',
    name: 'Inductor',
    type: 'module',
    description: 'Generic inductor for power supplies, filters, and RF applications.',
    usage: `l1 = new Inductor
l1.inductance = 10uH +/- 20%
l1.max_current = 1A`,
    children: [
      { name: 'p1', type: 'Electrical', itemType: 'interface' },
      { name: 'p2', type: 'Electrical', itemType: 'interface' },
      { name: 'inductance', type: 'H', itemType: 'parameter' },
      { name: 'max_current', type: 'A', itemType: 'parameter' },
    ],
  },
  {
    id: 'LED',
    name: 'LED',
    type: 'module',
    description: 'Light emitting diode with forward voltage and current parameters.',
    usage: `led = new LED
led.color = "green"
led.package = "0603"
power.hv ~> resistor ~> led.anode
led.cathode ~ power.lv`,
    children: [
      { name: 'anode', type: 'Electrical', itemType: 'interface' },
      { name: 'cathode', type: 'Electrical', itemType: 'interface' },
      { name: 'color', type: 'string', itemType: 'parameter' },
      { name: 'package', type: 'string', itemType: 'parameter' },
    ],
  },
  {
    id: 'Diode',
    name: 'Diode',
    type: 'module',
    description: 'Generic diode for rectification and protection circuits.',
    usage: `d1 = new Diode
d1.forward_voltage = 0.7V
power.hv ~> d1 ~> load`,
    children: [
      { name: 'anode', type: 'Electrical', itemType: 'interface' },
      { name: 'cathode', type: 'Electrical', itemType: 'interface' },
      { name: 'forward_voltage', type: 'V', itemType: 'parameter' },
      { name: 'max_current', type: 'A', itemType: 'parameter' },
    ],
  },
  {
    id: 'MOSFET',
    name: 'MOSFET',
    type: 'module',
    description: 'N-channel or P-channel MOSFET for switching and amplification.',
    usage: `q1 = new MOSFET
q1.channel = "N"
q1.gate ~ driver.output
q1.drain ~ load
q1.source ~ power.lv`,
    children: [
      { name: 'gate', type: 'Electrical', itemType: 'interface' },
      { name: 'drain', type: 'Electrical', itemType: 'interface' },
      { name: 'source', type: 'Electrical', itemType: 'interface' },
      { name: 'channel', type: 'string', itemType: 'parameter' },
    ],
  },
  {
    id: 'Crystal',
    name: 'Crystal',
    type: 'module',
    description: 'Quartz crystal oscillator for clock generation.',
    usage: `xtal = new Crystal
xtal.frequency = 8MHz +/- 50ppm
xtal.p1 ~ mcu.OSC_IN
xtal.p2 ~ mcu.OSC_OUT`,
    children: [
      { name: 'p1', type: 'Electrical', itemType: 'interface' },
      { name: 'p2', type: 'Electrical', itemType: 'interface' },
      { name: 'frequency', type: 'Hz', itemType: 'parameter' },
    ],
  },
  {
    id: 'Addressor',
    name: 'Addressor',
    type: 'module',
    description: 'I²C address selector with configurable address pins.',
    usage: `addr = new Addressor<address_bits=2>
addr.base = 0x40
addr.address_lines[0].line ~ power.lv  # A0 = 0
addr.address_lines[1].line ~ power.hv  # A1 = 1
assert addr.address is sensor.i2c.address`,
    children: [
      { name: 'address_lines', type: 'ElectricLogic[]', itemType: 'interface' },
      { name: 'address', type: 'dimensionless', itemType: 'parameter' },
      { name: 'base', type: 'dimensionless', itemType: 'parameter' },
    ],
  },
  // Traits
  {
    id: 'can_bridge',
    name: 'can_bridge',
    type: 'trait',
    description: 'Marks a module as bridgeable, enabling the ~> operator for series connections.',
    usage: `# Modules with can_bridge trait:
power.hv ~> resistor ~> led.anode
input ~> capacitor ~> output`,
  },
  {
    id: 'has_footprint',
    name: 'has_footprint',
    type: 'trait',
    description: 'Indicates the component has a physical footprint for PCB layout.',
    usage: `# Automatically applied to physical components
# Access footprint info via:
resistor.footprint  # e.g., "0402"`,
  },
  {
    id: 'is_decoupled',
    name: 'is_decoupled',
    type: 'trait',
    description: 'Marks a power rail as having proper decoupling capacitors.',
    usage: `trait is_decoupled
# Applied after adding decoupling caps:
power.hv ~> cap ~> power.lv`,
  },
  {
    id: 'has_designator_prefix',
    name: 'has_designator_prefix',
    type: 'trait',
    description: 'Sets the schematic designator prefix (R, C, U, etc.) for a component.',
    usage: `trait has_designator_prefix<prefix="U">
# Results in designators like U1, U2, U3...`,
  },
]

// Type icons and colors
const typeConfig: Record<StdLibType, { icon: typeof Box; color: string; label: string }> = {
  interface: { icon: Cable, color: 'var(--ctp-blue)', label: 'Interface' },
  module: { icon: Box, color: 'var(--ctp-green)', label: 'Module' },
  component: { icon: Cpu, color: 'var(--ctp-mauve)', label: 'Component' },
  trait: { icon: Zap, color: 'var(--ctp-yellow)', label: 'Trait' },
  parameter: { icon: Hash, color: 'var(--ctp-peach)', label: 'Parameter' },
}

// Enum values dropdown component
function EnumValuesDropdown({
  values,
  onClose
}: {
  values: string[]
  onClose: () => void
}) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredValues = values.filter(v =>
    v.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="enum-dropdown" onClick={(e) => e.stopPropagation()}>
      <div className="enum-dropdown-header">
        <Search size={12} />
        <input
          type="text"
          placeholder="Search values..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          autoFocus
        />
        <button className="enum-close-btn" onClick={onClose}>×</button>
      </div>
      <div className="enum-dropdown-list">
        {filteredValues.length === 0 ? (
          <div className="enum-empty">No matching values</div>
        ) : (
          filteredValues.map((value) => (
            <div
              key={value}
              className="enum-value-item"
              onClick={() => {
                navigator.clipboard.writeText(value)
              }}
              title="Click to copy"
            >
              {value}
            </div>
          ))
        )}
      </div>
      <div className="enum-dropdown-footer">
        {filteredValues.length} of {values.length} values
      </div>
    </div>
  )
}

// Child node in tree view
function ChildNode({
  child,
  depth,
  expandedPaths,
  onToggle
}: {
  child: StdLibChild
  depth: number
  expandedPaths: Set<string>
  onToggle: (path: string) => void
}) {
  const [showEnumDropdown, setShowEnumDropdown] = useState(false)
  const path = `${depth}-${child.name}`
  const isExpanded = expandedPaths.has(path)
  const hasChildren = child.children && child.children.length > 0
  const hasEnumValues = child.enumValues && child.enumValues.length > 0
  const childType = getChildItemType(child)
  const config = typeConfig[childType]
  const Icon = config.icon

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (hasEnumValues) {
      setShowEnumDropdown(!showEnumDropdown)
    } else if (hasChildren) {
      onToggle(path)
    }
  }

  return (
    <div className="stdlib-child-node">
      <div
        className={`stdlib-child-row ${hasChildren || hasEnumValues ? 'expandable' : ''} ${hasEnumValues ? 'has-enum' : ''}`}
        style={{ paddingLeft: `${depth * 6}px` }}
        onClick={handleClick}
      >
        {hasChildren ? (
          <button className="expand-btn">
            {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        ) : hasEnumValues ? (
          <button className="expand-btn enum-expand">
            {showEnumDropdown ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        ) : (
          <span className="expand-spacer" />
        )}
        <span className="stdlib-child-icon" style={{ color: config.color }}>
          <Icon size={12} />
        </span>
        <span className="stdlib-child-name">{child.name}</span>
        <span className="stdlib-child-type" style={{ color: config.color }}>
          {child.type}
          {hasEnumValues && (
            <span className="enum-count" title={`${child.enumValues!.length} possible values`}>
              ({child.enumValues!.length})
            </span>
          )}
        </span>
      </div>

      {/* Enum values dropdown */}
      {showEnumDropdown && hasEnumValues && (
        <EnumValuesDropdown
          values={child.enumValues!}
          onClose={() => setShowEnumDropdown(false)}
        />
      )}

      {isExpanded && hasChildren && (
        <div className="stdlib-child-children">
          {child.children!.map((subChild, idx) => (
            <ChildNode
              key={`${path}-${subChild.name}-${idx}`}
              child={subChild}
              depth={depth + 1}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// Standard library item card with tree view
function StdLibCard({ 
  item, 
  isSelected, 
  onSelect,
  expandedPaths,
  onToggleChild
}: {
  item: StdLibItem
  isSelected: boolean
  onSelect: () => void
  expandedPaths: Set<string>
  onToggleChild: (itemId: string, path: string) => void
}) {
  const config = typeConfig[item.type]
  const Icon = config.icon
  const hasChildren = item.children && item.children.length > 0
  
  const handleCopyUsage = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (item.usage) {
      navigator.clipboard.writeText(item.usage)
    }
  }
  
  return (
    <div 
      className={`stdlib-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
    >
      {/* Header - always visible */}
      <div className="stdlib-card-header">
        <div className="stdlib-type-icon" style={{ color: config.color }}>
          <Icon size={14} />
        </div>
        <span className="stdlib-card-name">{item.name}</span>
        <span className="stdlib-type-badge" style={{ 
          background: `${config.color}20`,
          color: config.color 
        }}>
          {config.label}
        </span>
      </div>
      
      {/* Expanded content */}
      {isSelected && (
        <>
          {/* Description */}
          <div className="stdlib-card-description">
            {item.description}
          </div>
          
          {/* Children tree view - flows naturally under parent */}
          {hasChildren && (
            <div className="stdlib-card-children">
              {item.children!.map((child, idx) => (
                <ChildNode
                  key={`${item.id}-${child.name}-${idx}`}
                  child={child}
                  depth={0}
                  expandedPaths={expandedPaths}
                  onToggle={(path) => onToggleChild(item.id, path)}
                />
              ))}
            </div>
          )}
          
          {/* Usage example */}
          {item.usage && (
            <div className="stdlib-card-usage">
              <div className="usage-header">
                <span>Usage</span>
                <button 
                  className="copy-btn"
                  onClick={handleCopyUsage}
                  title="Copy usage example"
                >
                  <Copy size={10} />
                </button>
              </div>
              <pre className="usage-code">{item.usage}</pre>
            </div>
          )}
          
        </>
      )}
    </div>
  )
}

interface StandardLibraryPanelProps {
  items?: StdLibItem[]
  isLoading?: boolean
  onOpenDetail?: (item: StdLibItem) => void
  onRefresh?: () => void
}

export function StandardLibraryPanel({
  items,
  isLoading = false,
  onOpenDetail: _onOpenDetail,
  onRefresh: _onRefresh,
}: StandardLibraryPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expandedChildren, setExpandedChildren] = useState<Map<string, Set<string>>>(new Map())
  // Start with all groups collapsed by default
  const [collapsedGroups, setCollapsedGroups] = useState<Set<StdLibType>>(
    new Set(['interface', 'module', 'trait', 'component'])
  )
  
  // Use provided items or fall back to mock data
  const stdlibItems = items && items.length > 0 ? items : mockStdLib
  // Check if we're in search mode (has search query)
  const isSearching = searchQuery.trim().length > 0
  
  // Toggle group collapse
  const toggleGroup = (type: StdLibType) => {
    setCollapsedGroups(prev => {
      const newSet = new Set(prev)
      if (newSet.has(type)) {
        newSet.delete(type)
      } else {
        newSet.add(type)
      }
      return newSet
    })
  }
  
  // Toggle child expansion
  const handleToggleChild = (itemId: string, path: string) => {
    setExpandedChildren(prev => {
      const newMap = new Map(prev)
      const itemPaths = newMap.get(itemId) || new Set()
      const newPaths = new Set(itemPaths)
      
      if (newPaths.has(path)) {
        newPaths.delete(path)
      } else {
        newPaths.add(path)
      }
      
      newMap.set(itemId, newPaths)
      return newMap
    })
  }
  
  // Filter items
  const filteredItems = stdlibItems.filter(item => {
    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const searchInChildren = (children?: StdLibChild[]): boolean => {
        if (!children) return false
        return children.some(c => 
          c.name.toLowerCase().includes(query) ||
          c.type.toLowerCase().includes(query) ||
          searchInChildren(c.children)
        )
      }
      
      return (
        item.name.toLowerCase().includes(query) ||
        item.description.toLowerCase().includes(query) ||
        searchInChildren(item.children)
      )
    }
    
    return true
  })
  
  // Group by type for display
  const groupedItems = filteredItems.reduce((acc, item) => {
    if (!acc[item.type]) acc[item.type] = []
    acc[item.type].push(item)
    return acc
  }, {} as Record<StdLibType, StdLibItem[]>)
  
  const typeOrder: StdLibType[] = ['interface', 'module', 'trait', 'component']
  
  // Show loading state
  if (isLoading) {
    return (
      <div className="stdlib-panel">
        <div className="stdlib-toolbar">
          <div className="search-box">
            <Search size={12} />
            <input 
              type="text"
              placeholder="Search standard library..."
              disabled
            />
          </div>
        </div>
        <div className="stdlib-list">
          <div className="stdlib-loading">
            <div className="loading-spinner" />
            <span>Loading standard library...</span>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="stdlib-panel">
      {/* Search and filters */}
      <div className="stdlib-toolbar">
        <div className="search-box">
          <Search size={12} />
          <input 
            type="text"
            placeholder="Search standard library..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      
      {/* Items list */}
      <div className="stdlib-list">
        {isSearching ? (
          // Flat list when searching - no groups, just show all matching results
          <div className="stdlib-search-results">
            {filteredItems.length === 0 ? (
              <div className="stdlib-empty">
                <Search size={24} />
                <span>No results for "{searchQuery}"</span>
              </div>
            ) : (
              <>
                <div className="search-results-count">
                  {filteredItems.length} result{filteredItems.length !== 1 ? 's' : ''}
                </div>
                {filteredItems.map(item => (
                  <StdLibCard
                    key={item.id}
                    item={item}
                    isSelected={selectedId === item.id}
                    onSelect={() => setSelectedId(selectedId === item.id ? null : item.id)}
                    expandedPaths={expandedChildren.get(item.id) || new Set()}
                    onToggleChild={(path) => handleToggleChild(item.id, path)}
                  />
                ))}
              </>
            )}
          </div>
        ) : (
          // Grouped view when not searching
          typeOrder.map(type => {
            const items = groupedItems[type]
            if (!items || items.length === 0) return null
            
            const config = typeConfig[type]
            const Icon = config.icon
            const isCollapsed = collapsedGroups.has(type)
            
            return (
              <div key={type} className={`stdlib-group ${isCollapsed ? 'collapsed' : ''}`}>
                <button 
                  className="stdlib-group-header"
                  onClick={() => toggleGroup(type)}
                  style={{ '--group-color': config.color } as React.CSSProperties}
                >
                  <span className="group-chevron">
                    {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                  </span>
                  <span className="group-icon" style={{ color: config.color }}>
                    <Icon size={12} />
                  </span>
                  <span className="group-label">{config.label}s</span>
                  <span className="group-count">({items.length})</span>
                </button>
                {!isCollapsed && (
                  <div className="stdlib-group-items">
                    {items.map(item => (
                      <StdLibCard
                        key={item.id}
                        item={item}
                        isSelected={selectedId === item.id}
                        onSelect={() => setSelectedId(selectedId === item.id ? null : item.id)}
                        expandedPaths={expandedChildren.get(item.id) || new Set()}
                        onToggleChild={handleToggleChild}
                      />
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}
        
        {filteredItems.length === 0 && (
          <div className="empty-state">
            <span>No items found</span>
            {searchQuery && (
              <span className="empty-hint">Try "I2C", "Resistor", or "power"</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
