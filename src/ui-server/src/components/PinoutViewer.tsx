/**
 * PinoutViewer - Interactive IC pinout diagram.
 *
 * Renders a physical chip layout using actual KiCad pad coordinates.
 * Pin pads are color-coded by bus type, labels rotate to match orientation,
 * and clicking a pin shows a detail popup with alternate functions.
 */

import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch'
import './PinoutViewer.css'

// ── Types ──────────────────────────────────────────────────────────────

interface PinoutData {
  version: string
  components: ComponentData[]
}

interface ComponentData {
  id: string
  name: string
  module_type: string | null
  designator: string | null
  package: string | null
  pin_count: number
  total_pads: number
  geometry: {
    x: number; y: number; width: number; height: number
    pad_bbox: { min_x: number; min_y: number; max_x: number; max_y: number }
  }
  pins: PinData[]
  buses: BusData[]
}

interface PinData {
  number: string
  name: string
  side: 'left' | 'right' | 'top' | 'bottom'
  position: number
  type: 'power' | 'ground' | 'signal' | 'nc'
  active_function: { name: string; type: string } | null
  alternate_functions: { name: string; type: string }[]
  pad_count: number | null
  x: number | null
  y: number | null
  w: number | null
  h: number | null
  rotation: number
}

interface BusData {
  id: string; type: string; name: string; pin_numbers: string[]
}

// ── Constants ──────────────────────────────────────────────────────────

const BUS_COLORS: Record<string, string> = {
  Power: '#e06c75', I2C: '#61afef', SPI: '#c678dd', UART: '#e5c07b',
  I2S: '#56b6c2', USB: '#98c379', JTAG: '#d19a66', Crystal: '#abb2bf',
  Analog: '#be5046', GPIO: '#6b7280', Control: '#d19a66', Signal: '#4b5263',
}

const TYPE_COLORS: Record<string, string> = {
  power: '#e06c75', ground: '#555', signal: '#888', nc: '#3e4451',
}

function getPinColor(pin: PinData): string {
  if (pin.active_function) return BUS_COLORS[pin.active_function.type] || '#666'
  return TYPE_COLORS[pin.type] || '#666'
}

// ── Scale: convert mm to px ────────────────────────────────────────────

const TARGET_PIN_HEIGHT_PX = 20 // desired visual height per pin slot
const MIN_SCALE = 8
const MAX_SCALE = 40
const FALLBACK_SCALE = 24

/** Compute per-component scale so pins render at a consistent visual size. */
function computeScale(comp: ComponentData): number {
  // Find minimum pad pitch (smallest gap between adjacent pads)
  const sides: Record<string, number[]> = {}
  for (const p of comp.pins) {
    if (p.x == null || p.y == null) continue
    const key = p.side
    if (!sides[key]) sides[key] = []
    sides[key].push(key === 'left' || key === 'right' ? p.y : p.x)
  }

  let minPitch = Infinity
  for (const coords of Object.values(sides)) {
    const sorted = [...coords].sort((a, b) => a - b)
    for (let i = 1; i < sorted.length; i++) {
      const diff = sorted[i] - sorted[i - 1]
      if (diff > 0.01) minPitch = Math.min(minPitch, diff)
    }
  }

  if (!isFinite(minPitch) || minPitch <= 0) return FALLBACK_SCALE

  // Scale so that one pitch = TARGET_PIN_HEIGHT_PX
  const scale = TARGET_PIN_HEIGHT_PX / minPitch
  return Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale))
}

// ── Main Component ─────────────────────────────────────────────────────

interface PinoutViewerProps {
  data: PinoutData
}

export function PinoutViewer({ data }: PinoutViewerProps) {
  const [activeIdx, setActiveIdx] = useState(0)
  // selectedBus is now a bus ID (e.g. "mcu_esp32_c3_package_I2C_mcu") or a type string for power
  const [selectedBus, setSelectedBus] = useState<string | null>(null)
  const [selectedPin, setSelectedPin] = useState<PinData | null>(null)
  const [popupPos, setPopupPos] = useState<{ x: number; y: number } | null>(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const [search, setSearch] = useState('')

  const comp = data.components[activeIdx]

  const filteredComps = useMemo(() => {
    if (!search) return data.components
    const q = search.toLowerCase()
    return data.components.filter(c =>
      c.name.toLowerCase().includes(q) ||
      (c.designator || '').toLowerCase().includes(q) ||
      (c.module_type || '').toLowerCase().includes(q)
    )
  }, [data.components, search])

  // Build the list of active buses from the component's bus data
  const activeBuses = useMemo(() => {
    if (!comp) return []
    const buses: { id: string; type: string; name: string; pinCount: number }[] = []

    // Add a synthetic "Power/GND" bus only if there are power pins
    // not already covered by a real Power bus in the data
    const hasPowerBus = comp.buses.some(b => b.type === 'Power')
    if (!hasPowerBus) {
      const pwrCount = comp.pins.filter(p => p.type === 'power' || p.type === 'ground').length
      if (pwrCount > 0) {
        buses.push({ id: '__power__', type: 'Power', name: 'Power/GND', pinCount: pwrCount })
      }
    }

    // Real buses from the component data
    comp.buses.forEach(b => {
      buses.push({ id: b.id, type: b.type, name: b.name, pinCount: b.pin_numbers.length })
    })
    return buses
  }, [comp])

  // Set of highlighted pin numbers for the selected bus
  const highlightedPins = useMemo(() => {
    if (!selectedBus || !comp) return null
    if (selectedBus === '__power__') {
      return new Set(comp.pins.filter(p => p.type === 'power' || p.type === 'ground').map(p => p.number))
    }
    const bus = comp.buses.find(b => b.id === selectedBus)
    if (bus) return new Set(bus.pin_numbers)
    return null
  }, [selectedBus, comp])

  const handlePinClick = useCallback((pin: PinData, e: React.MouseEvent) => {
    e.stopPropagation()
    if (selectedPin?.number === pin.number) {
      setSelectedPin(null)
      setPopupPos(null)
    } else {
      setSelectedPin(pin)
      setPopupPos({ x: e.clientX, y: e.clientY })
    }
  }, [selectedPin])

  const handleBgClick = useCallback(() => {
    setSelectedPin(null)
    setPopupPos(null)
    setSelectedBus(null)
  }, [])

  if (!comp) return null

  return (
    <div className="pinout-layout">
      {/* Side panel */}
      <div className={`pinout-panel ${panelOpen ? '' : 'collapsed'}`}>
        {/* Component selector */}
        {data.components.length > 1 && (
          <>
            <div className="pinout-panel-header">
              <span>Components</span>
              <button className="pinout-panel-close" onClick={() => setPanelOpen(false)}>&times;</button>
            </div>
            <div className="pinout-panel-search">
              <input
                placeholder="Search..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <div className="pinout-comp-list">
              {filteredComps.map(c => {
                const realIdx = data.components.indexOf(c)
                return (
                  <button
                    key={c.id}
                    className={`pinout-comp-item ${realIdx === activeIdx ? 'active' : ''}`}
                    onClick={() => { setActiveIdx(realIdx); setSelectedPin(null); setSelectedBus(null) }}
                  >
                    <span className="pinout-comp-des">{c.designator || '—'}</span>
                    <span className="pinout-comp-name">{c.name}</span>
                    <span className="pinout-comp-cnt">{c.pin_count}</span>
                  </button>
                )
              })}
            </div>
          </>
        )}
        {data.components.length <= 1 && (
          <div className="pinout-panel-header">
            <span>Buses</span>
            <button className="pinout-panel-close" onClick={() => setPanelOpen(false)}>&times;</button>
          </div>
        )}

        {/* Active buses list */}
        <div className="pinout-buses">
          {data.components.length > 1 && <div className="pinout-panel-divider" />}
          <div className="pinout-buses-title">Active Buses</div>
          <div className="pinout-buses-list">
            {activeBuses.map(b => (
              <button
                key={b.id}
                className={`pinout-bus-item ${selectedBus === b.id ? 'active' : ''}`}
                onClick={(e) => { e.stopPropagation(); setSelectedBus(prev => prev === b.id ? null : b.id) }}
              >
                <span className="pinout-bus-swatch" style={{ background: BUS_COLORS[b.type] || '#666' }} />
                <span className="pinout-bus-name">{b.name}</span>
                <span className="pinout-bus-type">{b.type}</span>
                <span className="pinout-bus-cnt">{b.pinCount}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main canvas with zoom/pan */}
      <div className="pinout-canvas" onClick={handleBgClick}>
        {!panelOpen && (
          <button className="pinout-menu-btn" onClick={e => { e.stopPropagation(); setPanelOpen(true) }}>
            &#9776;
          </button>
        )}
        <TransformWrapper
          initialScale={0.9}
          minScale={0.3}
          maxScale={5}
          centerOnInit
          wheel={{ step: 0.08 }}
          panning={{ velocityDisabled: true }}
          doubleClick={{ disabled: true }}
        >
          {({ zoomIn, zoomOut, resetTransform }) => (
            <>
              <div className="pinout-zoom-controls">
                <button onClick={() => zoomIn()} title="Zoom in">+</button>
                <button onClick={() => zoomOut()} title="Zoom out">&minus;</button>
                <button onClick={() => resetTransform()} title="Reset view">&#8634;</button>
              </div>
              <TransformComponent
                wrapperStyle={{ width: '100%', height: '100%' }}
                contentStyle={{ width: 'fit-content', height: 'fit-content' }}
              >
                <ChipDiagram
                  comp={comp}
                  highlightedPins={highlightedPins}
                  selectedPin={selectedPin}
                  onPinClick={handlePinClick}
                />
              </TransformComponent>
            </>
          )}
        </TransformWrapper>
      </div>

      {/* Detail popup */}
      {selectedPin && popupPos && (
        <PinDetail pin={selectedPin} pos={popupPos} onClose={() => { setSelectedPin(null); setPopupPos(null) }} />
      )}
    </div>
  )
}

// ── Chip Diagram ───────────────────────────────────────────────────────

interface ChipDiagramProps {
  comp: ComponentData
  highlightedPins: Set<string> | null
  selectedPin: PinData | null
  onPinClick: (pin: PinData, e: React.MouseEvent) => void
}

function ChipDiagram({ comp, highlightedPins, selectedPin, onPinClick }: ChipDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  const geo = comp.geometry
  if (!geo) return null

  // Per-component scale so pins are visually consistent across packages
  const scale = useMemo(() => computeScale(comp), [comp])

  const bbox = geo.pad_bbox
  // Total area in mm including label margins
  const labelMargin = 14 // mm for labels
  const totalW = (bbox.max_x - bbox.min_x + labelMargin * 2) * scale
  const totalH = (bbox.max_y - bbox.min_y + labelMargin * 2) * scale
  const originX = (-bbox.min_x + labelMargin) * scale
  const originY = (-bbox.min_y + labelMargin) * scale

  // Chip body in px
  const bodyX = originX + geo.x * scale
  const bodyY = originY + geo.y * scale
  const bodyW = geo.width * scale
  const bodyH = geo.height * scale

  return (
    <div className="pinout-diagram-wrap">
      <div className="pinout-diagram-scroll">
        <div
          ref={containerRef}
          className="pinout-diagram"
          style={{ width: totalW, height: totalH, position: 'relative' }}
        >
          {/* Chip body */}
          <div
            className="pinout-chip-body"
            style={{ left: bodyX, top: bodyY, width: bodyW, height: bodyH }}
          >
            <div className="pinout-chip-dot" />
            <div className="pinout-chip-label">{comp.designator || comp.name}</div>
            {comp.module_type && (
              <div className="pinout-chip-sublabel">{comp.module_type}</div>
            )}
          </div>

          {/* Pins */}
          {comp.pins.map(pin => {
            if (pin.x == null || pin.y == null) return null
            return (
              <PinPad
                key={pin.number}
                pin={pin}
                originX={originX}
                originY={originY}
                scale={scale}
                highlightedPins={highlightedPins}
                isSelected={selectedPin?.number === pin.number}
                onPinClick={onPinClick}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Pin Pad ────────────────────────────────────────────────────────────

interface PinPadProps {
  pin: PinData
  originX: number
  originY: number
  scale: number
  highlightedPins: Set<string> | null
  isSelected: boolean
  onPinClick: (pin: PinData, e: React.MouseEvent) => void
}

function PinPad({ pin, originX, originY, scale, highlightedPins, isSelected, onPinClick }: PinPadProps) {
  const color = getPinColor(pin)
  // Raw pad dimensions from KiCad (before any rotation)
  const padW = (pin.w || 0.5) * scale
  const padH = (pin.h || 0.5) * scale
  const cx = originX + pin.x! * scale
  const cy = originY + pin.y! * scale

  const faded = highlightedPins ? !highlightedPins.has(pin.number) : false
  const fnText = pin.active_function?.name || ''
  const label = fnText || pin.name

  // Each pin is a horizontal row: [label] [pad] for left side,
  // [pad] [label] for right side. For top/bottom the whole unit is rotated.
  //
  // Structure: a container div centered on the pad's KiCad position,
  // containing the pad + label in a flex row. For top/bottom, the
  // container is rotated as a unit.

  const isLeft = pin.side === 'left'
  const isRight = pin.side === 'right'
  const isTop = pin.side === 'top'

  // All pins use the NATIVE pad dimensions (no swapping).
  // Left/right: container is horizontal, pad is vertical (padW x padH).
  // Top/bottom: same container, but rotated ±90° as a unit — the rotation
  // naturally makes the vertical pad appear horizontal.

  // The pin unit is a single row: [accent][number][label]
  // For left side, it's reversed: [label][number][accent]
  // For top/bottom, the unit is rotated as a whole.

  // All sides: position at pad center, auto-size to content.
  // The accent bar is always on the chip-body side.
  // Left: row-reverse (accent right, label left, overflows leftward)
  // Right/Top/Bottom: row (accent left, label right)
  // Top/Bottom: rotated ±90° around pad center

  const base: React.CSSProperties = {
    position: 'absolute',
    display: 'inline-flex',
    alignItems: 'center',
    height: padH,
    cursor: 'pointer',
    left: cx - padW / 2,
    top: cy - padH / 2,
  }

  let containerStyle: React.CSSProperties

  if (isLeft) {
    // Anchor right edge at pad right edge, content grows leftward
    containerStyle = {
      ...base,
      flexDirection: 'row-reverse',
      // Position right edge at pad right edge, content grows leftward
      left: cx + padW / 2,
      transform: 'translateX(-100%)',
    }
  } else if (isRight) {
    containerStyle = { ...base, flexDirection: 'row' }
  } else if (isTop) {
    containerStyle = {
      ...base,
      flexDirection: 'row',
      transform: 'rotate(-90deg)',
      transformOrigin: `${padW / 2}px ${padH / 2}px`,
    }
  } else {
    // bottom
    containerStyle = {
      ...base,
      flexDirection: 'row',
      transform: 'rotate(90deg)',
      transformOrigin: `${padW / 2}px ${padH / 2}px`,
    }
  }

  const hasFunction = !!fnText
  const isNC = !hasFunction && pin.type === 'signal'
  const ncClass = isNC ? ' nc' : ''

  return (
    <div
      style={{ ...containerStyle, '--pin-color': color } as React.CSSProperties}
      className={`pinout-pin-unit${faded ? ' faded' : ''}${isSelected ? ' selected' : ''}${ncClass}`}
      onClick={e => onPinClick(pin, e)}
      title={`Pin ${pin.number}: ${pin.name}${fnText ? ' — ' + fnText : ''}\n${pin.alternate_functions.map(f => f.name + ' (' + f.type + ')').join('\n')}`}
    >
      {/* Color accent bar */}
      <span className="pinout-pin-accent" style={{ background: color }} />
      {/* Pin number */}
      <span className="pinout-pin-num">{pin.number}</span>
      {/* Function label — show for all sides, hide for NC */}
      {!isNC && (
        <span className="pinout-pin-label">{label}</span>
      )}
    </div>
  )
}

// ── Pin Detail Popup ───────────────────────────────────────────────────

interface PinDetailProps {
  pin: PinData
  pos: { x: number; y: number }
  onClose: () => void
}

function PinDetail({ pin, pos, onClose }: PinDetailProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [adjustedPos, setAdjustedPos] = useState(pos)

  useEffect(() => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect()
      let x = pos.x + 12
      let y = pos.y - 20
      if (x + rect.width > window.innerWidth) x = pos.x - rect.width - 12
      if (y + rect.height > window.innerHeight) y = window.innerHeight - rect.height - 8
      if (y < 4) y = 4
      setAdjustedPos({ x, y })
    }
  }, [pos])

  const color = getPinColor(pin)

  return (
    <div
      ref={ref}
      className="pinout-detail"
      style={{ left: adjustedPos.x, top: adjustedPos.y }}
      onClick={e => e.stopPropagation()}
    >
      <button className="pinout-detail-close" onClick={onClose}>&times;</button>
      <div className="pinout-detail-header">
        <span className="pinout-detail-num">Pin {pin.number}</span>
        <span className="pinout-detail-name">{pin.name}</span>
        <span className="pinout-detail-type" style={{ background: color }}>{pin.type}</span>
      </div>

      {pin.active_function && (
        <>
          <div className="pinout-detail-section">Active</div>
          <div className="pinout-detail-fn">
            <span className="pinout-detail-dot" style={{ background: BUS_COLORS[pin.active_function.type] || '#666' }} />
            <span className="pinout-detail-fn-name">{pin.active_function.name}</span>
            <span className="pinout-detail-fn-type">{pin.active_function.type}</span>
          </div>
        </>
      )}

      {pin.alternate_functions.length > 0 && (
        <>
          <div className="pinout-detail-section">Alternates</div>
          {pin.alternate_functions.map((fn, i) => (
            <div key={i} className="pinout-detail-fn">
              <span className="pinout-detail-dot" style={{ background: BUS_COLORS[fn.type] || '#666' }} />
              <span className="pinout-detail-fn-name">{fn.name}</span>
              <span className="pinout-detail-fn-type">{fn.type}</span>
            </div>
          ))}
        </>
      )}

      {pin.pad_count && pin.pad_count > 1 && (
        <div className="pinout-detail-meta">{pin.pad_count} pads connected</div>
      )}
    </div>
  )
}
